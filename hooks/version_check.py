#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "semver", "tomlkit", "tomli;python_version<'3.11'"
# ]
# ///
import sys
import os

import io 

try:
    import tomllib
except ImportError:
    import tomli as tomllib

pkg_name = 'py_ballisticcalc'
bin_pkg_name = 'py_ballisticcalc.exts'
version_pattern = r'(\d+)\.(\d+)\.(\d+)([ab]?)(\d*)\.?([a-zA-Z]+)?(\d*)'
pyproject_toml = "./pyproject.toml"
bin_pyproject_toml = "./py_ballisticcalc.exts/pyproject.toml"


def extract_dep_version(data, name):
    deps = data['project']['optional-dependencies']['exts']
    for dep in deps:
        _name, ver = dep.split("==")
        if _name.lower() == name.lower():
            return ver


# def extract_ver(name: str):
#     pkg_metadata = metadata(name)
#     pkg_ver = pkg_metadata.get('Version', None)
#     if pkg_ver is None:
#         raise Exception(f'{name} version is not defined')
#     match = re.match(version_pattern, pkg_ver)
#     if match:
#         # major, minor, patch, tag, build = match.groups()
#         return pkg_ver, match.groups()
#     else:
#         raise Exception(f"{name} can't extract version'")


def main():
    # --- FIX for UnicodeEncodeError on Windows ---
    # Force set sys.stdout and sys.stderr to UTF-8
    # for cp1252 on Windows.
    if sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
        except AttributeError:
            pass
    # --- END FIX ---
    
    # pkg_ver, groups = extract_ver(pkg_name)
    # bin_pkg_ver, bin_groups = extract_ver(bin_pkg_name)

    try:
        with open(pyproject_toml, 'rb') as f:
            pkg_toml = tomllib.load(f)

        with open(bin_pyproject_toml, 'rb') as f:
            bin_pkg_toml = tomllib.load(f)

        pkg_ver = pkg_toml['project']['version']
        bin_pkg_ver = bin_pkg_toml['project']['version']

        dep_ver = extract_dep_version(pkg_toml, bin_pkg_name)

        assert pkg_ver == bin_pkg_ver, f"❌ Versions don't match {pkg_name}=={pkg_ver} != {bin_pkg_name}=={bin_pkg_ver}"
        assert dep_ver == bin_pkg_ver, f"❌ Versions don't match {bin_pkg_name}=={bin_pkg_ver} != {dep_ver}"
        print("✅ Versions are matching")
    except AssertionError as err:
        raise err
    except Exception:
        raise Exception("❌ Could not parse versions")

if __name__ == '__main__':
    main()
