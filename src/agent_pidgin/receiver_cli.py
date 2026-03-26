import logging
import os
import sys
from __future__ import annotations

from agent_pidgin.mcp_app import create_mcp_app


def main() -> None:
    # Use VERBOSE=1 or --verbose to enable debug logging
    log_level = logging.DEBUG if os.environ.get("VERBOSE") == "1" or "--verbose" in sys.argv else logging.INFO

    # Configure logging to stderr to avoid interfering with MCP stdio transport
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )

    app = create_mcp_app()
    app.run(transport="stdio")


if __name__ == "__main__":
    main()
