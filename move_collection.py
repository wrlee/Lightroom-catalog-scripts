import sqlite3

def move_collection(db_path, collection_name, target_parent_name):
    """
    Move a collection to a new parent collection.

    Parameters:
    db_path (str): Path to the database file.
    collection_name (str): Name of the collection to move.
    target_parent_name (str): Name of the target parent collection.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Fetch collection record
        cursor.execute("SELECT id_local, isDefaultCollection, genealogy FROM collections WHERE name = ?", (collection_name,))
        collection = cursor.fetchone()
        if not collection:
            print(f"Error: Collection '{collection_name}' not found.")
            return

        collection_id, is_default, collection_genealogy = collection

        # Check if the collection is a default collection
        if is_default is not None and is_default == 1:
            print(f"Warning: Collection '{collection_name}' is marked as a default collection.")
            return

        # Fetch target parent collection record
        cursor.execute("SELECT id_local, genealogy FROM collections WHERE name = ?", (target_parent_name,))
        parent = cursor.fetchone()
        if not parent:
            print(f"Error: Parent collection '{target_parent_name}' not found.")
            return

        parent_id, parent_genealogy = parent

        # Update the collection's parent
        cursor.execute("UPDATE collections SET parent = ? WHERE id_local = ?", (parent_id, collection_id))

        # Update the collection's genealogy field
        if collection_genealogy:
            genealogy_parts = collection_genealogy.split('/')
            new_genealogy = f"{parent_genealogy}/{genealogy_parts[-1]}"
            cursor.execute("UPDATE collections SET genealogy = ? WHERE id_local = ?", (new_genealogy, collection_id))

        # Commit the changes
        conn.commit()
        print(f"Collection '{collection_name}' successfully moved under '{target_parent_name}'.")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn:
            conn.close()


# Usage example
db_path = "your_database_file.db"  # Replace with the actual database path
collection_name = "example_collection"
target_parent_name = "new_parent_collection"

move_collection(db_path, collection_name, target_parent_name)
