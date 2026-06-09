"""Cross-App Workflow Example — desktop-use

Reads data from one app, transforms it, and writes it into another.
Demonstrates window management, clipboard round-trips, and batch
commands for real multi-app automation workflows.

Real-world uses:
  - Copying data from a spreadsheet into an email
  - Moving text from a chat app into a ticketing system
  - Extracting info from a PDF reader into a form
"""

import re
import time
from desktop_use.client import DesktopAgent

SOURCE_WINDOW = "Notepad"    # app to read from
DEST_WINDOW   = "Excel"      # app to write into
SWITCH_DELAY  = 0.5


def extract_text_from_window(agent, title):
    """Focus a window, select-all + copy, read clipboard.  OCR fallback."""
    print(f"\n  Focusing '{title}'...")
    if not agent.focus_window(title).get("success"):
        print("    Could not focus window."); return ""
    agent.hotkey("ctrl", "a"); time.sleep(0.3)
    agent.hotkey("ctrl", "c"); time.sleep(0.3)

    text = agent.clipboard_get()
    if text:
        print(f"  Got {len(text)} chars from clipboard"); return text

    print("  Clipboard empty — OCR fallback...")
    shot = agent.screenshot(ocr=True)
    return shot.get("text", "") if shot.get("success") else ""


def transform_text(raw):
    """Parse raw text into records.  Extracts "Key: Value" lines."""
    records = []
    for line in raw.splitlines():
        line = line.strip()
        if not line: continue
        m = re.match(r"^(.+?):\s*(.+)$", line)
        if m:
            records.append({"key": m.group(1).strip(), "value": m.group(2).strip()})
        else:
            records.append({"key": "line", "value": line})
    return records


def paste_to_destination(agent, records):
    """Focus destination app and paste all records via batch commands."""
    if not records:
        print("  No records to paste."); return
    commands = [{"action": "focus_window", "title": DEST_WINDOW}]
    for rec in records:
        commands.append({"action": "type", "text": f"{rec['key']}\t{rec['value']}\n"})
        commands.append({"action": "wait", "seconds": 0.1})
    print(f"  Sending {len(commands)} commands to '{DEST_WINDOW}'...")
    result = agent.batch(commands)
    print("  OK." if result.get("success") else f"  Failed: {result}")


def main():
    agent = DesktopAgent()
    print("=== Cross-App Workflow ===\n")

    health = agent.health()
    if not health.get("success"):
        print(f"Server not reachable: {health}"); return
    print("Server connected.\n")

    # 1. Discover open windows
    print("Step 1: Open windows")
    for w in agent.get_windows().get("data", []):
        a = " [ACTIVE]" if w.get("active") else ""
        print(f"  - {w['title']} ({w['width']}x{w['height']}){a}")

    # 2. Extract data from source
    print(f"\nStep 2: Extract from '{SOURCE_WINDOW}'")
    raw_text = extract_text_from_window(agent, SOURCE_WINDOW)
    if not raw_text.strip():
        print("  No text — is the source app open?"); return
    print(f"  Preview: {raw_text.strip().splitlines()[:3]}")

    # 3. Transform
    print("\nStep 3: Transform")
    records = transform_text(raw_text)
    print(f"  Parsed {len(records)} records")
    for r in records[:3]:
        print(f"    {r['key']}: {r['value']}")

    # 4. Paste into destination
    print(f"\nStep 4: Paste into '{DEST_WINDOW}'")
    paste_to_destination(agent, records)

    # 5. Verification screenshot
    print("\nStep 5: Verification")
    final = agent.screenshot(ocr=True)
    if final.get("success"):
        print(f"  Saved: {final.get('path', '?')}")
    print("Done.")


if __name__ == "__main__":
    try: main()
    except ConnectionError as e: print(f"Server not reachable: {e}")
    except KeyboardInterrupt: print("\nInterrupted.")
    except Exception as e: print(f"Error: {e}")
