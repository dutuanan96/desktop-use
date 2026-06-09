"""Form Filler Example — desktop-use

Automates filling out a form with structured data by finding labeled
fields on screen via OCR and typing values into them.

Real-world uses:
  - Entering invoice data into accounting apps
  - Filling out government forms from a spreadsheet
  - Populating CRM fields from a contact list
"""

import time
from desktop_use.client import DesktopAgent

# Data to fill — keys should roughly match form labels on screen.
RECORD = {
    "First Name": "Jane",
    "Last Name":  "Doe",
    "Email":      "jane.doe@example.com",
    "Phone":      "555-123-4567",
    "Address":    "123 Main Street",
}

ACTION_DELAY = 0.3  # seconds between UI actions


def find_and_focus_field(agent, label):
    """Find a form label on screen, click next to it to focus the input."""
    result = agent.find_text(label)
    if not result.get("success"):
        print(f"    [!] Label '{label}' not found — skipping.")
        return False

    label_x, label_y = result["data"]["center"]
    agent.click(label_x + 150, label_y)       # offset right of label
    time.sleep(ACTION_DELAY)
    agent.hotkey("ctrl", "a")                  # select all existing text
    time.sleep(0.1)
    return True


def fill_form(agent, record):
    """Fill each field in the form with the corresponding record value."""
    filled = 0
    for i, (label, value) in enumerate(record.items(), 1):
        print(f"  [{i}/{len(record)}] Filling '{label}' = '{value}'")
        if not find_and_focus_field(agent, label):
            continue
        agent.type_text(str(value))            # paste via clipboard
        filled += 1
        time.sleep(ACTION_DELAY)
        agent.press("tab")                     # move to next field
    print(f"\n  Done — filled {filled}/{len(record)} fields.")


def main():
    agent = DesktopAgent()

    # Verify server connection
    health = agent.health()
    if not health.get("success"):
        print(f"Server not reachable: {health}"); return
    print(f"Server OK — version {health.get('version', '?')}")

    # Take initial screenshot + verify labels are on screen
    shot = agent.screenshot(ocr=True)
    if not shot.get("success"):
        print(f"Screenshot failed: {shot}"); return
    print(f"\nVerifying labels...")
    for label in RECORD:
        status = "OK" if agent.find_text(label).get("success") else "MISSING"
        print(f"  '{label}' — {status}")

    # Fill the form
    print("\nFilling form...")
    fill_form(agent, RECORD)

    # Final verification screenshot
    final = agent.screenshot(ocr=True)
    if final.get("success"):
        print(f"Final screenshot: {final.get('path', '?')}")


if __name__ == "__main__":
    try:
        main()
    except ConnectionError as e:
        print(f"Could not connect to desktop-use server: {e}")
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")
