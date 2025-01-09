import os
from pathlib import Path


def cleanup():
    root_dir = Path("./py_ballisticcalc.exts")
    for path in root_dir.rglob("*"):  # Matches all files and directories recursively
        if path.is_file():
            if path.suffix in {".pyd", ".c", ".html"}:
                print(path)
                try:
                    os.remove(path)
                except IOError:
                    pass


if __name__ == "__main__":
    cleanup()
