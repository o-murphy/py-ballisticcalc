"""
Mirror Cython sources to a stable location for coverage reporting.

This script:
1) Copies .pyx/.pxd from py_ballisticcalc.exts/py_ballisticcalc_exts/ to repo-root py_ballisticcalc_exts/
2) If present, also copies generated C files from the subproject build dir next to the mirrored sources,
   so the Cython coverage plugin can parse C comments to reconstruct original .pyx lines at report time.
"""

import os
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / 'py_ballisticcalc.exts' / 'py_ballisticcalc_exts'
MIRROR_DIR = REPO_ROOT / 'py_ballisticcalc_exts'

# Create mirror directory
MIRROR_DIR.mkdir(exist_ok=True)

copied = 0
# Copy all .pyx and .pxd files into top-level mirror so coverage can find sources
for ext in ('.pyx', '.pxd'):
    for src in SRC_DIR.glob(f'*{ext}'):
        dst = MIRROR_DIR / src.name
        shutil.copy2(src, dst)
        copied += 1

# Also copy generated C files from the build dir if they exist
BUILD_DIR = SRC_DIR / 'build' / 'py_ballisticcalc_exts'
if BUILD_DIR.exists():
    for c_src in BUILD_DIR.glob('*.c'):
        # 1) Place next to mirror .pyx
        dst = MIRROR_DIR / c_src.name
        shutil.copy2(c_src, dst)
        copied += 1
        # 2) Also place next to original .pyx inside the subproject source tree
        dst2 = SRC_DIR / c_src.name
        shutil.copy2(c_src, dst2)
        copied += 1

print(f"Synced {copied} files to {MIRROR_DIR}")
