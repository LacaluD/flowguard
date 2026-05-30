import subprocess

__version__ = "1.0.0"

try:
    __build__ = subprocess.check_output(
        ["git", "rev-list", "--count", "HEAD"],
        stderr=subprocess.DEVNULL,
    ).decode().strip()
    __commit__ = subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"],
        stderr=subprocess.DEVNULL,
    ).decode().strip()
except Exception:
    __build__ = "__dev__"
    __commit__ = "__dev__"