#!/usr/bin/env python3

import sqlite3
import argparse

def move_collection(db_path, collection_name, target_parent_name):
    """
    Move a collection to a new parent collection in the AgLibraryPublishedCollection database.

    Parameters:
    db_path (str): Path to the database file.
    collection_name (str): Name of the collection to move.
    target_parent_name (str): Name of the target parent collection.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Fetch collection record
        cursor.execute(
            "SELECT id_local, isDefaultCollection, genealogy FROM AgLibraryPublishedCollection WHERE name = ?",
            (collection_name,)
        )
        collections = cursor.fetchall()

        if len(collections) != 1:
            raise ValueError(f"Error: Found {len(collections)} records for collection '{collection_name}', expected exactly 1.")

        collection_id, is_default, collection_genealogy = collections[0]

        # Check if the collection is a default collection
        if is_default is not None and is_default == 1:
            print(f"Warning: Collection '{collection_name}' is marked as a default collection.")
            return

        # Fetch target parent collection record
        cursor.execute(
            "SELECT id_local, genealogy FROM AgLibraryPublishedCollection WHERE name = ?",
            (target_parent_name,)
        )
        parents = cursor.fetchall()

        if len(parents) != 1:
            raise ValueError(f"Error: Found {len(parents)} records for parent collection '{target_parent_name}', expected exactly 1.")

        parent_id, parent_genealogy = parents[0]

        # Construct new genealogy
        genealogy_parts = collection_genealogy.split('/') if collection_genealogy else []
        new_genealogy = f"{parent_genealogy}/{genealogy_parts[-1]}" if genealogy_parts else parent_genealogy

        # Perform a single update query
        cursor.execute(
            """
            UPDATE AgLibraryPublishedCollection
            SET parent = ?, genealogy = ?
            WHERE id_local = ?
            """,
            (parent_id, new_genealogy, collection_id)
        )
        # print(f"UPDATE AgLibraryPublishedCollection SET parent = {parent_id}, genealogy = '{new_genealogy}' WHERE id_local = {collection_id}")

        # Commit the changes
        conn.commit()
        print(f"Collection '{collection_name}' successfully moved under '{target_parent_name}'.")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except ValueError as ve:
        print(f"Validation error: {ve}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Move a collection to a new parent collection in the database.")
    parser.add_argument("db_path", type=str, help="Path to the database file.")
    parser.add_argument("collection_name", type=str, help="Name of the collection to move.")
    parser.add_argument("target_parent_name", type=str, help="Name of the target parent collection.")

    # Parse arguments
    args = parser.parse_args()

    # Execute the function
    move_collection(args.db_path, args.collection_name, args.target_parent_name)
