#!/usr/bin/env python3
"""Generate formatted GitHub release notes from CHANGELOG.md.

Usage:
    python scripts/gen_release_notes.py <version> <repo> [changelog]

Supports optional sections in CHANGELOG.md within a version/Unreleased block:

    ## [Unreleased]

    > One-line description shown below the release title.

    ### Upgrade Notes
    Backward-compatibility notes, migration steps, etc.

    ### Changed
    - ...

    ### Fixed
    - ...
"""

import re
import subprocess
import sys
from pathlib import Path


def extract_section(text: str, version: str) -> str:
    escaped = re.escape(version)
    patterns = [
        rf"^## \[?v?{escaped}\]?(?:\s|$)",
        r"^## \[?[Uu]nreleased\]?(?:\s|$)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.MULTILINE)
        if not m:
            continue
        # skip the rest of the matched header line
        nl = text.find("\n", m.start())
        start = nl + 1 if nl != -1 else m.end()
        next_m = re.search(r"^## ", text[start:], re.MULTILINE)
        end = start + next_m.start() if next_m else len(text)
        section = text[start:end].strip()
        if section:
            return section
    return ""


def parse_intro(section: str) -> str:
    for line in section.splitlines():
        if line.startswith(">"):
            return line.lstrip(">").strip()
    return ""


def parse_subsection(section: str, name: str) -> str:
    m = re.search(rf"^### {re.escape(name)}\s*$", section, re.MULTILINE)
    if not m:
        return ""
    start = m.end()
    next_m = re.search(r"^### ", section[start:], re.MULTILINE)
    end = start + next_m.start() if next_m else len(section)
    return section[start:end].strip()


_CHANGELOG_NOISE = re.compile(r"^\[!\[|^\[:[a-z]")  # badges, mkdocs snippets


def parse_highlights(section: str) -> str:
    lines, skip = [], False
    for line in section.splitlines():
        if line.startswith(">") or _CHANGELOG_NOISE.match(line):
            continue
        if re.match(r"^### Upgrade Notes\s*$", line):
            skip = True
            continue
        if skip and re.match(r"^### ", line):
            skip = False
        if not skip:
            lines.append(line)
    return "\n".join(lines).strip()


def get_prev_tag(version: str) -> str | None:
    try:
        tags = subprocess.check_output(["git", "tag", "--sort=-version:refname"], text=True).splitlines()
        exclude = {version, f"v{version}"}
        return next((t.strip() for t in tags if t.strip() and t.strip() not in exclude), None)
    except subprocess.CalledProcessError:
        return None


def get_contributors(prev_tag: str | None) -> list[str]:
    try:
        ref = f"{prev_tag}..HEAD" if prev_tag else "HEAD"
        names = subprocess.check_output(["git", "log", ref, "--format=%aN"], text=True).splitlines()
        return sorted({n for n in names if n and "github-actions" not in n.lower()})
    except subprocess.CalledProcessError:
        return []


TEMPLATE = """\
# 📦 py-ballisticcalc v{version}
{intro}
## 🚀 Highlights

{highlights}
{upgrade_section}
{contributors_section}
## 🔗 Full Changelog

{changelog_link}
"""


def generate(version: str, repo: str, changelog_path: Path) -> str:
    text = changelog_path.read_text(encoding="utf-8")
    section = extract_section(text, version)
    if not section:
        sys.exit(f"Error: no changelog section found for version {version!r}")

    intro = parse_intro(section)
    upgrade_notes = parse_subsection(section, "Upgrade Notes")
    highlights = parse_highlights(section)
    prev_tag = get_prev_tag(version)
    contributors = get_contributors(prev_tag)

    if prev_tag:
        url = f"https://github.com/{repo}/compare/{prev_tag}...v{version}"
        changelog_link = f"👉 [Compare {prev_tag}...v{version}]({url})"
    else:
        changelog_link = f"👉 https://github.com/{repo}/releases/tag/v{version}"

    contributor_list = "\n".join(f"* @{c}" for c in contributors)

    notes = TEMPLATE.format(
        version=version,
        intro=intro,
        highlights=highlights,
        upgrade_section=f"## 🛠 Upgrade Notes\n\n{upgrade_notes}\n" if upgrade_notes else "",
        contributors_section=(
            f"## 📜 Contributors\n\nSpecial thanks to everyone who contributed to this release:\n\n{contributor_list}\n"
            if contributors else ""
        ),
        changelog_link=changelog_link,
    )
    return re.sub(r"\n{3,}", "\n\n", notes).strip() + "\n"


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <version> <repo> [changelog]", file=sys.stderr)
        sys.exit(1)

    _version = sys.argv[1].lstrip("v")
    _repo = sys.argv[2]
    _changelog = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("CHANGELOG.md")

    sys.stdout.write(generate(_version, _repo, _changelog))
