#!/usr/bin/env python3

import sqlite3
import argparse
import os
import sys


class Options:
    """
    Encapsulates command-line options and provides message filtering logic.
    """
    QUIET_LEVELS = {"none": 0, "info": 1, "warn": 2, "error": 3}

    def __init__(self, dry_run=False, quiet="none"):
        self.dry_run = dry_run
        self.quiet_level = self.QUIET_LEVELS[quiet]

    @classmethod
    def from_args(cls, args=None):
        """
        Parses command-line options and initializes an Options instance.
        """
        parser = argparse.ArgumentParser(
            description="Collection utility to move between Publish services."
        )
        parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without applying changes.")
        parser.add_argument(
            "-q", "--quiet",
            nargs="?",
            const="info",  # Default to 'info' if no value is provided
            choices=cls.QUIET_LEVELS.keys(),
            help="Suppress messages by level: 'info', 'warn', or 'error' (default: 'info' if no value is given)."
        )
        parser.add_argument(
            "positional_args",
            nargs=argparse.REMAINDER,
            help="Positional arguments to be passed to the script."
        )
        parsed = parser.parse_args(args)
        return cls(dry_run=parsed.dry_run, quiet=parsed.quiet or "none"), parsed.positional_args

    def should_output(self, level):
        """
        Determines if a message of a given severity should be output based on the quiet level.
        """
        return self.QUIET_LEVELS[level] > self.quiet_level


def log_message(message, options, level="info"):
    """
    Logs messages according to the quiet level.
    """
    if options.should_output(level):
        print(message, file=sys.stderr if level in ["warn", "error"] else sys.stdout)


def move_collection(db_path, collection_name, target_parent_name, options):
    """
    Move a collection to a new parent collection in the AgLibraryPublishedCollection database.
    """
    try:
        # Check if the database file exists
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database file '{db_path}' does not exist.")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Fetch collection record
        cursor.execute(
            "SELECT id_local, isDefaultCollection, genealogy FROM AgLibraryPublishedCollection WHERE name = ?",
            (collection_name,)
        )
        collections = cursor.fetchall()

        if len(collections) != 1:
            raise ValueError(
                f"Found {len(collections)} records for collection '{collection_name}', expected exactly 1."
            )

        collection_id, is_default, collection_genealogy = collections[0]

        # Check if the collection is a default collection
        if is_default is not None and is_default == 1:
            raise ValueError(f"Collection '{collection_name}' is marked as a default collection.")

        # Fetch target parent collection record
        cursor.execute(
            "SELECT id_local, genealogy FROM AgLibraryPublishedCollection WHERE name = ?",
            (target_parent_name,)
        )
        parents = cursor.fetchall()

        if len(parents) != 1:
            raise ValueError(
                f"Found {len(parents)} records for parent collection '{target_parent_name}', expected exactly 1."
            )

        parent_id, parent_genealogy = parents[0]

        # Construct new genealogy
        genealogy_parts = collection_genealogy.split('/') if collection_genealogy else []
        new_genealogy = f"{parent_genealogy}/{genealogy_parts[-1]}" if genealogy_parts else parent_genealogy

        log_message(f"Preparing to move collection '{collection_name}' under '{target_parent_name}'.", options, "info")
        log_message(f" - Current parent: {collection_genealogy or 'None'}", options, "info")
        log_message(f" - New parent: {parent_genealogy}", options, "info")
        log_message(f" - New genealogy: {new_genealogy}", options, "info")

        if options.dry_run:
            log_message("Dry run: No changes made.", options, "info")
        else:
            # Perform a single update query
            cursor.execute(
                """
                UPDATE AgLibraryPublishedCollection
                SET parent = ?, genealogy = ?
                WHERE id_local = ?
                """,
                (parent_id, new_genealogy, collection_id)
            )
            conn.commit()
            log_message("Changes applied successfully.", options, "info")

        return 0

    except (sqlite3.Error, FileNotFoundError, ValueError) as e:
        log_message(f"Error: {e}", options, "error")
        return 1
    except Exception as e:
        log_message(f"Unexpected error: {e}", options, "error")
        return 1
    finally:
        if 'conn' in locals():
            conn.close()


def main():
    # Parse options and remaining arguments
    options, remaining_args = Options.from_args()

    if len(remaining_args) < 3:
        print(
            "Usage: move_collection.py <db_path> <collection_name> <target_parent_name> [--dry-run] [-q | --quiet]",
            file=sys.stderr
        )
        sys.exit(1)

    # Positional arguments
    db_path = remaining_args[0]
    collection_name = remaining_args[1]
    target_parent_name = remaining_args[2]

    # Call the main function
    result = move_collection(db_path, collection_name, target_parent_name, options)
    sys.exit(result)


if __name__ == "__main__":
    main()
