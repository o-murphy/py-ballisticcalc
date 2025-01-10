# import re
# from importlib_metadata import metadata

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


if __name__ == '__main__':
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

        assert pkg_ver != bin_pkg_ver, f"Versions don't match {pkg_name}=={pkg_ver} != {bin_pkg_name}=={bin_pkg_ver}"
        assert dep_ver == bin_pkg_ver, f"Versions don't match {bin_pkg_name}=={bin_pkg_ver} != {dep_ver}"
    except AssertionError as err:
        raise err
    except Exception:
        raise Exception("Could not parse versions")
