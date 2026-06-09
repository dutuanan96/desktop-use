"""Batch Commands Example — desktop-use

Demonstrates how to group multiple actions into a single batch request
for faster execution.  The server processes each action in order and
returns all results at once, avoiding per-request network overhead.

Useful for sequences like:
  focus a window → type text → press Enter → save
"""

from desktop_use.client import DesktopAgent


def main():
    agent = DesktopAgent()

    # Build a list of actions to execute in sequence.
    # Each tuple is (method_name, args, kwargs).
    batch = [
        ("focus_window",  ("Notepad",),                     {}),
        ("type_text",     ("Batch commands are fast!\n",),   {}),
        ("hotkey",        ("ctrl", "s"),                     {}),
        ("type_text",     ("test.txt",),                     {}),
        ("hotkey",        ("enter",),                        {}),
    ]

    print(f"Sending batch of {len(batch)} actions...")
    result = agent.batch(batch)

    if not result.get("success"):
        print(f"Batch failed: {result}")
        return

    # Inspect individual results
    results = result.get("results", [])
    for i, (action, res) in enumerate(zip(batch, results), 1):
        method = action[0]
        status = "OK" if res.get("success") else "FAIL"
        print(f"  [{i}] {method:20s} → {status}  {res}")

    print(f"\nBatch complete — {len(results)} actions executed.")


if __name__ == "__main__":
    try:
        main()
    except ConnectionError as e:
        print(f"Could not connect to desktop-use server: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
