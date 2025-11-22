#!/usr/bin/env python3.9
"""
envsync_normalize.py
------------------------------------------------------------
Normalize Salesforce metadata folder structures:

1) Branch -> Dump (normalized dump-style)
   python3.9 envsync_normalize.py -b <branch_name> -type branch

2) Dump -> Branch (rebuild branch env-style)
   python3.9 envsync_normalize.py -d <dump.zip> -type dump -o <org_env>

Fixes included (per your feedback):
- Branch->Dump has NO extra src/ folder.
- customSettings -> CustomSettingData is renamed RECURSIVELY anywhere.
- commonLabel CustomLabels merge is namespace-safe and deletes commonLabel.
------------------------------------------------------------
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
# Simple error exit
# ------------------------------------------------------------
def die(msg: str):
    print(f"ERROR: {msg}")
    sys.exit(1)


# ------------------------------------------------------------
# Load rule file (JSON)
# ------------------------------------------------------------
def load_rules(rule_path="conf/folder_normalization.rule"):
    if not os.path.exists(rule_path):
        die(f"Rule file not found: {rule_path}")
    with open(rule_path, "r") as f:
        return json.load(f)


# ------------------------------------------------------------
# Run shell commands
# ------------------------------------------------------------
def run_shell(cmd: str):
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return (p.returncode == 0, p.stdout.strip(), p.stderr.strip())


# ------------------------------------------------------------
# Parse ~/.bashrc to extract live branches and sandbox mapping
# ------------------------------------------------------------
def parse_bashrc_for_live_branches(rules):
    cfg = rules["live_branch_detection"]
    bashrc_path = os.path.expanduser(cfg["bashrc_path"])
    aliases = cfg["aliases_to_read"]
    keywords = cfg["alias_path_keywords"]

    if not os.path.exists(bashrc_path):
        return []

    live = []
    with open(bashrc_path, "r") as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        for alias_name in aliases:
            if line.startswith(f"alias {alias_name}="):

                # Ensure keyword matches deploy area
                keyword = keywords.get(alias_name)
                if keyword and keyword not in line:
                    continue

                # Extract branch name = segment before "/SFDC/"
                parts = line.split("/")
                branch_name = None
                for i, p in enumerate(parts):
                    if p.strip().startswith("SFDC"):
                        if i > 0:
                            branch_name = parts[i - 1]
                        break

                if not branch_name:
                    continue

                # Extract cd path
                m = re.search(r"cd\s+([^;']+)", line)
                branch_path = m.group(1) if m else None
                if not branch_path:
                    continue

                live.append({
                    "name": branch_name,
                    "sandbox": alias_name,   # sbx/tst/hfx
                    "path": branch_path      # absolute path
                })

    return live


# ------------------------------------------------------------
# Resolve branch path + MAIN_ENV
# ------------------------------------------------------------
def resolve_branch_info(branch_name: str, rules):
    master_path = rules["paths"]["master_github_path"]
    env_rules = rules["env_rules"]

    # Master branch
    if branch_name == "Master":
        return {
            "branch_type": "master",
            "branch_path": master_path,
            "main_env": env_rules["master_main_env"],
            "tag": "Master"
        }

    # Live branch (must be found in bashrc)
    live_list = parse_bashrc_for_live_branches(rules)
    for item in live_list:
        if item["name"] == branch_name:
            return {
                "branch_type": "live",
                "branch_path": item["path"],
                "main_env": item["sandbox"],  # sbx/tst/hfx
                "tag": branch_name            # IMPORTANT: tag is branch name ONLY
            }

    die(f"Branch '{branch_name}' not found in ~/.bashrc aliases.")


# ------------------------------------------------------------
# Apply rename map RECURSIVELY (Fix-1)
# ------------------------------------------------------------
def apply_rename_map(base_path: str, rename_map: dict):
    """
    Recursively rename directories anywhere under base_path.
    Example: customSettings -> CustomSettingData
    """
    for old, new in rename_map.items():
        # walk bottom-up so parent renames don't break traversal
        for root, dirs, _ in os.walk(base_path, topdown=False):
            for d in dirs:
                if d == old:
                    old_path = os.path.join(root, d)
                    new_path = os.path.join(root, new)

                    # If target exists, merge content
                    if os.path.exists(new_path):
                        for item in os.listdir(old_path):
                            shutil.move(os.path.join(old_path, item), new_path)
                        shutil.rmtree(old_path)
                    else:
                        shutil.move(old_path, new_path)


# ------------------------------------------------------------
# Merge commonLabel labels -> labels/CustomLabels + delete commonLabel (Fix-2)
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

    # ---- helper to read namespace ----
    def get_ns(tag):
        return tag.split("}")[0].strip("{") if tag.startswith("{") else None

    # ---- load source XML ----
    src_tree = ET.parse(src_file)
    src_root = src_tree.getroot()
    ns = get_ns(src_root.tag)

    # Namespace-safe labels tag
    labels_tag = f"{{{ns}}}labels" if ns else "labels"

    # Extract ONLY <labels> blocks
    src_nodes = src_root.findall(f".//{labels_tag}")
    if not src_nodes:
        return

    # Ensure target XML exists
    if not os.path.exists(tgt_file):
        root_tag = f"{{{ns}}}CustomLabels" if ns else "CustomLabels"
        new_root = ET.Element(root_tag)
        ET.ElementTree(new_root).write(tgt_file, encoding="utf-8", xml_declaration=True)

    tgt_tree = ET.parse(tgt_file)
    tgt_root = tgt_tree.getroot()

    dedupe = rule["xml_merge"].get("dedupe_by_text", True)
    existing_blocks = set()
    if dedupe:
        for node in tgt_root.findall(f".//{labels_tag}"):
            existing_blocks.add(ET.tostring(node, encoding="unicode"))

    for node in src_nodes:
        txt = ET.tostring(node, encoding="unicode")
        if dedupe and txt in existing_blocks:
            continue
        tgt_root.append(node)

    tgt_tree.write(tgt_file, encoding="utf-8", xml_declaration=True)

    # ✅ Delete commonLabel folder after merge
    if rule["xml_merge"].get("delete_source_folder_after_merge", True):
        shutil.rmtree(src_folder, ignore_errors=True)


# ------------------------------------------------------------
# Normalize one extra env folder into tmp/env_<env>_inside_<tag>
# ------------------------------------------------------------
def normalize_one_env(envname: str, source_env_base: str,
                      tmp_root: str, tag: str, branch_type: str,
                      rules):
    naming = rules["naming_conventions"]["temp_env_folder_pattern"]

    if branch_type == "master":
        out_folder_name = naming["master"].format(ENV=envname)
    else:
        out_folder_name = naming["live_branch"].format(ENV=envname, BRANCH_NAME=tag)

    out_folder = os.path.join(tmp_root, out_folder_name)
    os.makedirs(out_folder, exist_ok=True)

    src_env_folder = os.path.join(source_env_base, envname)
    if not os.path.exists(src_env_folder):
        return  # safe skip if missing

    shutil.copytree(src_env_folder, out_folder, dirs_exist_ok=True)

    # Apply renames + label merge inside env folders too
    apply_rename_map(out_folder, rules["rename_maps"]["branch_to_dump"])
    merge_custom_labels(out_folder, rules)


# ------------------------------------------------------------
# BRANCH -> DUMP normalization (matches your mv commands)
# ------------------------------------------------------------
def branch_to_dump(branch_name: str, rules):
    info = resolve_branch_info(branch_name, rules)

    branch_path = info["branch_path"]
    main_env = info["main_env"]
    branch_type = info["branch_type"]
    tag = info["tag"]

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    work_base = os.path.join(os.getcwd(), "norm_runs", ts)
    tmp_root = os.path.join(work_base, "tmp")
    norm_dump_root = os.path.join(work_base, "normalized_dump")

    os.makedirs(tmp_root, exist_ok=True)
    os.makedirs(norm_dump_root, exist_ok=True)

    # Root of normalized dump
    work_branch_root = os.path.join(tmp_root, tag)
    os.makedirs(work_branch_root, exist_ok=True)

    # ✅ Copy src directly into tmp/<TAG>/
    src_from = os.path.join(branch_path, "src")
    if not os.path.exists(src_from):
        die(f"src folder not found: {src_from}")

    shutil.copytree(src_from, work_branch_root, dirs_exist_ok=True)

    # env is now tmp/<TAG>/env
    env_root = os.path.join(work_branch_root, "env")
    main_env_folder = os.path.join(env_root, main_env)

    if not os.path.exists(main_env_folder):
        die(f"Main env folder missing: {main_env_folder}")

    # ✅ Move env/<MAIN_ENV>/* to tmp/<TAG>/
    for item in os.listdir(main_env_folder):
        shutil.move(os.path.join(main_env_folder, item), work_branch_root)

    # ✅ Remove env entirely
    shutil.rmtree(env_root, ignore_errors=True)

    # ✅ Recursive renames
    apply_rename_map(work_branch_root, rules["rename_maps"]["branch_to_dump"])

    # ✅ Merge + delete commonLabel
    merge_custom_labels(work_branch_root, rules)

    # Additional env normalization
    if branch_type == "master":
        additional_envs = rules["env_rules"]["master_additional_envs"]
        source_env_base = os.path.join(rules["paths"]["master_github_path"], "src", "env")
    else:
        additional_envs = rules["env_rules"]["live_additional_envs"]
        source_env_base = os.path.join(branch_path, "src", "env")

    for envname in additional_envs:
        if envname == main_env:
            continue
        normalize_one_env(envname, source_env_base, tmp_root, tag, branch_type, rules)

    # Final output copy
    out_path = os.path.join(norm_dump_root, tag)
    shutil.copytree(work_branch_root, out_path, dirs_exist_ok=True)

    print("\n✅ Branch → Dump normalization completed.")
    print(f"Working folder: {work_base}")
    print(f"Normalized dump output: {out_path}\n")


# ------------------------------------------------------------
# DUMP -> BRANCH normalization (inverse)
# ------------------------------------------------------------
def dump_to_branch(dump_name: str, org_env_name: str, rules):
    if org_env_name not in ["prod", "sbx", "tst", "hfx"]:
        die("Invalid -o org env name. Use one of: prod, sbx, tst, hfx")

    main_env = org_env_name
    dump_zip_path = os.path.join(rules["paths"]["prod_dump_base"], dump_name)
    if not os.path.exists(dump_zip_path):
        die(f"Dump not found: {dump_zip_path}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    work_base = os.path.join(os.getcwd(), "norm_runs", ts)
    tmp_root = os.path.join(work_base, "tmp")
    norm_branch_root = os.path.join(work_base, "normalized_branch")

    os.makedirs(tmp_root, exist_ok=True)
    os.makedirs(norm_branch_root, exist_ok=True)

    dump_tag = f"Dump_{Path(dump_name).stem}"

    work_dump_root = os.path.join(tmp_root, dump_tag)
    os.makedirs(work_dump_root, exist_ok=True)

    ok, _, err = run_shell(f'unzip "{dump_zip_path}" -d "{work_dump_root}"')
    if not ok:
        die(f"Unzip failed: {err}")

    # If unzip created a single top folder, shift root
    inner_items = os.listdir(work_dump_root)
    if len(inner_items) == 1:
        inner_path = os.path.join(work_dump_root, inner_items[0])
        if os.path.isdir(inner_path):
            work_dump_root = inner_path

    # Reverse renames (labels -> customLabel etc.)
    apply_rename_map(work_dump_root, rules["rename_maps"]["dump_to_branch"])

    # Create src/env/<main_env>/
    src_root = os.path.join(work_dump_root, "src")
    env_root = os.path.join(src_root, "env")
    main_env_folder = os.path.join(env_root, main_env)
    os.makedirs(main_env_folder, exist_ok=True)

    # Move all metadata root folders into env/<main_env>/
    for item in os.listdir(work_dump_root):
        if item == "src" or item.startswith("env_"):
            continue
        shutil.move(os.path.join(work_dump_root, item), main_env_folder)

    out_path = os.path.join(norm_branch_root, dump_tag)
    shutil.copytree(work_dump_root, out_path, dirs_exist_ok=True)

    print("\n✅ Dump → Branch normalization completed.")
    print(f"Working folder: {work_base}")
    print(f"Normalized branch output: {out_path}\n")


# ------------------------------------------------------------
# CLI parsing
# ------------------------------------------------------------
def parse_args():
    p = argparse.ArgumentParser()

    p.add_argument("-type", choices=["branch", "dump"], required=True)
    p.add_argument("-b", dest="branch_name")
    p.add_argument("-d", dest="dump_name")
    p.add_argument("-o", dest="org_env_name")

    args = p.parse_args()

    if args.type == "branch":
        if not args.branch_name:
            die("-b <branch_name> required for -type branch")
        if args.dump_name or args.org_env_name:
            die("-d / -o not allowed for -type branch")

    if args.type == "dump":
        if not args.dump_name or not args.org_env_name:
            die("-d <dump.zip> and -o <org_env> required for -type dump")
        if args.branch_name:
            die("-b not allowed for -type dump")

    return args


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def main():
    rules = load_rules()
    args = parse_args()

    if args.type == "branch":
        branch_to_dump(args.branch_name, rules)
    else:
        dump_to_branch(args.dump_name, args.org_env_name, rules)


if __name__ == "__main__":
    main()
