"""
YAML config validator — shell wrapper for yq via subprocess.
Runs basic + extensible checks and indentation validation.
Add this file to .gitignore if using locally.
"""

import subprocess
from pathlib import Path
import sys


DIRECTORY = r"C:\\Progs\\yml2dot"
YQ_DIR = r"C:\\Progs\\yq\\yq-4.48.2\\yq.exe"
YML2_DOT_DIR = r"C:\\Progs\\yml2dot\\yml2dot.exe"

INDENT_SIZE = 2
EXTENDED_CHECKS = [
    ".name",
    ".jobs",
    ".on",
    ".jobs.*.steps",
    ".jobs.*.runs-on"
]

DEPRECATED_ACTIONS = ["setup-python@v1", "checkout@v1"]


def find_yaml_files(directory):
    """Return list of *.yml / *.yaml files. Supports both file and directory."""
    path = Path(directory)

    if path.is_file():
        return [path] if path.suffix.lower() in (".yml", ".yaml") else []

    if not path.is_dir():
        print(f"❌ '{directory}' is neither a file nor directory")
        sys.exit(1)

    return list(path.rglob("*.yml")) + list(path.rglob("*.yaml"))


def check_for_empty_file(file_path):
    try:
        if file_path.stat().st_size == 0:
            print(f"❌ {file_path} — empty file")
            return 1
    except OSError as e:
        print(f"❌ {file_path} — could not stat file: {e}")
        return 1

    return 0


def check_for_deprecated_keys(file_path, content):
    issues = 0
    if not content:
        return 0

    for deprecated in DEPRECATED_ACTIONS:
        if deprecated in content:
            print(f"⚠ {file_path}: uses deprecated action '{deprecated}'")
            issues += 1

    return issues


def run_yq(file_path, expression, description):
    """Run yq. If base check — still capture stderr to detect broken YAML."""
    try:
        result = subprocess.run(
            [YQ_DIR, "eval", expression, str(file_path)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        output = result.stdout.strip()
        # For extended checks — missing field = empty or "null"
        if expression != ".":
            if output in ("", "null"):
                print(f"❌ {file_path} — {description} missing!")
                return 1

        print(f"✅ {file_path} — {description} OK")
        return 0

    except subprocess.CalledProcessError as e:
        print(f"❌ {file_path} — {description} error:")
        print(e.stderr.strip())
        return 1


def check_indentation(file_path):
    """Check for mixed tabs/spaces, trailing spaces, bad indentation."""
    errors = 0

    with open(file_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            raw_line = line.rstrip("\r\n")

            if not raw_line.strip():
                continue  # skip empty lines

            stripped = raw_line.lstrip("\t ")
            indent = raw_line[: len(raw_line) - len(stripped)]

            # Mixed indent
            if "\t" in indent and " " in indent:
                print(f"❌ {file_path}: line {i} — mixed tabs/spaces")
                errors += 1
                continue

            # Tabs
            if "\t" in indent:
                print(f"⚠ {file_path}: line {i} — tab used (use spaces)")
                continue

            # Wrong indentation multiple
            if indent and (len(indent) % INDENT_SIZE != 0):
                print(
                    f"⚠ {file_path}: line {i} — indentation "
                    f"not a multiple of {INDENT_SIZE}"
                )

            # Trailing spaces
            if raw_line != raw_line.rstrip(" \t"):
                print(f"⚠ {file_path}: line {i} — trailing spaces")

    return errors


def main():
    total_errors = 0

    yaml_files = find_yaml_files(DIRECTORY)
    print(yaml_files)

    if not yaml_files:
        print(f"No YAML files found in '{DIRECTORY}'")
        sys.exit(0)

    for file_path in yaml_files:
        print("\n" + "-" * 60)
        print(f"🔍 Checking: {file_path}")

        # Empty file
        total_errors += check_for_empty_file(file_path)

        # Read file contents
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"❌ Cannot read {file_path}: {e}")
            total_errors += 1
            continue

        # Base YAML validity
        total_errors += run_yq(file_path, ".", "base syntax check")

        # Extended checks via yq
        for expr in EXTENDED_CHECKS:
            total_errors += run_yq(file_path, expr, f"check '{expr}'")

        # Deprecated GitHub Actions
        total_errors += check_for_deprecated_keys(file_path, content)

        # Indentation & whitespace
        total_errors += check_indentation(file_path)

    print("\n" + "=" * 60)
    if total_errors > 0:
        print(f"❌ Total errors found: {total_errors}")
        sys.exit(1)
    else:
        print("✅ YAML file is valid!")
        # sys.exit(0)
        return yaml_files
    

def build_dot_scheme(test_files):
    """Shell-func to build dot scheme for successfully validate yml files"""
    for f in test_files:
        f = Path(f)
        output_file = f"{f.stem}.png"

        try:
            cmd = f'"{YML2_DOT_DIR}" "{str(f)}" | dot -Tpng > "{output_file}"'

            subprocess.run(cmd, shell=True, check=True)
            
            print(f"✅ {f} → {output_file} generated")
        except subprocess.CalledProcessError as e:
            print(f"Error while creating scheme for: {f}")
            if e.stderr:
                print(e.stderr.strip())
            return 1
        
    sys.exit(0)


if __name__ == "__main__":
    test = main()
    if test:
        build_dot_scheme(test_files=test)
    else:
        print('here')
        sys.exit(0)
