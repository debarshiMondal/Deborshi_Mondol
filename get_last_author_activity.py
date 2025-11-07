#!/usr/bin/env python3
import subprocess
import sys
from datetime import datetime
from collections import OrderedDict

# -------------- helpers -------------- #

def run_git(args):
    """Run a git command and return stdout (str) or None on failure."""
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
        print("ERROR: 'git' not found in PATH.", file=sys.stderr)
        sys.exit(1)


def ensure_git_repo():
    inside = run_git(["rev-parse", "--is-inside-work-tree"])
    if inside != "true":
        print("ERROR: Run this script inside a git repository clone.", file=sys.stderr)
        sys.exit(1)


def get_branches_from_git():
    """
    Parse `git branch -a` and return an OrderedDict:
    { display_name: git_ref_to_query }

    Rules:
    - Include local branches (e.g. 'master').
    - Include remotes/origin/* as '<name>' mapped to 'origin/<name>'.
    - Skip HEAD pointers and duplicates.
    - Preserve listing order as seen from git.
    """
    out = run_git(["branch", "-a"])
    if out is None:
        print("ERROR: Unable to list branches.", file=sys.stderr)
        sys.exit(1)

    branches = OrderedDict()

    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue

        # Drop current-branch marker
        if line.startswith("* "):
            line = line[2:].strip()

        # Skip HEAD pointers or symbolic refs
        if "->" in line:
            continue

        # Remote branches
        if line.startswith("remotes/"):
            # Expect: remotes/origin/branch-name
            parts = line.split("/", 2)
            if len(parts) < 3:
                continue
            _, remote, rest = parts
            # Only care about origin/* for this use-case
            if remote == "origin":
                display = rest  # "branch-name"
                ref = f"origin/{rest}"
                # Prefer not to overwrite once set to keep first-seen order
                branches.setdefault(display, ref)
            else:
                # For other remotes: keep as "remote/rest"
                display = f"{remote}/{rest}"
                ref = f"{remote}/{rest}"
                branches.setdefault(display, ref)
        else:
            # Local branch
            display = line
            ref = line
            # If not seen before, add. If already present from origin, keep existing.
            branches.setdefault(display, ref)

    if not branches:
        print("ERROR: No branches found from `git branch -a`.", file=sys.stderr)
        sys.exit(1)

    return branches


def get_last_commit_date(ref, author):
    """
    Return last commit date (%Y-%m-%d) by `author` on given ref.
    If none, return 'NA'.
    """
    out = run_git([
        "log",
        ref,
        f"--author={author}",
        "--date=short",
        "--format=%cd",
        "-n", "1",
    ])
    return out if out else "NA"


def parse_date(date_str):
    """Parse YYYY-MM-DD to date obj; return None if invalid/NA."""
    if not date_str or date_str == "NA":
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


# -------------- main -------------- #

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} \"Author Name\"", file=sys.stderr)
        sys.exit(1)

    author = " ".join(sys.argv[1:]).strip()
    ensure_git_repo()

    # Optional: sync refs silently
    run_git(["fetch", "--all", "--quiet"])

    branches = get_branches_from_git()

    # Collect results
    results = []  # (display_branch, date_str)
    for display, ref in branches.items():
        date_str = get_last_commit_date(ref, author)
        results.append((display, date_str))

    # Find latest non-NA date
    latest_date = None
    for _, d in results:
        pd = parse_date(d)
        if pd and (latest_date is None or pd > latest_date):
            latest_date = pd

    # ANSI highlight setup
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    RESET = "\033[0m"
    STAR = "★"

    # Print report
    # Format: "<branch> <date>" and highlight the max date row(s)
    for br, d in results:
        pd = parse_date(d)
        if latest_date and pd == latest_date:
            # Highlight latest
            # Works even without color thanks to marker text.
            print(f"{BOLD}{GREEN}{STAR} {br} {d} <-- LATEST{RESET}")
        else:
            print(f"  {br} {d}")

if __name__ == "__main__":
    main()
