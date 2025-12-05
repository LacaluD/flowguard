"""Constant Storage"""

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

DEPRECATED_ACTIONS = ["setup-python@v3", "checkout@v4", "telegram-action@v1"]