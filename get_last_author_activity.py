#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

BRANCH_FILE = "branch.txt"

def run_git_command(args):
    """Run a git command and return stdout as text, or None on error."""
    try:
        result = subprocess.run(
            ["git"] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip()
    except FileNotFoundError:
        print("ERROR: 'git' command not found. Make sure Git is installed and in PATH.", file=sys.stderr)
        sys.exit(1)

def get_last_commit_date(branch: str, author: str) -> str:
    """
    Returns the last commit date (%Y-%m-%d) by `author` on `branch`.
    Tries both local branch and origin/<branch>.
    If no commit found, returns 'NA'.
    """
    # Try direct branch
    log_output = run_git_command([
        "log",
        branch,
        f"--author={author}",
        "--date=short",
        "--format=%cd",
        "-n", "1",
    ])

    # If branch not found or no commit, try origin/<branch>
    if not log_output:
        log_output = run_git_command([
            "log",
            f"origin/{branch}",
            f"--author={author}",
            "--date=short",
            "--format=%cd",
            "-n", "1",
        ])

    return log_output if log_output else "NA"

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} \"Author Name\"", file=sys.stderr)
        sys.exit(1)

    author = " ".join(sys.argv[1:]).strip()

    branch_file_path = Path(BRANCH_FILE)
    if not branch_file_path.is_file():
        print(f"ERROR: '{BRANCH_FILE}' not found in current directory.", file=sys.stderr)
        sys.exit(1)

    # Optional: ensure we’re in a git repo
    is_repo = run_git_command(["rev-parse", "--is-inside-work-tree"])
    if is_repo != "true":
        print("ERROR: This script must be run inside a git repository (SFDC clone).", file=sys.stderr)
        sys.exit(1)

    # (Optional but useful) fetch latest refs silently
    run_git_command(["fetch", "--all", "--quiet"])

    with branch_file_path.open("r", encoding="utf-8") as f:
        branches = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]

    if not branches:
        print(f"ERROR: No branch names found in '{BRANCH_FILE}'.", file=sys.stderr)
        sys.exit(1)

    # Output: one line per branch: "<branch> <date>"
    # If no commit by that author: date = NA
    for br in branches:
        last_date = get_last_commit_date(br, author)
        print(f"{br} {last_date}")

if __name__ == "__main__":
    main()
