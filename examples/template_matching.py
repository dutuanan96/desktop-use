"""Template Matching Example — desktop-use

Shows how to use template matching to find a visual element on screen:
  1. Take a screenshot and save a region as a template image.
  2. Use find_template() to locate that image on screen.
  3. Click the center of the matched region.

This is useful when you need to find icons, buttons, or UI elements
that don't have selectable text.
"""

import time
from desktop_use.client import DesktopAgent


# Coordinates for the region to save as a template (x, y, width, height).
# Adjust these to match the target element on YOUR screen.
TEMPLATE_REGION = {"x": 100, "y": 100, "width": 80, "height": 80}
TEMPLATE_PATH = "templates/my_button.png"


def main():
    agent = DesktopAgent()

    # --- 1. Take a full screenshot so the region is visible on disk ----------
    print("Taking screenshot...")
    result = agent.screenshot(ocr=False)
    if not result.get("success"):
        print(f"Screenshot failed: {result}")
        return
    print(f"Screenshot saved to: {result.get('path', 'unknown')}")

    # --- 2. Save a cropped region as the template image ----------------------
    #    (The server exposes a crop endpoint, or you can use PIL locally.)
    print(f"Saving template region {TEMPLATE_REGION} to {TEMPLATE_PATH}...")
    crop_result = agent.save_template(
        TEMPLATE_REGION["x"], TEMPLATE_REGION["y"],
        TEMPLATE_REGION["width"], TEMPLATE_REGION["height"],
        save_path=TEMPLATE_PATH,
    )
    if crop_result.get("success"):
        print(f"Template saved: {crop_result.get('path')}")
    else:
        print(f"Could not save template: {crop_result}")
        return

    # --- 3. Find the template on screen --------------------------------------
    print("Searching for template on screen...")
    match = agent.find_template(TEMPLATE_PATH)
    if match.get("success"):
        x, y = match["x"], match["y"]
        confidence = match.get("confidence", "N/A")
        print(f"Template found at ({x}, {y})  confidence={confidence}")
    else:
        print("Template not found on screen.")
        return

    # --- 4. Click the matched position ---------------------------------------
    print(f"Clicking on match at ({x}, {y})...")
    click_result = agent.click(x, y)
    print("Click succeeded." if click_result.get("success") else f"Click failed: {click_result}")

    time.sleep(0.5)


if __name__ == "__main__":
    try:
        main()
    except ConnectionError as e:
        print(f"Could not connect to desktop-use server: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
