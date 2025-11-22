#!/usr/bin/env python3.9
"""
envsync_normalize.py
------------------------------------------------------------
Single purpose: Normalize folder structures in two directions:

1) Branch -> Dump format
   python3.9 envsync_normalize.py -b <branch> -type branch

2) Dump -> Branch format
   python3.9 envsync_normalize.py -d <dump.zip> -type dump -o <org_env>

Important:
- Rules are loaded from conf/folder_normalization.rule (JSON).
- This script creates its own working folder inside ./norm_runs/<timestamp>/.
- Output folders:
    ./norm_runs/<ts>/normalized_dump/<BranchTag>/
    ./norm_runs/<ts>/normalized_branch/<DumpTag>/
------------------------------------------------------------
This file is heavily commented for beginners.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET


# ------------------------------------------------------------
# Small helper to print and exit with error
# ------------------------------------------------------------
def die(msg: str):
    print(f"ERROR: {msg}")
    sys.exit(1)


# ------------------------------------------------------------
# Read rule file (JSON)
# ------------------------------------------------------------
def load_rules(rule_path="conf/folder_normalization.rule"):
    if not os.path.exists(rule_path):
        die(f"Rule file not found: {rule_path}")

    with open(rule_path, "r") as f:
        return json.load(f)


# ------------------------------------------------------------
# Run shell commands safely (beginner friendly)
# ------------------------------------------------------------
def run_shell(cmd: str):
    """
    Runs a Linux shell command.
    Returns (success_boolean, stdout_text, stderr_text)
    """
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return (p.returncode == 0, p.stdout.strip(), p.stderr.strip())


# ------------------------------------------------------------
# Find all files recursively under a folder
# ------------------------------------------------------------
def list_all_files(root_dir: str):
    files = []
    for base, _, fnames in os.walk(root_dir):
        for f in fnames:
            full = os.path.join(base, f)
            rel = os.path.relpath(full, root_dir)
            files.append(rel)
    return files


# ------------------------------------------------------------
# Parse ~/.bashrc to extract live branches and their sandbox env
# ------------------------------------------------------------
def parse_bashrc_for_live_branches(rules):
    bashrc_path = os.path.expanduser(rules["live_branch_detection"]["bashrc_path"])
    aliases = rules["live_branch_detection"]["aliases_to_read"]
    keywords = rules["live_branch_detection"]["alias_path_keywords"]

    if not os.path.exists(bashrc_path):
        return []  # no live branches possible

    live = []  # list of dict: {name, sandbox, path}

    with open(bashrc_path, "r") as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        # Check each alias one by one
        for alias_name in aliases:
            if line.startswith(f"alias {alias_name}="):
                # Example alias line:
                # alias sbx='cd /data/.../sfdc_deploySBX/2025-q4nov-release/SFDC/;pwd'
                # We only accept if keyword matches expected deploy folder
                keyword = keywords.get(alias_name)
                if keyword and keyword not in line:
                    continue

                # Extract branch name = folder just before "/SFDC/"
                # Split by "/" and find "SFDC"
                parts = line.split("/")
                branch_name = None
                for i, p in enumerate(parts):
                    if p.strip().startswith("SFDC"):
                        if i > 0:
                            branch_name = parts[i - 1]
                        break

                if branch_name:
                    # Extract actual cd path (between cd and ;pwd)
                    m = re.search(r"cd\s+([^;']+)", line)
                    branch_path = m.group(1) if m else None

                    live.append({
                        "name": branch_name,
                        "sandbox": alias_name,
                        "path": branch_path
                    })

    return live


# ------------------------------------------------------------
# Resolve branch path and MAIN_ENV for branch mode
# ------------------------------------------------------------
def resolve_branch_info(branch_name: str, rules):
    master_path = rules["paths"]["master_github_path"]

    # Case 1: Master branch
    if branch_name == "Master":
        return {
            "branch_type": "master",
            "branch_path": master_path,
            "main_env": rules["env_rules"]["master_main_env"],
            "branch_tag": "Master"
        }

    # Case 2: Live branch (must exist in bashrc)
    live_list = parse_bashrc_for_live_branches(rules)
    for item in live_list:
        if item["name"] == branch_name:
            return {
                "branch_type": "live",
                "branch_path": item["path"],   # path resolved from bashrc alias
                "main_env": item["sandbox"],   # sbx/tst/hfx
                "branch_tag": f"Branch_{branch_name}"
            }

    die(f"Branch '{branch_name}' not found in ~/.bashrc live aliases.")


# ------------------------------------------------------------
# Apply rename map to folders in-place
# ------------------------------------------------------------
def apply_rename_map(base_path: str, rename_map: dict):
    """
    Rename any folder if it exists.
    Example:
      customLabel -> labels
    """
    for old, new in rename_map.items():
        old_path = os.path.join(base_path, old)
        new_path = os.path.join(base_path, new)
        if os.path.exists(old_path):
            # If target already exists, merge content
            if os.path.exists(new_path):
                for item in os.listdir(old_path):
                    shutil.move(os.path.join(old_path, item), new_path)
                shutil.rmtree(old_path)
            else:
                shutil.move(old_path, new_path)


# ------------------------------------------------------------
# Merge commonLabel/CustomLabels.labels-meta.xml into labels version
# ------------------------------------------------------------
def merge_custom_labels(base_path: str, rules):
    rule = rules["custom_label_merge"]
    if not rule.get("enabled"):
        return

    src_folder = os.path.join(base_path, rule["source_folder"])
    src_file = os.path.join(src_folder, rule["source_file"])

    tgt_folder = os.path.join(base_path, rule["target_folder"])
    tgt_file = os.path.join(tgt_folder, rule["target_file"])

    if not os.path.exists(src_file):
        return  # nothing to merge

    os.makedirs(tgt_folder, exist_ok=True)

    # Load source XML
    src_tree = ET.parse(src_file)
    src_root = src_tree.getroot()

    extract_name = rule["xml_merge"]["extract_node_name"]

    # Find all <labels> nodes in source
    src_labels_nodes = src_root.findall(f".//{extract_name}")

    if not src_labels_nodes:
        return

    # If target does not exist, create skeleton
    if not os.path.exists(tgt_file):
        # Create <CustomLabels> root (no namespace assumptions)
        new_root = ET.Element(rule["xml_merge"]["insert_under_root"])
        new_tree = ET.ElementTree(new_root)
        new_tree.write(tgt_file, encoding="utf-8", xml_declaration=True)

    # Now load target XML
    tgt_tree = ET.parse(tgt_file)
    tgt_root = tgt_tree.getroot()

    # Deduplicate if enabled
    dedupe = rule["xml_merge"].get("dedupe_by_text", True)
    existing_blocks = set()
    if dedupe:
        for node in tgt_root.findall(f".//{extract_name}"):
            existing_blocks.add(ET.tostring(node, encoding="unicode"))

    # Insert each labels block into target root
    for node in src_labels_nodes:
        node_text = ET.tostring(node, encoding="unicode")
        if dedupe and node_text in existing_blocks:
            continue
        tgt_root.append(node)

    # Write back to file
    tgt_tree.write(tgt_file, encoding="utf-8", xml_declaration=True)

    # After merge, commonLabel folder can remain (or be removed by caller)


# ------------------------------------------------------------
# Copy + normalize an env folder into tmp/env_X_inside_TAG
# ------------------------------------------------------------
def normalize_one_env(envname: str, source_env_base: str, tmp_root: str,
                      branch_tag: str, rules):
    out_folder = os.path.join(tmp_root, f"env_{envname}_inside_{branch_tag}")
    os.makedirs(out_folder, exist_ok=True)

    src_env_folder = os.path.join(source_env_base, envname)
    if not os.path.exists(src_env_folder):
        # If folder is missing, skip silently (some env folders may not exist)
        return

    # Copy the whole env folder content
    shutil.copytree(src_env_folder, out_folder, dirs_exist_ok=True)

    # Apply branch->dump renames inside this env folder
    apply_rename_map(out_folder, rules["rename_maps"]["branch_to_dump"])

    # Merge commonLabel into labels inside this env folder
    merge_custom_labels(out_folder, rules)


# ------------------------------------------------------------
# BRANCH -> DUMP Normalization
# ------------------------------------------------------------
def branch_to_dump(branch_name: str, rules):
    # 1. Resolve branch info (path, main env name, type)
    info = resolve_branch_info(branch_name, rules)

    branch_path = info["branch_path"]
    main_env = info["main_env"]
    branch_type = info["branch_type"]
    branch_tag = info["branch_tag"]

    # 2. Create timestamp working folder
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    work_base = os.path.join(os.getcwd(), "norm_runs", ts)
    tmp_root = os.path.join(work_base, "tmp")
    norm_dump_root = os.path.join(work_base, "normalized_dump")
    os.makedirs(tmp_root, exist_ok=True)
    os.makedirs(norm_dump_root, exist_ok=True)

    # 3. Copy src/ of branch into tmp/<branch_tag>/src
    work_branch_root = os.path.join(tmp_root, branch_tag)
    src_root = os.path.join(work_branch_root, "src")
    os.makedirs(src_root, exist_ok=True)

    src_from = os.path.join(branch_path, "src")
    if not os.path.exists(src_from):
        die(f"src folder not found in branch path: {src_from}")

    shutil.copytree(src_from, src_root, dirs_exist_ok=True)

    # 4. Move env/<main_env> content to root of work_branch_root
    env_root = os.path.join(src_root, "env")
    main_env_folder = os.path.join(env_root, main_env)

    if not os.path.exists(main_env_folder):
        die(f"Main env folder missing: {main_env_folder}")

    # Move everything inside env/<main_env> to work_branch_root
    for item in os.listdir(main_env_folder):
        shutil.move(os.path.join(main_env_folder, item), work_branch_root)

    # Remove env folder completely (as per rule)
    shutil.rmtree(env_root, ignore_errors=True)

    # 5. Apply rename rules (branch -> dump)
    apply_rename_map(work_branch_root, rules["rename_maps"]["branch_to_dump"])

    # 6. Merge commonLabel labels into labels/CustomLabels.labels-meta.xml
    merge_custom_labels(work_branch_root, rules)

    # 7. Normalize additional env folders into tmp/env_*_inside_*
    if branch_type == "master":
        additional_envs = rules["env_rules"]["master_additional_envs"]
        source_env_base = os.path.join(rules["paths"]["master_github_path"], "src", "env")
    else:
        additional_envs = rules["env_rules"]["live_additional_envs"]
        source_env_base = os.path.join(branch_path, "src", "env")

    # We skip the main env itself
    for envname in additional_envs:
        if envname == main_env:
            continue
        normalize_one_env(envname, source_env_base, tmp_root, branch_tag, rules)

    # 8. Final output: copy normalized result to normalized_dump/<branch_tag>/
    out_path = os.path.join(norm_dump_root, branch_tag)
    shutil.copytree(work_branch_root, out_path, dirs_exist_ok=True)

    print("\n✅ Branch → Dump normalization completed.")
    print(f"Working folder: {work_base}")
    print(f"Normalized dump output: {out_path}\n")


# ------------------------------------------------------------
# DUMP -> BRANCH Normalization
# ------------------------------------------------------------
def dump_to_branch(dump_name: str, org_env_name: str, rules):
    # 1. Validate org env name
    if org_env_name not in ["prod", "sbx", "tst", "hfx"]:
        die("Invalid -o org env name. Use one of: prod, sbx, tst, hfx")

    main_env = org_env_name
    dump_zip_path = os.path.join(rules["paths"]["prod_dump_base"], dump_name)

    if not os.path.exists(dump_zip_path):
        die(f"Dump file not found: {dump_zip_path}")

    # 2. Create timestamp working folder
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    work_base = os.path.join(os.getcwd(), "norm_runs", ts)
    tmp_root = os.path.join(work_base, "tmp")
    norm_branch_root = os.path.join(work_base, "normalized_branch")
    os.makedirs(tmp_root, exist_ok=True)
    os.makedirs(norm_branch_root, exist_ok=True)

    dump_tag = f"Dump_{Path(dump_name).stem}"

    # 3. Unzip dump into tmp/<dump_tag>/
    work_dump_root = os.path.join(tmp_root, dump_tag)
    os.makedirs(work_dump_root, exist_ok=True)

    ok, out, err = run_shell(f'unzip "{dump_zip_path}" -d "{work_dump_root}"')
    if not ok:
        die(f"Unzip failed: {err}")

    # 4. Sometimes unzip creates one top folder inside.
    #    If there is exactly one folder, treat it as actual dump root.
    inner_items = os.listdir(work_dump_root)
    if len(inner_items) == 1:
        inner_path = os.path.join(work_dump_root, inner_items[0])
        if os.path.isdir(inner_path):
            work_dump_root = inner_path  # shift root

    # 5. Reverse rename rules (dump -> branch)
    apply_rename_map(work_dump_root, rules["rename_maps"]["dump_to_branch"])

    # 6. Recreate src/env/<main_env>/
    src_root = os.path.join(work_dump_root, "src")
    env_root = os.path.join(src_root, "env")
    main_env_folder = os.path.join(env_root, main_env)
    os.makedirs(main_env_folder, exist_ok=True)

    # 7. Move all metadata folders into env/<main_env>/
    #    We move everything except "src" and any env_* temp folders.
    for item in os.listdir(work_dump_root):
        if item == "src" or item.startswith("env_"):
            continue
        shutil.move(os.path.join(work_dump_root, item), main_env_folder)

    # 8. Restore additional env folders if tmp/env_* exist
    #    (They may not exist for production dumps; safe to skip)
    additional_envs = rules["env_rules"]["live_additional_envs"]
    for envname in additional_envs:
        if envname == main_env:
            continue
        tmp_env_folder = os.path.join(tmp_root, f"env_{envname}_inside_{dump_tag}")
        if os.path.exists(tmp_env_folder):
            dest_env_folder = os.path.join(env_root, envname)
            shutil.copytree(tmp_env_folder, dest_env_folder, dirs_exist_ok=True)

    # 9. Final output: copy reconstructed branch to normalized_branch/<dump_tag>/
    out_path = os.path.join(norm_branch_root, dump_tag)
    shutil.copytree(work_dump_root, out_path, dirs_exist_ok=True)

    print("\n✅ Dump → Branch normalization completed.")
    print(f"Working folder: {work_base}")
    print(f"Normalized branch output: {out_path}\n")


# ------------------------------------------------------------
# Parse CLI arguments
# ------------------------------------------------------------
def parse_args():
    p = argparse.ArgumentParser()

    p.add_argument("-type", choices=["branch", "dump"], required=True)
    p.add_argument("-b", dest="branch_name")
    p.add_argument("-d", dest="dump_name")
    p.add_argument("-o", dest="org_env_name")

    args = p.parse_args()

    # --- strict validation as per your contract ---
    if args.type == "branch":
        if not args.branch_name:
            die("-b <branch_name> required for -type branch")
        if args.dump_name or args.org_env_name:
            die("-d or -o are not allowed for -type branch")

    if args.type == "dump":
        if not args.dump_name or not args.org_env_name:
            die("-d <dump.zip> and -o <org env name> required for -type dump")
        if args.branch_name:
            die("-b is not allowed for -type dump")

    return args


# ------------------------------------------------------------
# MAIN ENTRY POINT
# ------------------------------------------------------------
def main():
    rules = load_rules()
    args = parse_args()

    if args.type == "branch":
        branch_to_dump(args.branch_name, rules)

    elif args.type == "dump":
        dump_to_branch(args.dump_name, args.org_env_name, rules)


if __name__ == "__main__":
    main()
