<div align="center">

# 🖥️ desktop-use

**Turn any AI agent into a desktop power user — control Windows from anywhere**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%2F%20WSL-orange)](#)
[![PyPI](https://img.shields.io/badge/pip%20install-desktop--use-purple)](https://pypi.org/project/desktop-use/)
[![Downloads](https://img.shields.io/pypi/dm/desktop-use)](https://pypi.org/project/desktop-use/)
[![Build](https://img.shields.io/badge/build-passing-brightgreen)](#)

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
| 📸 **Screenshot** | Capture full screen or specific regions as PNG/BMP |
| 🔍 **OCR** | Extract text from any screen region (RapidOCR — no API key needed) |
| 🎯 **Template Matching** | Find UI elements by image template (OpenCV-powered) |
| 🖱️ **Mouse Control** | Click, double-click, right-click, drag, scroll at any coordinate |
| ⌨️ **Keyboard Control** | Type text, press hotkeys, hold modifiers |
| 🪟 **Window Management** | Find, focus, move, resize, minimize, maximize windows |
| 📋 **Clipboard** | Read and write the system clipboard |
| ⚡ **HTTP API** | RESTful API on port `8765` — works from any language |
| 🔌 **WebSocket** | Real-time streaming on port `8766` — perfect for AI loops |

---

## 🖥️ Demo

```
 ██╗    ██╗ ██████╗ █████╗ ███████╗████████╗
 ██║    ██║██╔════╝██╔══██╗██╔════╝╚══██╔══╝
 ██║ █╗ ██║██║     ███████║███████╗   ██║
 ██║███╗██║██║     ██╔══██║╚════██║   ██║
 ╚███╔███╔╝╚██████╗██║  ██║███████║   ██║
  ╚══╝╚══╝  ╚═════╝╚═╝  ╚═╝╚══════╝   ╚═╝
   desktop-use v5.0 — AI-Powered Desktop Control
```

**Server startup:**
```
$ desktop-use-server
🖥️  desktop-use server v5.0
├── HTTP API:  http://localhost:8765
├── WebSocket: ws://localhost:8766
└── Ready.
```

**Health check:**
```
$ curl http://localhost:8765/health
{
  "status": "ok",
  "version": "5.0",
  "uptime": 982.0,
  "ocr": true,
  "opencv": true,
  "pid": 28116
}
```

---

## 🚀 Quick Start

### 1. Install

```bash
pip install desktop-use
```

### 2. Start the Server (Windows)

```bash
# Run in Windows PowerShell or CMD (not WSL)
desktop-use-server
```

```
🖥️  desktop-use server v0.1.0
├── HTTP API:  http://localhost:8765
├── WebSocket: ws://localhost:8766
└── Ready.
```

### 3. Run the Client (from WSL, Linux, or anywhere)

```python
from desktop_use import DesktopClient

client = DesktopClient("http://localhost:8765")

# Take a screenshot
screenshot = client.screenshot()
screenshot.save("screen.png")

# Find and click a button
template = client.find_template("submit_button.png")
if template:
    client.click(template.x, template.y)
    print("Clicked submit!")
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
│  │  (PIL/GDI+)  │  │  (RapidOCR)  │  │  Matching    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Mouse &     │  │  Window Mgmt │  │  Clipboard   │  │
│  │  Keyboard    │  │  (Win32 API)  │  │  (Win32)     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
               Windows Desktop / Apps
```

**Flow:** Your agent in WSL sends HTTP requests → desktop-use server on Windows executes native Win32 operations → results return as JSON.

---

## 📚 API Reference

### Screenshot

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/screenshot` | `GET` | Full-screen capture (returns PNG) |
| `/screenshot?region=x,y,w,h` | `GET` | Capture specific region |
| `/screenshot/base64` | `GET` | Full-screen as base64 JSON |

### OCR

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ocr` | `GET` | OCR entire screen |
| `/ocr?region=x,y,w,h` | `GET` | OCR specific region |
| `/ocr?region=x,y,w,h&lang=en` | `GET` | OCR with language hint |

### Template Matching

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/find?template=name.png` | `GET` | Find template on screen, returns `{x, y, confidence}` |
| `/find?template=name.png&threshold=0.8` | `GET` | Find with custom confidence threshold |
| `/find/all?template=name.png` | `GET` | Find all matches on screen |
| `/find?template=name.png&region=x,y,w,h` | `GET` | Find template in specific region |

### Mouse

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/click?x=100&y=200` | `POST` | Left click at coordinates |
| `/click?x=100&y=200&button=right` | `POST` | Right click |
| `/click?x=100&y=200&button=middle` | `POST` | Middle click |
| `/doubleclick?x=100&y=200` | `POST` | Double click |
| `/mousedown?x=100&y=200` | `POST` | Mouse button down |
| `/mouseup?x=100&y=200` | `POST` | Mouse button up |
| `/drag?x1=100&y1=200&x2=300&y2=400` | `POST` | Drag from point to point |
| `/scroll?x=100&y=200&delta=3` | `POST` | Scroll (positive = up, negative = down) |
| `/move?x=100&y=200` | `POST` | Move cursor without clicking |
| `/position` | `GET` | Get current cursor position |

### Keyboard

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/type?text=hello` | `POST` | Type text string |
| `/type?text=hello&interval=50` | `POST` | Type with delay between chars (ms) |
| `/press?key=enter` | `POST` | Press a single key |
| `/press?key=ctrl+c` | `POST` | Press key combination |
| `/press?key=ctrl+shift+s` | `POST` | Multi-modifier combo |
| `/keydown?key=shift` | `POST` | Hold key down |
| `/keyup?key=shift` | `POST` | Release key |
| `/hotkey?keys=ctrl+alt+delete` | `POST` | Simultaneous key press |

### Window Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/windows` | `GET` | List all visible windows |
| `/windows?title=Notepad` | `GET` | Find window by title (partial match) |
| `/window/focus?title=Notepad` | `POST` | Focus/bring window to front |
| `/window/move?title=Notepad&x=0&y=0&w=800&h=600` | `POST` | Move and resize window |
| `/window/minimize?title=Notepad` | `POST` | Minimize window |
| `/window/maximize?title=Notepad` | `POST` | Maximize window |
| `/window/close?title=Notepad` | `POST` | Close window |
| `/window/screenshot?title=Notepad` | `GET` | Screenshot of specific window |

### Clipboard

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/clipboard` | `GET` | Get clipboard text |
| `/clipboard?text=hello` | `POST` | Set clipboard text |
| `/clipboard/clear` | `POST` | Clear clipboard |

### System

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | `GET` | Server health check |
| `/info` | `GET` | Server version and capabilities |

---

## 🐍 Python Client Examples

### Basic Usage

```python
from desktop_use import DesktopClient

client = DesktopClient("http://localhost:8765")

# Screenshot
screenshot = client.screenshot()
screenshot.save("desktop.png")

# OCR — extract all text from screen
text = client.ocr()
print(text)

# Click a button at specific coordinates
client.click(500, 300)

# Type something
client.type("Hello, desktop-use!")

# Press a hotkey
client.hotkey("ctrl", "s")
```

### Template Matching Workflow

```python
from desktop_use import DesktopClient

client = DesktopClient("http://localhost:8765")

# Find the "Submit" button on screen
result = client.find_template("submit_button.png", threshold=0.85)

if result:
    print(f"Found button at ({result.x}, {result.y}) with {result.confidence:.1%} confidence")
    client.click(result.x, result.y)
else:
    print("Button not found — taking screenshot for debug")
    client.screenshot().save("debug.png")
```

### AI Agent Loop

```python
from desktop_use import DesktopClient
import json

client = DesktopClient("http://localhost:8765")

def agent_step(task_description: str) -> str:
    """One step of an AI agent loop."""

    # 1. See the screen
    screenshot_b64 = client.screenshot_base64()

    # 2. Read what's on screen
    ocr_text = client.ocr()

    # 3. Ask the AI what to do next
    prompt = f"""You are controlling a Windows desktop.
Task: {task_description}

Current screen text (OCR):
{ocr_text}

What action should I take next? Reply with JSON:
{{"action": "click|type|press|hotkey", "params": {{...}}}}"""

    # 4. Parse AI response (using your preferred LLM)
    # response = call_llm(prompt)
    # action = json.loads(response)

    # 5. Execute the action
    # client.execute(action)
    return "Action executed"

# Run the loop
for i in range(20):
    result = agent_step("Open Notepad and write a hello world program")
    print(f"Step {i+1}: {result}")
```

---

## 🖥️ CLI Usage

```bash
# Start the server
desktop-use-server

# Start on custom port
desktop-use-server --port 9000

# Start with WebSocket enabled
desktop-use-server --ws-port 8766

# Start with verbose logging
desktop-use-server --debug

# Get help
desktop-use-server --help
```

**Quick client from terminal (curl examples):**

```bash
# Health check
curl http://localhost:8765/health

# Screenshot → save to file
curl -o screenshot.png http://localhost:8765/screenshot

# OCR → get text
curl http://localhost:8765/ocr

# Click at coordinates
curl -X POST "http://localhost:8765/click?x=500&y=300"

# Type text
curl -X POST "http://localhost:8765/type?text=Hello+World"

# Press hotkey
curl -X POST "http://localhost:8765/hotkey?keys=ctrl+c"

# List windows
curl http://localhost:8765/windows

# Find template
curl "http://localhost:8765/find?template=button.png"
```

---

## ⚔️ Comparison

| Feature | **desktop-use** | Anthropic computer_use | OpenHands | PyAutoGUI |
|---------|:--------------:|:---------------------:|:---------:|:---------:|
| **Runs locally** | ✅ | ❌ (API only) | ✅ | ✅ |
| **HTTP API** | ✅ | ❌ | ❌ | ❌ |
| **WSL / Linux → Windows** | ✅ | ❌ | ❌ | ❌ |
| **OCR built-in** | ✅ | ✅ | ✅ | ❌ |
| **Template matching** | ✅ | ❌ | ❌ | ❌ |
| **Window management** | ✅ | Limited | Limited | ❌ |
| **WebSocket streaming** | ✅ | ❌ | ❌ | ❌ |
| **Works with any AI** | ✅ | Claude only | Multiple | ✅ |
| **Setup complexity** | `pip install` | API key + sandbox | Docker | `pip install` |
| **Offline / air-gapped** | ✅ | ❌ | Partial | ✅ |
| **Data leaves machine** | ❌ Never | ✅ Sent to API | ❌ | ❌ Never |
| **License** | MIT | Proprietary | Apache 2.0 | BSD |

> **TL;DR:** Anthropic's computer_use is powerful but requires sending screenshots to their API. desktop-use gives you the same capabilities **entirely locally** with a clean HTTP interface any framework can use.

---

## 🤖 Integration with AI Agents

### Hermes Agent

```python
# Use desktop-use as a Hermes tool
from desktop_use import DesktopClient

client = DesktopClient("http://localhost:8765")

# Hermes can now take actions:
screenshot = client.screenshot()  # "See" the screen
text = client.ocr()              # "Read" the screen
client.click(x, y)              # "Act" on the screen
```

### Claude (Anthropic) — computer_use replacement

```python
from anthropic import Anthropic
from desktop_use import DesktopClient

client = DesktopClient("http://localhost:8765")
claude = Anthropic()

def claude_computer_use(task: str):
    """Use Claude with local desktop control — no Anthropic computer_use API needed."""

    for _ in range(25):
        # Get screen state locally (no data sent to Anthropic except prompt)
        screenshot_b64 = client.screenshot_base64()
        ocr_text = client.ocr()

        response = claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Task: {task}\nScreen text: {ocr_text}"},
                    {"type": "image", "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": screenshot_b64,
                    }},
                ],
            }],
        )

        # Parse and execute Claude's suggested action
        # action = parse_claude_response(response)
        # client.execute(action)
```

### LangChain

```python
from langchain.agents import initialize_agent, Tool
from desktop_use import DesktopClient

client = DesktopClient("http://localhost:8765")

# Define tools for LangChain
tools = [
    Tool(name="screenshot", func=lambda _: str(client.screenshot_base64())[:50],
         description="Take a screenshot of the current desktop"),
    Tool(name="read_screen", func=lambda _: client.ocr(),
         description="Read all text on screen via OCR"),
    Tool(name="click", func=lambda coords: client.click(*map(int, coords.split(","))),
         description="Click at x,y coordinates. Input: 'x,y'"),
    Tool(name="type_text", func=lambda text: client.type(text),
         description="Type text on the keyboard"),
]

agent = initialize_agent(tools, llm, agent="zero-shot-react-description")
agent.run("Open Notepad and type a poem")
```

### OpenAI Function Calling

```python
import openai
from desktop_use import DesktopClient

client = DesktopClient("http://localhost:8765")

tools = [
    {
        "type": "function",
        "function": {
            "name": "screenshot",
            "description": "Capture the current desktop screen",
            "parameters": {},
        }
    },
    {
        "type": "function",
        "function": {
            "name": "click",
            "description": "Click at specific screen coordinates",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate"},
                    "y": {"type": "integer", "description": "Y coordinate"},
                },
                "required": ["x", "y"],
            },
        }
    },
]

# Then use with openai.chat.completions.create(tools=tools, ...)
```

---

## 🤝 Contributing

Contributions are welcome! Here's how to get started:

1. **Fork** the repository
2. **Clone** your fork: `git clone https://github.com/YOUR_USERNAME/desktop-use.git`
3. **Create** a branch: `git checkout -b feature/awesome-feature`
4. **Install** dev dependencies: `pip install -e ".[dev]"`
5. **Make** your changes
6. **Test** your changes: `pytest tests/`
7. **Commit** and **push**: `git push origin feature/awesome-feature`
8. **Open** a Pull Request

### Ideas for contributions:
- 🐛 Bug fixes and issue reports
- 📸 New screenshot formats (JPEG, WebP)
- 🔍 Additional OCR languages
- 🪟 Cross-platform support (macOS, Linux native)
- 📖 Documentation improvements
- 🧪 More test coverage
- 🔌 Plugin system for custom actions

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

```
MIT License

Copyright (c) 2025 An Du

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

<div align="center">

**Made with ❤️ by [An Du](https://github.com/dutuanan96)**

⭐ If this project helps you, please give it a star — it motivates continued development!

</div>
