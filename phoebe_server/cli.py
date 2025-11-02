"""Command-line interface."""

import argparse
import uvicorn
from .config import config
from . import database


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="PHOEBE Server")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run the server")
    run_parser.add_argument("--host", default=config.server.host, help="Host to bind to")
    run_parser.add_argument("--port", type=int, default=config.server.port, help="Port to bind to")
    run_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    # Init database command
    init_db_parser = subparsers.add_parser("init-db", help="Initialize the database")
    init_db_parser.add_argument("--force", action="store_true", help="Reinitialize even if database exists")

    args = parser.parse_args()

    if args.command == "run":
        uvicorn.run(
            "phoebe_server.main:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
        )
    elif args.command == "init-db":
        from pathlib import Path
        db_path = Path(config.database.path)

        if db_path.exists() and not args.force:
            print(f"Database already exists at {db_path}")
            print("Use --force to reinitialize")
            return

        database.init_database()
        print(f"Database initialized at {db_path}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
