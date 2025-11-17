#!/usr/bin/env python3
"""
find_hardcoded_values.py

Usage:
    python3 find_hardcoded_values.py <ENV> <MODE>

Where:
  <ENV>  = Environment name (e.g., DEV, QA, UAT, PROD)
  <MODE> = 1 | 2 | 3
           1 -> Scan src/classes only
           2 -> Scan changeSetDeploy/src/classes only
           3 -> Scan both and generate both CSVs

Output:
  - Mode 1: hardcoded_src_classes_<ENV>.csv
  - Mode 2: hardcoded_changeset_classes_<ENV>.csv
  - Mode 3: both of the above

The script then sends an email with the generated CSV(s) attached using mutt.
The email_to value is read from: build/property/<ENV>.conf
"""

import os
import re
import csv
import sys
import subprocess
from typing import List, Tuple, Optional

# --------------------- CONSTANT PATHS ---------------------

SRC_CLASSES_DIR = "src/classes"
CHANGESET_CLASSES_DIR = "changeSetDeploy/src/classes"
CONF_DIR = "build/property"   # contains <ENV>.conf

# Regex for Apex/Java-style string literals (handles escaped quotes)
STRING_LITERAL_RE = re.compile(
    r'"([^"\\]*(?:\\.[^"\\]*)*)"|\'([^\'\\]*(?:\\.[^\'\\]*)*)\''
)


# --------------------- CONFIG LOADER ----------------------


def load_email_to(env: str) -> str:
    """
    Load email_to from build/property/<ENV>.conf

    Expected line format (case-sensitive key):
        email_to=addr1@domain.com,addr2@domain.com
    """
    conf_path = os.path.join(CONF_DIR, f"{env}.conf")
    if not os.path.isfile(conf_path):
        print(f"Error: config file not found: {conf_path}", file=sys.stderr)
        sys.exit(1)

    email_to = None
    try:
        with open(conf_path, "r", encoding="utf-8", errors="ignore") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("email_to"):
                    # Support formats like: email_to=..., email_to = ...
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        email_to = parts[1].strip()
                        break
    except (OSError, UnicodeDecodeError) as e:
        print(f"Error: failed to read {conf_path}: {e}", file=sys.stderr)
        print(e, file=sys.stderr)
        sys.exit(1)

    if not email_to:
        print(f"Error: 'email_to' not found or empty in {conf_path}", file=sys.stderr)
        sys.exit(1)

    return email_to


# --------------------- CORE SCAN LOGIC --------------------


def find_hardcoded_strings_in_file(filepath: str) -> List[Tuple[str, int, str]]:
    """
    Scan a single .cls file and return list of (FileName, LineNumber, Literal).
    """
    results: List[Tuple[str, int, str]] = []
    filename = os.path.basename(filepath)

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for lineno, line in enumerate(f, start=1):
                # Remove single-line comments to reduce noise
                code_part = line.split("//", 1)[0]
                for match in STRING_LITERAL_RE.finditer(code_part):
                    literal = match.group(0)  # full match including quotes
                    if literal in ('""', "''"):
                        continue  # skip empty strings
                    results.append((filename, lineno, literal))
    except (OSError, UnicodeDecodeError) as e:
        print(f"Warning: Could not read {filepath}: {e}", file=sys.stderr)

    return results


def scan_dir_for_cls(dir_path: str) -> List[Tuple[str, int, str]]:
    """
    Walk a directory and scan all .cls files.
    """
    all_results: List[Tuple[str, int, str]] = []

    if not os.path.isdir(dir_path):
        print(f"Warning: directory not found: {dir_path}", file=sys.stderr)
        return all_results

    for root, _, files in os.walk(dir_path):
        for name in files:
            if name.lower().endswith(".cls"):
                path = os.path.join(root, name)
                all_results.extend(find_hardcoded_strings_in_file(path))

    return all_results


def write_csv(csv_path: str, rows: List[Tuple[str, int, str]]) -> None:
    """
    Write results to CSV with required columns.
    """
    directory = os.path.dirname(csv_path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["File Name", "Line Number", "Hard Coaded Value"])
        writer.writerows(rows)


# ----------------------- EMAIL PART -----------------------


