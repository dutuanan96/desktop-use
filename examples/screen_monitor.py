"""Screen Monitor Example — desktop-use

Polls the screen for specific text patterns and triggers actions when
they appear.  Useful for waiting on download dialogs, auto-dismissing
errors, or monitoring log windows for specific events.

Real-world uses:
  - Wait for "Download Complete" and click the notification away
  - Monitor a server log window for error messages
  - Auto-dismiss recurring error dialogs
  - Detect when a build finishes in a terminal window
"""

import time
from desktop_use.client import DesktopAgent

POLL_INTERVAL = 2     # seconds between scans
MAX_POLLS    = 50     # 0 = infinite (until Ctrl+C)

# Rules: what text to look for and what action to take.
# "once" = trigger only once, then deactivate that rule.
RULES = [
    {"pattern": "error",            "action": "dismiss", "once": True},
    {"pattern": "download complete", "action": "click",  "target": "Open",  "once": True},
    {"pattern": "save changes",     "action": "click",  "target": "Don't Save", "once": False},
]


def log(msg):
    """Print a timestamped message."""
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


def execute_action(agent, rule):
    """Run the action defined in a rule.  Returns True on success."""
    action = rule["action"]
    if action == "click":
        target = rule.get("target", "OK")
        found = agent.find_text(target)
        if found.get("success"):
            x, y = found["data"]["center"]
            agent.click(x, y)
            log(f"  -> Clicked '{target}' at ({x},{y})")
            return True
        log(f"  -> '{target}' not found"); return False
    elif action == "dismiss":
        for btn in ["OK", "Close", "Dismiss", "Cancel"]:
            found = agent.find_text(btn)
            if found.get("success"):
                x, y = found["data"]["center"]
                agent.click(x, y)
                log(f"  -> Dismissed via '{btn}'"); return True
        log("  -> No dismiss button found"); return False
    return False


def monitor(agent):
    """Main polling loop — OCR the screen and check rules each iteration."""
    fired = set()
    for poll in range(1, MAX_POLLS + 1) if MAX_POLLS > 0 else iter(int, 0):
        log(f"Poll #{poll}")
        result = agent.screenshot(ocr=True)
        if not result.get("success"):
            log(f"  Screenshot failed"); time.sleep(POLL_INTERVAL); continue

        text_lower = result.get("text", "").lower()
        for idx, rule in enumerate(RULES):
            if rule.get("once") and idx in fired: continue
            if rule["pattern"].lower() in text_lower:
                log(f"  MATCH: '{rule['pattern']}'")
                if execute_action(agent, rule) and rule.get("once"):
                    fired.add(idx); log(f"  Rule #{idx} deactivated")
        time.sleep(POLL_INTERVAL)
    log("Monitoring complete.")


def main():
    agent = DesktopAgent()
    print(f"=== Screen Monitor ===  ({POLL_INTERVAL}s interval, "
          f"{len(RULES)} rules, max {MAX_POLLS or 'infinite'} polls)\n")
    health = agent.health()
    if not health.get("success"):
        print(f"Server not reachable: {health}"); return
    print("Server connected.\n")
    monitor(agent)


if __name__ == "__main__":
    try: main()
    except ConnectionError as e: print(f"Server not reachable: {e}")
    except KeyboardInterrupt: print("\nStopped by user.")
    except Exception as e: print(f"Unexpected error: {e}")
