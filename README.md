Scripts to fix Adobe Lightroom data that cannot be managed by the program itself.

[Adobe Lightroom Classic](https://www.adobe.com/products/photoshop-lightroom-classic.html) Catelogs can become unusable due to the program's inability to adjust to differences in how operating systems reference directories. This matters when you access or move `.lrcat` file between Windows and macOS.

The issue is in each operating system refers to file directories differently and Lightroom stores the directory references in Catalog files consistent with the operating system it is running under, at the time. But since Windows and macOS refer to directories differently, the references will cause errors or not recognize directory locations when the Catalog file is used on different operating system.

These scripts will allow the user to fix such problems by redefining the directory path names within the catalog files.

There are also situations that the Lightroom Classic interface does not allow certain capabilities, e.g., moving a collection from one publish service to another. In most common cases, that is just a data manipulation.

Before using these scripts, I recommend two things before doing anything which will modify the Catalog (`.lrcat`) file:
1. Close Lightroom Classic
2. Backup the Catalog (.lrcat) file

#### Notes
- Names of scripts are likely to change. Perhaps all functionality will be combined into a single script with sub-commands.
- Add script to list and update image Library's directory path

## move_collection

Moves a collection from one service to another. Lightroom does not allow you to move or copy a colletion... you have to recreate it in its new location. You can do this by exporting the definition importing it into the new location, but that is tedious.
```
move_collection {lrcat_file} {collection} {service}
```
- `lrcat_file` is the path the Lightroom Classic Catalog file
- `collection` is the name of a collection to be moved
- `service` is the service to move the collection to

options:
- `--quiet` [`info` | `warn` | `error`] suppress output
- `--dry-run` Run the script but don't actuallly make changes

returns:
- 0: Completed successfully
- 1: An error occurred during processing

#### Note
- Each service has a default-collection.

#### To Dos
- Allow default-collections to be moved
- If more than one collection of the same name exists, allow a way to specify the desired collection
- Allow the target collection's directory to be reset
- Allow re-definition of a collection's destination path
- Allow re-definition of a service's default root path
- List collections' paths
- List service's collections and their paths, noting its default collection

## library_folders

List and update image Library folder locations. This script will list the directory settings for the image Libraries and will allow the path to be changed for any library.

```
library_folders {lrcat_file} [library] [new_path]
```
- `lrcat_file` is the path the Lightroom Classic Catalog file
- `library` is the name of a library whose path to be updated. If `new_path` is not specified, the current value will be displayed. If not specified, all library values are displayed.
- `new_path` is the new path to be set for the library. If not specified, current values are diplayed.

options:
- `--quiet` [`info` | `warn` | `error`] suppress output
- `--dry-run` Run the script but don't actuallly make changes

returns:
- 0: Completed successfully
- 1: An error occurred during processing

#### To Dos
- Allow selection of specific library when there are more than one.