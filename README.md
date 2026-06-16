<div align="center">

# 🖥️ desktop-use

**Turn any AI agent into a desktop power user — control Windows from anywhere**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%2F%20WSL-orange)](#)

</div>

---

## Why desktop-use?

AI agents can chat, write code, and reason — but they **can't control a computer**.

Today's LLMs have no hands. They can't take a screenshot, click a button, type into a field, or launch an application. Every "computer use" demo from Anthropic, Google, or Microsoft is locked behind proprietary APIs or cloud-only sandboxed VMs.

**desktop-use** fixes this. It exposes a simple HTTP + WebSocket API that lets *any* AI agent — local or remote — see and control a real Windows desktop in real time.

- 🐧 **Run your agent in WSL / Linux / Docker** while controlling a native Windows desktop
- 🤖 **Plug into any AI framework** — Hermes, Claude, LangChain, OpenAI, custom agents
- 🔒 **100% local** — no cloud APIs, no data leaves your machine
- ⚡ **Lightweight** — single pip install, server starts in < 1 second
- 🧩 **Composable** — screenshot → OCR → decide → act, all via REST calls

If you're building an AI agent that needs to *do things on a computer*, this is the missing bridge.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📸 **Screenshot** | Capture full screen or specific regions |
| 🔍 **OCR** | Extract text from any screen region (RapidOCR — no API key needed) |
| 🎯 **Template Matching** | Find UI elements by image template (OpenCV-powered) |
| 🖱️ **Mouse Control** | Click, double-click, right-click, drag, scroll at any coordinate |
| ⌨️ **Keyboard Control** | Type text (clipboard paste, bypasses IME), press hotkeys |
| 🪟 **Window Management** | Find, focus, move, resize windows |
| 📋 **Clipboard** | Read and write the system clipboard |
| ⚡ **HTTP API** | RESTful API on port `8765` — works from any language |
| 🔌 **WebSocket** | Real-time streaming on port `8766` — perfect for AI loops |

---

## 🖥️ Demo

```
$ desktop-use serve

 desktop_use server v0.1.0
============================================================
  HTTP API:     http://0.0.0.0:8765
  WebSocket:    ws://0.0.0.0:8766
  RapidOCR:     ON
  OpenCV:       ON
  FAILSAFE:     move mouse to top-left corner to abort
============================================================
```

**Health check:**
```json
$ curl http://localhost:8765/health
{
  "status": "ok",
  "version": "0.1.0",
  "uptime": 982.0,
  "ocr": true,
  "opencv": true,
  "pid": 28116
}
```

---

## 🚀 Quick Start

### 1. Install (on Windows)

```bash
pip install desktop-use
```

### 2. Start the Server (Windows)

```bash
# Run in Windows PowerShell or CMD (not WSL)
desktop-use serve
```

### 3. Run the Client (from WSL, Linux, or anywhere)

```python
from desktop_use.client import DesktopAgent

agent = DesktopAgent()  # connects to localhost:8765

# Take a screenshot + OCR
result = agent.screenshot(ocr=True)
print(f"Found {len(result['ocr'])} text items on screen")

# Find and click a button
result = agent.find_text("导入零件")
if result["success"]:
    x, y = result["data"]["center"]
    agent.click(x, y)
    print(f"Clicked at ({x}, {y})")

# Type text (bypasses IME — works with Chinese, Vietnamese, English)
agent.type_text("你好世界")

# Press hotkey
agent.hotkey("ctrl", "s")
```

That's it. You're controlling Windows.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    YOUR AI AGENT                        │
│            (WSL / Linux / Docker / Cloud)               │
│                                                         │
│   Python  ·  TypeScript  ·  curl  ·  Any HTTP client   │
└───────────────────────┬─────────────────────────────────┘
                        │
                   HTTP / WebSocket
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│              desktop-use SERVER (Windows)                │
│                    Port 8765 / 8766                      │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Screenshot   │  │  OCR Engine  │  │   Template   │  │
│  │  (mss)        │  │  (RapidOCR)  │  │  Matching    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Mouse &     │  │  Window Mgmt │  │  Clipboard   │  │
│  │  Keyboard    │  │  (pygetwin)  │  │  (PowerShell)│  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
               Windows Desktop / Apps
```

**Flow:** Your agent in WSL sends HTTP requests → desktop-use server on Windows executes native operations → results return as JSON.

---

## 📚 API Reference

All actions go through `POST /action` with a JSON body:

```bash
curl -X POST http://localhost:8765/action \
  -H "Content-Type: application/json" \
  -d '{"action": "click", "x": 100, "y": 200}'
```

### Screenshot

| Action | Parameters | Description |
|--------|-----------|-------------|
| `screenshot` | `name`, `ocr`, `base64`, `region` | Capture screen. `region`: `[x, y, w, h]` |
| `ocr` | `path`, `region` | OCR an image or screen region |
| `find_text` | `text`, `region` | Find text on screen, returns best match |
| `find_all_text` | `text`, `region` | Find all text matches |

### Template Matching

| Action | Parameters | Description |
|--------|-----------|-------------|
| `find_template` | `template`, `threshold`, `region` | Find template image on screen |
| `find_all_templates` | `template`, `threshold`, `region` | Find all instances |

Template images go in `templates/` folder (configurable via `DESKTOP_USE_DATA_DIR`).

### Mouse

| Action | Parameters | Description |
|--------|-----------|-------------|
| `click` | `x`, `y`, `button` | Click at coordinates. `button`: `left`/`right`/`middle` |
| `double_click` | `x`, `y` | Double click |
| `right_click` | `x`, `y` | Right click |
| `move` | `x`, `y`, `duration` | Move cursor |
| `drag` | `x1`, `y1`, `x2`, `y2`, `duration` | Drag from point to point |
| `get_mouse` | — | Get current cursor position |

### Keyboard

| Action | Parameters | Description |
|--------|-----------|-------------|
| `type` | `text` | Type text via clipboard paste (bypasses IME) |
| `hotkey` | `keys` | Press key combo, e.g. `["ctrl", "s"]` |
| `press` | `key`, `presses` | Press a single key |
| `scroll` | `amount`, `x`, `y` | Scroll (positive = up) |

### Window Management

| Action | Parameters | Description |
|--------|-----------|-------------|
| `focus_window` | `title` | Focus window by title keyword |
| `get_windows` | — | List all visible windows |
| `get_active` | — | Get active window title |
| `resize_window` | `title`, `width`, `height` | Resize window |
| `move_window` | `title`, `x`, `y` | Move window |

### Clipboard

| Action | Parameters | Description |
|--------|-----------|-------------|
| `clipboard_set` | `text` | Set clipboard text |
| `clipboard_get` | — | Get clipboard text |

### System

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | `GET` | Server health check |
| `/action` | `POST` | Execute any command (see above) |
| `/batch` | `POST` | Execute multiple commands: `{"commands": [...]}` |
| `/windows` | `GET` | List all windows |
| `/mouse` | `GET` | Mouse position |
| `/screen_size` | `GET` | Screen resolution |

---

## 🐍 Python Client Examples

### Basic Usage

```python
from desktop_use.client import DesktopAgent

agent = DesktopAgent()

# Screenshot + OCR
result = agent.screenshot(ocr=True)
for item in result["ocr"]:
    print(f"  {item['text']} at {item['center']}")

# Click at coordinates
agent.click(500, 300)

# Type text (clipboard paste — safe for Chinese/Vietnamese)
agent.type_text("Hello, desktop-use!")

# Press hotkey
agent.hotkey("ctrl", "s")

# Find text and click it
result = agent.find_text("Submit")
if result["success"]:
    agent.click(*result["data"]["center"])
```

### Template Matching Workflow

```python
from desktop_use.client import DesktopAgent

agent = DesktopAgent()

# Find the "Submit" button by image
result = agent.find_template("submit_button.png", threshold=0.85)

if result["success"]:
    x, y = result["data"]["center"]
    conf = result["data"]["confidence"]
    print(f"Found button at ({x}, {y}) with {conf:.1%} confidence")
    agent.click(x, y)
else:
    print("Button not found")
```

### AI Agent Loop

```python
from desktop_use.client import DesktopAgent

agent = DesktopAgent()

def agent_step(task: str) -> str:
    """One step of an AI agent loop."""

    # 1. See the screen
    result = agent.screenshot(ocr=True, base64=True)
    screenshot_b64 = result["base64"]
    ocr_text = "\n".join(item["text"] for item in result["ocr"])

    # 2. Ask the AI what to do next
    prompt = f"""Task: {task}
Screen text:
{ocr_text}
What action should I take? Reply JSON:
{{"action": "click|type|press|hotkey", "params": {{...}}}}"""

    # 3. Parse AI response (using your preferred LLM)
    # response = call_llm(prompt)
    # action = json.loads(response)

    # 4. Execute
    # agent.click(action["params"]["x"], action["params"]["y"])
    return "Step done"

for i in range(20):
    result = agent_step("Open Notepad and write hello world")
    print(f"Step {i+1}: {result}")
```

### Batch Commands (faster)

```python
from desktop_use.client import DesktopAgent

agent = DesktopAgent()

# Send multiple commands in one request — much faster
result = agent.batch([
    {"action": "focus_window", "title": "Notepad"},
    {"action": "type", "text": "Hello from desktop-use!"},
    {"action": "hotkey", "keys": ["ctrl", "s"]},
])

for step in result["data"]:
    print(f"  {step['cmd']}: {'✓' if step['result']['success'] else '✗'}")
```

---

## 🖥️ CLI Usage

```bash
# Start the server
desktop-use serve

# Start on custom port
desktop-use serve --port 9000

# Get help
desktop-use --help
```

**Client CLI:**

```bash
# Health check
python -m desktop_use.client health

# Screenshot
python -m desktop_use.client screenshot

# Screenshot + OCR
python -m desktop_use.client screenshot ocr

# Find text
python -m desktop_use.client find_text "Submit"

# Click
python -m desktop_use.client click 500 300

# Type text
python -m desktop_use.client type "Hello World"

# List windows
python -m desktop_use.client windows

# Focus window
python -m desktop_use.client focus "Notepad"
```

**curl examples:**

```bash
# Health
curl http://localhost:8765/health

# Click
curl -X POST http://localhost:8765/action \
  -d '{"action":"click","x":500,"y":300}'

# Find text
curl -X POST http://localhost:8765/action \
  -d '{"action":"find_text","text":"Submit"}'

# List windows
curl http://localhost:8765/windows
```

---

## ⚔️ Comparison

| Feature | **desktop-use** | Anthropic computer_use | OpenHands | PyAutoGUI |
|---------|:--------------:|:---------------------:|:---------:|:---------:|
| **Runs locally** | ✅ | ❌ (API only) | ✅ | ✅ |
| **HTTP API** | ✅ | ❌ | ❌ | ❌ |
| **WSL → Windows** | ✅ | ❌ | ❌ | ❌ |
| **OCR built-in** | ✅ | ✅ | ✅ | ❌ |
| **Template matching** | ✅ | ❌ | ❌ | ❌ |
| **Window management** | ✅ | Limited | Limited | ❌ |
| **WebSocket streaming** | ✅ | ❌ | ❌ | ❌ |
| **Works with any AI** | ✅ | Claude only | Multiple | ✅ |
| **Setup** | `pip install` | API key + sandbox | Docker | `pip install` |
| **Data leaves machine** | ❌ Never | ✅ Sent to API | ❌ | ❌ Never |
| **License** | MIT | Proprietary | Apache 2.0 | BSD |

> **TL;DR:** Anthropic's computer_use requires sending screenshots to their API. desktop-use gives you the same capabilities **entirely locally** with a clean HTTP interface any framework can use.

---

## 🤖 Integration with AI Agents

### Hermes Agent

```python
from desktop_use.client import DesktopAgent

agent = DesktopAgent()

# Hermes can now take actions:
screenshot = agent.screenshot()  # "See" the screen
text = agent.ocr()              # "Read" the screen
agent.click(x, y)               # "Act" on the screen
```

### Claude (Anthropic) — computer_use replacement

```python
from anthropic import Anthropic
from desktop_use.client import DesktopAgent

agent = DesktopAgent()
claude = Anthropic()

def claude_computer_use(task: str):
    """Use Claude with local desktop control."""

    for _ in range(25):
        # Get screen state locally
        result = agent.screenshot(ocr=True, base64=True)
        ocr_text = "\n".join(i["text"] for i in result["ocr"])

        response = claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Task: {task}\nScreen: {ocr_text}"},
                    {"type": "image", "source": {
                        "type": "base64", "media_type": "image/png",
                        "data": result["base64"],
                    }},
                ],
            }],
        )
        # Parse and execute Claude's suggested action
