from __future__ import annotations

from agent_pidgin.mcp_app import create_mcp_app


def main() -> None:
    app = create_mcp_app()
    app.run(transport="stdio")


if __name__ == "__main__":
    main()
