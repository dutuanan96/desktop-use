"""Allow running as ``python -m desktop_use``."""

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="desktop-use",
        description="Desktop automation toolkit for AI agents",
    )
    parser.add_argument(
        "--version", action="version", version="%(prog)s 0.1.0"
    )
    sub = parser.add_subparsers(dest="command")

    serve = sub.add_parser("serve", help="Start the HTTP/WebSocket server")
    serve.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    serve.add_argument("--port", type=int, default=8765, help="HTTP port (default: 8765)")
    serve.add_argument("--ws-port", type=int, default=8766, help="WebSocket port (default: 8766)")

    args = parser.parse_args()

    if args.command == "serve":
        import os
        os.environ["DESKTOP_USE_HOST"] = args.host
        os.environ["DESKTOP_USE_HTTP_PORT"] = str(args.port)
        os.environ["DESKTOP_USE_WS_PORT"] = str(args.ws_port)
        from desktop_use.server import main as server_main
        server_main()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
