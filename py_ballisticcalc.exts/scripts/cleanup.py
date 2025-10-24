import os
from pathlib import Path
import shutil

# Assuming this script is located in your project's root directory,
# where the .gitignore file would typically reside.
# If the script is elsewhere, adjust this path accordingly.
root_dir: Path = Path(__file__).parent.parent

# Unified list of cleanup patterns, mirroring .gitignore conventions.
# - Patterns starting with '/': Match a file only in the `root_dir` (non-recursive).
# - Patterns ending with '/': Match directories recursively (unless specifically rooted).
# - Other patterns: Match files recursively.
cleanup_patterns = [
    # Non-recursive files in root_dir (these were removed in your last update, keeping for reference if needed)
    # "/*.pyd",
    # "/*.c",
    # "/*.h",
    # "/*.html",
    "build/",  # Recursive directory (matches 'build' in root or any subdir)
    "dist/",  # Recursive directory (matches 'build' in root or any subdir)
    "*.egg-info/",  # Recursive directory
    # Fixed: Each pattern must be a separate string in the list, separated by a comma.
    "py_ballisticcalc_exts/*.c",  # Specific recursive file pattern for generated C files
    "py_ballisticcalc_exts/*.h",  # Specific recursive file pattern for generated header files
    "py_ballisticcalc_exts/*.html",  # Specific recursive file pattern for HTML files
    "py_ballisticcalc_exts/*.pyd",  # Specific recursive file pattern for Pyd files
]


def cleanup():
    print(f"Starting cleanup in: {root_dir}\n")

    # Iterate through each defined cleanup pattern
    for pattern in cleanup_patterns:
        is_directory_pattern = pattern.endswith("/")
        is_non_recursive_file_pattern = pattern.startswith("/") and not is_directory_pattern

        if is_non_recursive_file_pattern:
            # Handle non-recursive file patterns (e.g., "/my_file.txt")
            # We only look at direct children of root_dir
            file_name_pattern = pattern[1:]  # Remove the leading slash for matching

            print(f"Processing non-recursive file pattern: '{pattern}'")
            for path in root_dir.iterdir():  # Iterate only direct children
                if path.is_file() and path.name == file_name_pattern:  # Match by exact name (after stripping '/')
                    print(f"  Deleting file: {path.relative_to(root_dir)}")
                    try:
                        os.remove(path)
                    except OSError as e:
                        print(f"  Error deleting {path.relative_to(root_dir)}: {e}")
                    break  # Stop looking for this file once found and deleted
        elif is_directory_pattern:
            # Handle directory patterns (e.g., "build/", "*.egg-info/")
            dir_pattern = pattern[:-1]  # Remove trailing slash for matching

            print(f"Processing directory pattern: '{pattern}'")
            # rglob finds directories recursively
            # Note: rglob("build") will find any 'build' directory.
            # If you only wanted root 'build/', you'd need `if path == root_dir / "build":`
            for dir_path in root_dir.rglob(dir_pattern):
                if dir_path.is_dir():
                    print(f"  Deleting directory: {dir_path.relative_to(root_dir)}")
                    try:
                        shutil.rmtree(dir_path)
                    except OSError as e:
                        print(f"  Error deleting {dir_path.relative_to(root_dir)}: {e}")
        else:
            # Handle recursive file patterns (e.g., "*.pyd", "py_ballisticcalc_exts/*.c")
            # print(f"Processing recursive file pattern: '{pattern}'")
            print(f"Processing non-recursive file pattern: '{pattern}'")
            # for file_path in root_dir.rglob(pattern):
            for file_path in root_dir.glob(pattern):
                if file_path.is_file():
                    print(f"  Deleting file: {file_path.relative_to(root_dir)}")
                    try:
                        os.remove(file_path)
                    except OSError as e:
                        print(f"  Error deleting {file_path.relative_to(root_dir)}: {e}")


if __name__ == "__main__":
    cleanup()
