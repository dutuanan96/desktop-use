"""Basic Usage Example — desktop-use

Demonstrates the fundamental operations:
  - Taking a screenshot with OCR
  - Finding text on screen
  - Clicking at coordinates
  - Typing text
  - Reading the current mouse position

Run the desktop-use server on Windows first, then execute this script.
"""

import time
from desktop_use.client import DesktopAgent


def main():
    agent = DesktopAgent()

    # --- 1. Screenshot with OCR ------------------------------------------------
    print("Taking a screenshot with OCR...")
    result = agent.screenshot(ocr=True)
    if not result.get("success"):
        print(f"Screenshot failed: {result}")
        return
    print(f"Screenshot saved. OCR text (first 200 chars):")
    print(result.get("text", "")[:200])

    # --- 2. Find text on screen ------------------------------------------------
    target = "Start"
    print(f"\nSearching for '{target}' on screen...")
    found = agent.find_text(target)
    if found.get("success"):
        x, y = found["x"], found["y"]
        print(f"Found '{target}' at ({x}, {y})")
    else:
        print(f"'{target}' not found on screen.")
        return

    # --- 3. Click at the found position ----------------------------------------
    print(f"Clicking on ({x}, {y})...")
    click_result = agent.click(x, y)
    if click_result.get("success"):
        print("Click succeeded.")
    else:
        print(f"Click failed: {click_result}")

    time.sleep(1)

    # --- 4. Type some text -----------------------------------------------------
    print("Typing 'Hello, desktop-use!'...")
    agent.focus_window("Notepad")  # adjust window title as needed
    type_result = agent.type_text("Hello, desktop-use!")
    print("Type succeeded." if type_result.get("success") else f"Type failed: {type_result}")

    # --- 5. Get current mouse position ----------------------------------------
    pos = agent.get_mouse()
    if pos.get("success"):
        print(f"\nMouse is at ({pos['x']}, {pos['y']})")
    else:
        print(f"get_mouse failed: {pos}")


if __name__ == "__main__":
    try:
        main()
    except ConnectionError as e:
        print(f"Could not connect to desktop-use server: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
