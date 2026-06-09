"""AI Agent Loop Example — desktop-use

Demonstrates the core automation pattern used by AI-driven agents:
  1. Screenshot the screen (with OCR).
  2. Analyse the text / state.
  3. Decide what action to take next.
  4. Execute the action.
  5. Repeat until the task is complete.

In a real deployment the "decide" step calls an LLM; here we use a
simple rule-based demo so the script is self-contained.
"""

import time
from desktop_use.client import DesktopAgent

MAX_STEPS = 10  # safety limit to avoid infinite loops
STEP_DELAY = 1  # seconds between iterations


def decide(ocr_text: str) -> dict | None:
    """Simple rule-based decision maker.  Returns an action dict or None."""
    text_lower = ocr_text.lower()

    if "error" in text_lower or "failed" in text_lower:
        print("  → Detected error state — clicking OK if present.")
        return {"action": "find_and_click", "text": "OK"}

    if "save" in text_lower:
        print("  → Detected save prompt — pressing Ctrl+S.")
        return {"action": "hotkey", "keys": ["ctrl", "s"]}

    if "password" in text_lower:
        print("  → Detected password field — typing password.")
        return {"action": "type", "text": "my_secret_password"}

    # Default: nothing to do
    return None


def execute_action(agent: DesktopAgent, action: dict) -> None:
    """Execute a single action dict produced by decide()."""
    kind = action["action"]

    if kind == "find_and_click":
        found = agent.find_text(action["text"])
        if found.get("success"):
            agent.click(found["x"], found["y"])
            print(f"    Clicked '{action['text']}' at ({found['x']}, {found['y']})")
        else:
            print(f"    '{action['text']}' not found on screen.")

    elif kind == "hotkey":
        agent.hotkey(*action["keys"])
        print(f"    Pressed {'+'.join(action['keys'])}")

    elif kind == "type":
        agent.type_text(action["text"])
        print(f"    Typed text ({len(action['text'])} chars)")

    else:
        print(f"    Unknown action: {kind}")


def main():
    agent = DesktopAgent()
    print("=== AI Agent Loop (demo) ===\n")

    for step in range(1, MAX_STEPS + 1):
        print(f"--- Step {step} ---")

        # 1. Screenshot + OCR
        result = agent.screenshot(ocr=True)
        if not result.get("success"):
            print(f"  Screenshot failed: {result}")
            break

        ocr_text = result.get("text", "")
        print(f"  OCR text ({len(ocr_text)} chars): {ocr_text[:120]}...")

        # 2. Decide
        action = decide(ocr_text)
        if action is None:
            print("  No action needed — task complete or idle.")
            break

        # 3. Execute
        execute_action(agent, action)
        time.sleep(STEP_DELAY)

    print("\nAgent loop finished.")


if __name__ == "__main__":
    try:
        main()
    except ConnectionError as e:
        print(f"Could not connect to desktop-use server: {e}")
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")
