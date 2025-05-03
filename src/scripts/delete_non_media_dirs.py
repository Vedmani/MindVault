from mindvault.core.config import settings
import shutil
from pathlib import Path

media_dir = settings.media_dir

def delete_empty_or_json_only_dirs(root_dir: Path):
    """
    Deletes directories that are either empty or contain only JSON files.

    Args:
        root_dir (Path): The root directory to search within.
    """
    deleted_count = 0
    for item in root_dir.iterdir():
        if item.is_dir():
            contents = list(item.iterdir())

            if not contents:
                # Directory is empty
                print(f"Deleting empty directory: {item}")
                shutil.rmtree(item)
                deleted_count += 1
            else:
                json_only = all(f.name.endswith('.json') for f in contents)
                if json_only:
                    # Directory contains only JSON files
                    print(f"Deleting directory with only JSON files: {item}")
                    shutil.rmtree(item)
                    deleted_count += 1
                else:
                    # Recursively check subdirectories
                    deleted_count += delete_empty_or_json_only_dirs(item)
    return deleted_count

if __name__ == "__main__":
    deleted_dirs = delete_empty_or_json_only_dirs(media_dir)
    print(f"Total number of deleted directories: {deleted_dirs}")