```

### LangChain

```python
from langchain.agents import initialize_agent, Tool
from desktop_use.client import DesktopAgent

agent = DesktopAgent()

tools = [
    Tool(name="screenshot", func=lambda _: str(agent.screenshot()["path"]),
         description="Take a screenshot"),
    Tool(name="read_screen", func=lambda _: str(agent.ocr()),
         description="Read all text on screen via OCR"),
    Tool(name="click", func=lambda coords: agent.click(*map(int, coords.split(","))),
         description="Click at x,y. Input: 'x,y'"),
    Tool(name="type_text", func=lambda text: agent.type_text(text),
         description="Type text on keyboard"),
]

# agent = initialize_agent(tools, llm, agent="zero-shot-react-description")
# agent.run("Open Notepad and type a poem")
```

---

## 📦 Installation

### From source

```bash
git clone https://github.com/dutuanan96/desktop-use.git
cd desktop-use
pip install -e ".[dev]"
```

### Requirements

- **Python** 3.10+
- **Windows** (server runs natively on Windows)
- **WSL/Linux** (client can run from anywhere)

### Dependencies (auto-installed)

`fastapi` · `uvicorn` · `pyautogui` · `mss` · `pygetwindow` · `rapidocr-onnxruntime` · `opencv-python` · `requests` · `websockets` · `pillow`

---

## 🧪 Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -v

# Lint
ruff check desktop_use/
ruff format --check desktop_use/
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with ❤️ for the AI agent community**

⭐ Star this repo if you find it useful!

</div>


## Virtual Display Setup (Optional)

For complete isolation (AI on separate screen), install Parsec Virtual Display:

### 1. Install Parsec
```cmd
winget install Parsec.Parsec
```

### 2. Enable Virtual Display
1. Open Parsec app
2. Go to Settings → Host
3. Enable "Virtual Display"
4. Set resolution (e.g., 1920x1080)

### 3. Use in Code
```python
from desktop_use.client import DesktopAgent

agent = DesktopAgent()

# Move Chrome to virtual display
agent.setup_workspace(["Chrome", "ERPNext"])

# Now AI works on virtual display, user works on physical display
# All screenshots and OCR will be from virtual display only
agent.screenshot(ocr=True)  # Captures virtual display
agent.click(100, 200, window_title="Chrome")  # Clicks on virtual display
```

### 4. How It Works
- Physical monitor: YOUR work
- Virtual monitor: AI's workspace
- AI uses PostMessage (cursor doesn't move)
- AI captures only virtual display region
- Complete isolation!

