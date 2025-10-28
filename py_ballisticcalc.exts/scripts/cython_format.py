import sys
import re
import argparse
from pathlib import Path


def cython_fmt(f: Path):
    """
    Performs basic formatting:
    1. Removes trailing whitespace from all lines.
    2. Removes lines that contain only whitespace or are completely empty.
    """
    try:
        with open(f, "r", encoding="utf-8") as fp:
            data = fp.read()
    except Exception as e:
        print(f"Error reading file {f}: {e}", file=sys.stderr)
        return

    # 1. Remove trailing whitespace (spaces/tabs at the end of a line)
    # The pattern r"[ \t]+$" matches one or more spaces/tabs ([ \t]+)
    # at the end of the line ($).
    # re.MULTILINE is necessary for $ to match the end of each line, not just the string.
    data = re.sub(r"[ \t]+$", "", data, flags=re.MULTILINE)

    # 2. Remove lines that contain only whitespace or are completely empty.
    # The pattern r"^\s*$" matches start of line, zero or more whitespace chars (including newlines), and end of line.
    data = re.sub(r"^\s*$", "", data, flags=re.MULTILINE)

    try:
        with open(f, "w", encoding="utf-8") as fp:
            fp.write(data)
        print(f"Formatting complete: {f}")
    except Exception as e:
        print(f"Error writing to file {f}: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="A simple formatter for Cython files (*.pyx, *.pxd).")
    # Accepts one or more paths (files or directories)
    parser.add_argument("input", type=Path, nargs="+", help="Paths to files or directories to format.")
    # Adds an option for recursive search
    parser.add_argument(
        "-r", "--recursive", action="store_true", help="Recursively search for files in subdirectories."
    )

    args = parser.parse_args()
    inputs: list[Path] = args.input
    is_recursive: bool = args.recursive

    # Patterns for Cython files
    cython_patterns = ["*.pyx", "*.pxd"]

    for item in inputs:
        if item.is_dir():
            print(f"Processing directory: {item}")
            # Use rglob() for recursive search or glob() for non-recursive
            search_method = item.rglob if is_recursive else item.glob

            # Search for files using each pattern
            found_files = []
            for pattern in cython_patterns:
                found_files.extend(search_method(pattern))

            if not found_files:
                print(f"  Files *.pyx, *.pxd not found {'recursively' if is_recursive else ''} in {item}.")

            for f in found_files:
                cython_fmt(f)

        elif item.is_file():
            # Check if the file has the correct extension
            if item.suffix in [".pyx", ".pxd"]:
                cython_fmt(item)
            else:
                print(f"Skipping file {item}: not a *.pyx or *.pxd file.")

        else:
            print(f"Path does not exist or is neither a file nor a directory: {item}", file=sys.stderr)


if __name__ == "__main__":
    main()
