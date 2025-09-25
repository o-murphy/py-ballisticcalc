#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "semver", "tomlkit"
# ]
# ///
import os
import re
import subprocess
from argparse import ArgumentParser
from pathlib import Path

import tomlkit


def is_semver(version: str) -> bool:
    """
    Checks if a string is a valid version according to a common PyPI/PEP 440-like format,
    allowing for 'b' (beta) pre-release identifiers without a hyphen.
    """
    # This regex is more lenient for pre-releases like 'bN' or 'rcN'
    # It allows formats like 1.0.0b1, 1.0.0rc1, as well as strict semver 1.0.0-alpha.1
    pep440_like_pattern = re.compile(
        r"^\d+\.\d+\.\d+(?:[abc]|rc|dev|post|a|b|f)?\d*(?:[.-]?\d+)?(?:[+-][0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
    )
    return bool(pep440_like_pattern.match(version))


def update_toml_version(file_path: Path, new_version: str, is_ext_file: bool = False, dry_run: bool = False):
    """
    Updates the 'project.version' in a TOML file and
    conditionally updates 'project.optional-dependencies.exts' for the main pyproject.toml.
    Preserves comments and formatting.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            doc = tomlkit.parse(f.read())

        cur_version = doc['project']['version']

        # Update project.version
        if 'project' in doc and 'version' in doc['project']:
            doc['project']['version'] = new_version
        else:
            print(f"Warning: 'project.version' not found in {file_path}. Skipping version update for this file.")

        # If it's the main pyproject.toml, update the 'exts' dependency as well
        if not is_ext_file:
            exts_path = ['project', 'optional-dependencies', 'exts']
            current_level = doc
            found_exts = True
            for i, key in enumerate(exts_path):
                if key in current_level:
                    current_level = current_level[key]
                else:
                    found_exts = False
                    break

            if found_exts:
                updated_exts_list = []
                for dep_str in current_level:
                    if dep_str.startswith('py_ballisticcalc.exts=='):
                        updated_exts_list.append(f'py_ballisticcalc.exts=={new_version}')
                    else:
                        updated_exts_list.append(dep_str)
                doc['project']['optional-dependencies']['exts'] = updated_exts_list
                print(f"New exts list in {file_path}: {updated_exts_list}")
            else:
                print(
                    f"Warning: 'project.optional-dependencies.exts' not found in {file_path}. Skipping exts dependency update.")

        if not dry_run:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(tomlkit.dumps(doc))

        print(f"Successfully updated versions in {file_path} from {cur_version} to {new_version}")

    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
    except Exception as e:
        print(f"An error occurred while processing {file_path}: {e}")


def update_uv_lock(file_path: Path) -> bool:
    _cur_dir = os.getcwd()
    _root = file_path.parent.absolute()
    _uv_lock = _root / "uv.lock"
    _uv_lock_posix = _uv_lock.as_posix()
    try:
        os.chdir(_root)
        subprocess.run(
            ['uv', 'sync'],
            capture_output=True,
            text=True,
            check=True
        )
        if not _uv_lock.exists():
            raise FileNotFoundError(_uv_lock_posix)
    except subprocess.CalledProcessError as e:
        print(f"Error syncing {_uv_lock_posix}: {e}")
        print(e.stderr)
        return False
    except OSError as e:
        print(f"Error: Could not update {_uv_lock_posix}: {e}")
        return False
    finally:
        os.chdir(_cur_dir)
    print(f"Successfully updated uv lock: {_uv_lock_posix}")
    return True


def is_git_working_tree_clean() -> bool:
    """Checks if the Git working tree is clean."""
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True,
            text=True,
            check=True
        )
        return not bool(result.stdout.strip())
    except subprocess.CalledProcessError as e:
        print(f"Error checking git status: {e}")
        print(e.stderr)
        return False
    except FileNotFoundError:
        print("Git command not found. Please ensure Git is installed and in your PATH.")
        return False


def git_commit_changes(version: str, files: list[Path]):
    """Adds specified files and commits them with a version bump message."""
    try:
        # Add files to staging area
        for f in files:
            subprocess.run(['git', 'add', str(f)], check=True)
            print(f"Added {f} to staging.")

        # Commit changes
        commit_message = f"chore: bump version to {version}"
        subprocess.run(['git', 'commit', '-m', commit_message], check=True)
        print(f"Committed changes with message: '{commit_message}'")
    except subprocess.CalledProcessError as e:
        print(f"Error during git commit: {e}")
        print(e.stderr)
    except FileNotFoundError:
        print("Git command not found. Please ensure Git is installed and in your PATH.")


def main():
    parser = ArgumentParser(description="Update versions in pyproject.toml files.")
    parser.add_argument('version', type=str, help='The new semantic version to set (e.g., 2.2.0b5).')
    parser.add_argument('--dry-run', action="store_true", help='Dry run: do not write files or commit.')
    parser.add_argument('--no-commit', action="store_true", help="Don't commit changes, even if working tree is clean.")

    args = parser.parse_args()
    version = args.version

    if not is_semver(version):
        parser.error(
            f"Version '{version}' is invalid. Please use a valid semantic versioning format (e.g., 1.0.0, 1.0.0-alpha, 1.0.0+build).")

    pyproject_toml = Path("pyproject.toml")
    bin_pyproject_toml = Path("py_ballisticcalc.exts", "pyproject.toml")

    files_to_update = [
        pyproject_toml,
        pyproject_toml.parent / 'uv.lock',
        bin_pyproject_toml,
        bin_pyproject_toml.parent / 'uv.lock',
    ]

    try:
        if args.dry_run:
            print("Dry run: Checking conditions and showing what would happen without modifying files or committing.")
            update_toml_version(pyproject_toml, version, is_ext_file=False, dry_run=True)
            update_toml_version(bin_pyproject_toml, version, is_ext_file=True, dry_run=True)
            print("Dry run complete. No files were changed, and no commit was made.")
            return  # Exit after dry run

        if not args.no_commit:
            # Case 1: no_commit is False (commit is allowed)
            if is_git_working_tree_clean():
                print("Working tree is clean. Proceeding to update files and commit.")
                update_toml_version(pyproject_toml, version, is_ext_file=False, dry_run=False)
                update_toml_version(bin_pyproject_toml, version, is_ext_file=True, dry_run=False)
                update_uv_lock(pyproject_toml)
                update_uv_lock(bin_pyproject_toml)
                git_commit_changes(version, files_to_update)
            else:
                print("Working tree is not clean. Skipping file updates and commit as --no-commit was not specified.")
                # IMPORTANT: No update_toml_version calls here, ensuring files are NOT touched.
        else:
            # Case 2: no_commit is True (only update files, never commit)
            print("Due to --no-commit flag, only updating files. Skipping commit.")
            update_toml_version(pyproject_toml, version, is_ext_file=False, dry_run=False)
            update_toml_version(bin_pyproject_toml, version, is_ext_file=True, dry_run=False)
            update_uv_lock(pyproject_toml)
            update_uv_lock(bin_pyproject_toml)

    except Exception as e:
        print(f"A general error occurred: {e}")


if __name__ == "__main__":
    main()
