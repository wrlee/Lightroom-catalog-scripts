#!/usr/bin/env python3

import sqlite3
import argparse
import os
import sys


class Options:
    """
    Encapsulates command-line options and provides message filtering logic.
    """
    QUIET_LEVELS = {"info": 1, "warn": 2, "error": 3}

    def __init__(self, dry_run=False, quiet=None):
        self.dry_run = dry_run
        self.quiet_level = self.QUIET_LEVELS.get(quiet, 0)  # Default to 'none' behavior (0) if quiet is None.

    @classmethod
    def from_args(cls, args=None):
        """
        Parses command-line options and initializes an Options instance.
        """
        parser = argparse.ArgumentParser(
            description="Collection utility to move between Publish services.",
            usage="%(prog)s <db_path> <collection_name> <target_publish_service> [--dry-run] [-q | --quiet {info,warn,error}]"
        )
        parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without applying changes.")
        parser.add_argument(
            "-q", "--quiet",
            choices=cls.QUIET_LEVELS.keys(),
            help="Suppress messages by level: 'info', 'warn', or 'error' (default: show all messages)."
        )
        parser.add_argument(
            "db_path", metavar="db_path", help="Path to the SQLite database file."
        )
        parser.add_argument(
            "collection_name", metavar="collection_name", help="Name of the collection to be moved."
        )
        parser.add_argument(
            "target_publish_service", metavar="target_publish_service", help="Name of the target Publish service."
        )

        parsed = parser.parse_args(args)
        return cls(dry_run=parsed.dry_run, quiet=parsed.quiet), parsed

    def should_output(self, level):
        """
        Determines if a message of a given severity should be output based on the quiet level.
        """
        return self.QUIET_LEVELS.get(level, 0) > self.quiet_level


def log_message(message, options, level="info"):
    """
    Logs messages according to the quiet level.
    """
    if options.should_output(level):
        print(message, file=sys.stderr if level in ["warn", "error"] else sys.stdout)


def move_collection(db_path, collection_name, target_publish_service, options):
    """
    Move a collection to a new Publish service in the AgLibraryPublishedCollection database.
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

        # Fetch target Publish service record
        cursor.execute(
            "SELECT id_local, genealogy FROM AgLibraryPublishedCollection WHERE name = ?",
            (target_publish_service,)
        )
        services = cursor.fetchall()

        if len(services) != 1:
            raise ValueError(
                f"Found {len(services)} records for Publish service '{target_publish_service}', expected exactly 1."
            )

        service_id, service_genealogy = services[0]

        # Construct new genealogy
        genealogy_parts = collection_genealogy.split('/') if collection_genealogy else []
        new_genealogy = f"{service_genealogy}/{genealogy_parts[-1]}" if genealogy_parts else service_genealogy

        log_message(f"Preparing to move collection '{collection_name}' under Publish service '{target_publish_service}'.", options, "info")
        log_message(f" - Current parent: {collection_genealogy or 'None'}", options, "info")
        log_message(f" - New parent: {service_genealogy}", options, "info")
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
                (service_id, new_genealogy, collection_id)
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
    try:
        # Parse options and arguments
        options, args = Options.from_args()

        # Call the main function
        result = move_collection(args.db_path, args.collection_name, args.target_publish_service, options)
        sys.exit(result)
    except SystemExit:
        raise  # Allow argparse to handle system exit on --help
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
