#!/usr/bin/env python3

import os
import sqlite3
import sys
import logging
from argparse import ArgumentParser
from typing import Optional, List, Tuple


class Arguments:
    """Parses and stores command-line arguments."""
    def __init__(self):
        parser = ArgumentParser(
            description="Utility to manage library folders in Lightroom catalogs."
        )
        parser.add_argument("catalog_path", help="Path to the Lightroom catalog file.")
        parser.add_argument(
            "library_name", nargs="?", help="Name of the library to inspect or update."
        )
        parser.add_argument(
            "new_path", nargs="?", help="New absolute path for the library."
        )
        parser.add_argument(
            "-m", "--missing-only", action="store_true",
            help="List only libraries with missing paths."
        )
        parser.add_argument("-d", "--dry-run", action="store_true", help="Perform a dry run (no changes made).")
        parser.add_argument(
            "-q", "--quiet", nargs="?", const="info", choices=["info", "warn", "error"],
            help="Suppress messages below the specified level. Defaults to 'info'."
        )

        self.args = parser.parse_args()

    @property
    def catalog_path(self) -> str:
        return self.args.catalog_path

    @property
    def library_name(self) -> Optional[str]:
        return self.args.library_name

    @property
    def new_path(self) -> Optional[str]:
        return self.args.new_path

    @property
    def missing_only(self) -> bool:
        return self.args.missing_only

    @property
    def dry_run(self) -> bool:
        return self.args.dry_run

    @property
    def quiet(self) -> Optional[str]:
        return self.args.quiet


def configure_logging(quiet: Optional[str]) -> None:
    """Configures the logging module based on verbosity level."""
    levels = {"info": logging.INFO, "warn": logging.WARNING, "error": logging.ERROR}
    logging_level = levels.get(quiet, logging.INFO)

    logging.basicConfig(
        level=logging_level,
        format="%(levelname)s: %(message)s"
    )


def validate_arguments(args: Arguments) -> None:
    """Validates the command-line arguments before processing.

    Args:
        args: Parsed command-line arguments.

    Raises:
        FileNotFoundError: If the catalog file or new path (if specified) does not exist.
        ValueError: If arguments conflict or are invalid.
    """
    if not os.path.exists(args.catalog_path):
        raise FileNotFoundError(f"Catalog file '{args.catalog_path}' does not exist.")

    if args.new_path and not os.path.exists(args.new_path):
        raise FileNotFoundError(f"New path '{args.new_path}' does not exist.")

    if args.missing_only and args.new_path:
        raise ValueError("Cannot use '--missing-only' when specifying a new path for a library update.")


def fetch_libraries(cursor: sqlite3.Cursor, library_name: Optional[str] = None) -> List[Tuple[int, str, str, str]]:
    """Fetches library records from the catalog.

    Args:
        cursor: SQLite cursor to execute queries.
        library_name: Name of the library to filter (optional).

    Returns:
        List of tuples containing library data.
    """
    query = "SELECT id_local, name, absolutePath, relativePathFromCatalog FROM AgLibraryRootFolder"
    if library_name:
        query += " WHERE name = ?"
        cursor.execute(query, (library_name,))
    else:
        cursor.execute(query)
    return cursor.fetchall()


def manage_library_folder(args: Arguments) -> int:
    """Main function to handle library folder management."""
    try:
        validate_arguments(args)  # Validate all arguments upfront

        with sqlite3.connect(args.catalog_path) as conn:
            cursor = conn.cursor()

            # Fetch libraries based on library_name argument
            libraries = fetch_libraries(cursor, args.library_name)

            if not libraries:
                logging.error(f"No libraries found with the name '{args.library_name}'.")
                return 1

            if args.library_name is None:
                # List all libraries
                missing_count = 0
                logging.info("Libraries and their paths:")
                for _, name, absolute_path, relative_path in libraries:
                    path_exists = os.path.exists(absolute_path)
                    if args.missing_only and path_exists:
                        continue

                    prefix = "*" if not path_exists else " "
                    if not path_exists:
                        missing_count += 1

                    relative_path_str = f', "{relative_path}"' if relative_path else ""
                    logging.info(f'{prefix}    {name}: "{absolute_path}"{relative_path_str}')

                if missing_count > 0 and not args.missing_only:
                    logging.info("\n* indicates missing directories.")
                return 0

            if args.new_path is None:
                # Display matching libraries
                logging.info(f"Libraries matching '{args.library_name}':")
                for _, name, absolute_path, relative_path in libraries:
                    path_exists = os.path.exists(absolute_path)
                    prefix = "*" if not path_exists else " "

                    relative_path_str = f', "{relative_path}"' if relative_path else ""
                    logging.info(f'{prefix}    {name}: "{absolute_path}"{relative_path_str}')
                return 0

            if len(libraries) > 1:
                logging.error(
                    f"Multiple libraries found with the name '{args.library_name}'. Update requires exactly one match."
                )
                return 1

            # Single library record for updating
            library_id, _, absolute_path, relative_path = libraries[0]

            logging.info(
                f'Changing absolute path for "{args.library_name}": "{absolute_path}" -> "{args.new_path}"'
            )

            if args.dry_run:
                logging.info("Dry run: No changes made.")
            else:
                cursor.execute(
                    "UPDATE AgLibraryRootFolder SET absolutePath = ? WHERE id_local = ?",
                    (args.new_path, library_id)
                )
                conn.commit()
                logging.info("Changes applied successfully.")

    except Exception as e:
        logging.error(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    args = Arguments()
    configure_logging(args.quiet)  # Configure logging before any output
    sys.exit(manage_library_folder(args))