def send_email_with_mutt(env: str,
                         email_to: str,
                         csv1: Optional[str],
                         csv2: Optional[str]) -> None:
    """
    Send email using mutt with 1 or 2 CSV attachments.
    email_to comes from build/property/<ENV>.conf
    """
    subject = f"Hard-coded values in the Apex class are being deployed to {env}"

    # Build mail body text
    body_lines = [
        "Hi Team,",
        "Please find the reports attached for the deployed Apex class review.",
    ]

    csv1_label = os.path.basename(csv1) if csv1 else "N/A"
    csv2_label = os.path.basename(csv2) if csv2 else "N/A"

    # Follow your requested sentence as closely as possible
    body_lines.append(
        f"{csv1_label} covers the entire Apex class codebase, "
        f"and {csv2_label} covers only the validated Apex classes."
    )

    body = "\n".join(body_lines) + "\n"

    # Build mutt command
    cmd = ["mutt", "-s", subject]

    if csv1:
        cmd.extend(["-a", csv1])
    if csv2:
        cmd.extend(["-a", csv2])

    cmd.append("--")
    cmd.append(email_to)

    print(f"Sending email to {email_to} with mutt...")
    try:
        subprocess.run(cmd, input=body, text=True, check=True)
        print("Email sent successfully.")
    except FileNotFoundError:
        print("Error: mutt command not found. Please install mutt or adjust the script.", file=sys.stderr)
    except subprocess.CalledProcessError as e:
        print(f"Error: mutt failed with exit code {e.returncode}", file=sys.stderr)


# ----------------------- CLI / MAIN -----------------------


def print_usage_and_exit() -> None:
    usage = (
        "Usage:\n"
        "  python3 find_hardcoded_values.py <ENV> <MODE>\n\n"
        "Where:\n"
        "  <ENV>  = Environment name (e.g., DEV, QA, UAT, PROD)\n"
        "  <MODE> = 1 | 2 | 3\n"
        "           1 -> Scan src/classes only\n"
        "           2 -> Scan changeSetDeploy/src/classes only\n"
        "           3 -> Scan both and generate both CSVs\n\n"
        "Example:\n"
        "  python3 find_hardcoded_values.py UAT 1\n"
        "  python3 find_hardcoded_values.py UAT 2\n"
        "  python3 find_hardcoded_values.py UAT 3\n"
    )
    print(usage, file=sys.stderr)
    sys.exit(1)


def main():
    if len(sys.argv) != 3:
        print_usage_and_exit()

    env = sys.argv[1].strip()
    mode_str = sys.argv[2].strip()

    if not env:
        print("Error: ENV name cannot be empty.\n", file=sys.stderr)
        print_usage_and_exit()

    if mode_str not in {"1", "2", "3"}:
        print(f"Error: Invalid MODE '{mode_str}'. Must be 1, 2, or 3.\n", file=sys.stderr)
        print_usage_and_exit()

    mode = int(mode_str)

    # Load email_to from build/property/<ENV>.conf
    email_to = load_email_to(env)
    print(f"Using email_to from config: {email_to}")

    # Build output file names
    csv_src = os.path.abspath(f"hardcoded_src_classes_{env}.csv")
    csv_changeset = os.path.abspath(f"hardcoded_changeset_classes_{env}.csv")

    generated_src = False
    generated_changeset = False

    # Mode 1 & 3: scan src/classes
    if mode in (1, 3):
        print(f"Scanning {SRC_CLASSES_DIR} for hard-coded string literals...")
        results_src = scan_dir_for_cls(SRC_CLASSES_DIR)
        write_csv(csv_src, results_src)
        print(f"  -> Found {len(results_src)} entries in {csv_src}")
        generated_src = True

    # Mode 2 & 3: scan changeSetDeploy/src/classes
    if mode in (2, 3):
        print(f"Scanning {CHANGESET_CLASSES_DIR} for hard-coded string literals...")
        results_changeset = scan_dir_for_cls(CHANGESET_CLASSES_DIR)
        write_csv(csv_changeset, results_changeset)
        print(f"  -> Found {len(results_changeset)} entries in {csv_changeset}")
        generated_changeset = True

    # Decide which CSVs to attach
    attach_csv1 = csv_src if generated_src else None
    attach_csv2 = csv_changeset if generated_changeset else None

    # Send email
    send_email_with_mutt(env, email_to, attach_csv1, attach_csv2)


if __name__ == "__main__":
    main()
