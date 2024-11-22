#!/usr/bin/env python3

import sqlite3
import argparse
import os
import sys


class Arguments:
    """
    Encapsulates command-line arguments and provides message filtering logic.
    """
    QUIET_LEVELS = {"info": 1, "warn": 2, "error": 3}

    def __init__(self, dry_run=False, missing_only=None, quiet=None, db_path=None, library_name=None, new_path=None):
        self.dry_run = dry_run
        self.missing_only = missing_only
        self.quiet_level = self.QUIET_LEVELS.get(quiet, 0)
        self.db_path = db_path
        self.library_name = library_name
        self.new_path = new_path

    @classmethod
    def from_args(cls, args=None):
        """
        Parses command-line arguments and initializes an Arguments instance.
        """
        parser = argparse.ArgumentParser(
            description="Manage directory paths for Lightroom libraries.",
            usage=(
                "%(prog)s <db_path> [library_name] [new_path] [--dry-run] "
                "[-q | --quiet {info,warn,error}]"
            )
        )
        parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without applying changes.")
        parser.add_argument(
            "-m", "--missing-only", action="store_true",
            help="List only libraries with missing paths."
        )
        parser.add_argument(
            "-q", "--quiet",
            choices=cls.QUIET_LEVELS.keys(),
            help="Suppress messages by level: 'info', 'warn', or 'error' (default: show all messages)."
        )
        parser.add_argument(
            "db_path", metavar="db_path", help="Path to the Lightroom Catalog file."
        )
        parser.add_argument(
            "library_name", metavar="library_name", nargs="?", help="Name of the library to display or update (optional)."
        )
        parser.add_argument(
            "new_path", metavar="new_path", nargs="?", help="New absolute path to set for the library (optional)."
        )

        parsed = parser.parse_args(args)
        return cls(
            dry_run=parsed.dry_run,
            missing_only=parsed.missing_only,
            quiet=parsed.quiet,
            db_path=parsed.db_path,
            library_name=parsed.library_name,
            new_path=parsed.new_path
        )

    def should_output(self, level):
        """
        Determines if a message of a given severity should be output based on the quiet level.
        """
        return self.QUIET_LEVELS.get(level, 0) > self.quiet_level


def log_message(message, arguments, level="info"):
    """
    Logs messages according to the quiet level.
    """
    if arguments.should_output(level):
        print(message, file=sys.stderr if level in ["warn", "error"] else sys.stdout)


def manage_library_folder(db_path, library_name, new_path, arguments):
    """
    Display or update directory paths for Lightroom libraries.
    """
    try:
        # Check if the database file exists
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Lightroom Catalog file '{db_path}' does not exist.")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        if library_name is None:
            # List all libraries and their paths
            cursor.execute("SELECT name, absolutePath, relativePathFromCatalog FROM AgLibraryRootFolder")
            libraries = cursor.fetchall()

            if not libraries:
                log_message("No libraries found in the catalog.", arguments, "warn")
                return 0

            log_message("Libraries and their paths:", arguments, "info")
            for name, absolute_path, relative_path in libraries:
                # Check if the directory exists
                path_exists = os.path.exists(absolute_path)
                if arguments.missing_only and path_exists:
                    continue  # Skip if path exists and missing-only flag is active

                missing_label = " (MISSING)" if not path_exists else ""
                relative_path_str = f', "{relative_path}"' if relative_path else ""
                log_message(f' - {name}: "{absolute_path}"{missing_label}{relative_path_str}', arguments, "info")
            return 0

        # Fetch library record(s)
        cursor.execute(
            "SELECT id_local, absolutePath, relativePathFromCatalog FROM AgLibraryRootFolder WHERE name = ?",
            (library_name,)
        )
        libraries = cursor.fetchall()

        if not libraries:
            raise ValueError(f"No libraries found with the name '{library_name}'.")

        if new_path is None:
            # List all matching libraries when no new path is provided
            log_message(f"Libraries matching '{library_name}':", arguments, "info")
            for _, absolute_path, relative_path in libraries:
                # Check if the directory exists
                path_status = " (MISSING)" if not os.path.exists(absolute_path) else ""
                relative_path_str = f', "{relative_path}"' if relative_path else ""
                log_message(f' - {library_name}: "{absolute_path}"{path_status} {relative_path_str}', arguments, "info")
            return 0

        if len(libraries) > 1:
            raise ValueError(
                f"Multiple libraries found with the name '{library_name}'. Update requires exactly one match."
            )

        # Single library record for updating
        library_id, absolute_path, relative_path = libraries[0]

        # Check if the new path exists
        if not os.path.exists(new_path):
            raise ValueError(f"New path '{new_path}' does not exist.")

        # Warn if relativePathFromCatalog is not empty
        if relative_path:
            log_message(
                f'Warning: Library "{library_name}" has a non-empty "relativePathFromCatalog" field.',
                arguments, "warn"
            )

        # Log changes
        log_message(
            f'Changing absolute path for "{library_name}": "{absolute_path}" -> "{new_path}"',
            arguments,
            "info"
        )

        if arguments.dry_run:
            log_message("Dry run: No changes made.", arguments, "info")
        else:
            # Perform the update
            cursor.execute(
                "UPDATE AgLibraryRootFolder SET absolutePath = ? WHERE id_local = ?",
                (new_path, library_id)
            )
            conn.commit()
            log_message("Changes applied successfully.", arguments, "info")

        return 0

    except (sqlite3.Error, FileNotFoundError, ValueError) as e:
        log_message(f"Error: {e}", arguments, "error")
        return 1
    except Exception as e:
        log_message(f"Unexpected error: {e}", arguments, "error")
        return 1
    finally:
        if 'conn' in locals():
            conn.close()


def main():
    try:
        # Parse arguments
        arguments = Arguments.from_args()

        # Call the main function
        result = manage_library_folder(
            db_path=arguments.db_path,
            library_name=arguments.library_name,
            new_path=arguments.new_path,
            arguments=arguments
        )
        sys.exit(result)
    except SystemExit:
        raise  # Allow argparse to handle system exit on --help
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
