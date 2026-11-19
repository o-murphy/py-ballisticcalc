"""Whether anything a workflow tests has changed since its last successful run by schedule.

    python .github/scripts/changed_since_last_run.py tests-ctypes.yml

The night run of tests-ctypes.yml (QEMU: an hour or more per architecture) is not worth it when nothing it tests has changed. "What it
tests" is the `paths` of its pull_request trigger, so the list is the workflow's own and is written once. The last successful scheduled
run is found with `gh` (GH_TOKEN, GH_REPO, and `actions: read`); the files are compared with git (the history must be checked out).

Prints `skip=true` or `skip=false` (also to $GITHUB_OUTPUT). It runs the tests, `skip=false`, whenever it cannot tell: no run yet,
the commit of that run is not in the history, `gh` or `git` fail.
"""

import os
import subprocess
import sys
from pathlib import Path

import yaml

WORKFLOWS = Path(__file__).resolve().parent.parent / "workflows"


def pathspecs(workflow: str) -> list[str]:
    """The `paths` of the pull_request trigger as git pathspecs (a glob needs the `glob` magic to cross directories)."""
    document = yaml.safe_load((WORKFLOWS / workflow).read_text(encoding="utf-8"))
    triggers = document.get("on", document.get(True))  # YAML 1.1 reads the key `on` as true
    return [f":(glob){path}" if "*" in path else path for path in triggers["pull_request"]["paths"]]


def last_success(workflow: str) -> str | None:
    """The commit of the last successful run of the workflow that was started by the schedule."""
    command = [
        "gh",
        "run",
        "list",
        "--workflow",
        workflow,
        "--event",
        "schedule",
        "--status",
        "success",
        "--limit",
        "1",
    ]
    output = subprocess.run(
        [*command, "--json", "headSha", "--jq", ".[0].headSha // empty"], capture_output=True, text=True, check=True
    )
    return output.stdout.strip() or None


def decide(workflow: str) -> tuple[bool, str]:
    """(skip, why)."""
    last = last_success(workflow)
    if last is None:
        return False, "no successful scheduled run yet"
    if subprocess.run(["git", "cat-file", "-e", f"{last}^{{commit}}"], capture_output=True).returncode != 0:
        return False, f"the commit of the last run, {last[:7]}, is not in the history"
    diff = subprocess.run(["git", "diff", "--quiet", last, "HEAD", "--", *pathspecs(workflow)], capture_output=True)
    if diff.returncode == 0:
        return True, f"nothing it tests has changed since the last successful scheduled run ({last[:7]})"
    if diff.returncode == 1:
        return False, f"something it tests has changed since the last successful scheduled run ({last[:7]})"
    return False, f"git diff failed: {diff.stderr.decode().strip()}"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: changed_since_last_run.py <workflow file name>", file=sys.stderr)
        return 2
    try:
        skip, why = decide(argv[1])
    except (subprocess.CalledProcessError, OSError, KeyError) as error:
        skip, why = False, f"could not tell ({error!r})"
        print(f"::warning::{argv[1]}: {why}", flush=True)
    print(f"::notice::{argv[1]}: {'skipped' if skip else 'runs'}: {why}", flush=True)
    line = f"skip={str(skip).lower()}"
    print(line)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            output.write(line + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
