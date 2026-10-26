"""CLI entrypoint to launch the Omnivore-to-Anki FastMCP server."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.mcp.server import mcp

if __name__ == "__main__":
    mcp.run()