# Project Goal
This is a console tool for validating yml configs.
Project is created to help developers validate and create schemas of their yml configs.

---

## Features
Under the hood project is running 2 third-party projects:
[YML2DOT](https://github.com/lucasepe/yml2dot) and [YQ](https://github.com/mikefarah/yq)

- Basic YAML syntax validation via yq
- Custom checks for required fields (extensible)
- Detection of deprecated actions
- Indentation and formatting checks
- Generate DOT scheme diagrams via yml2dot

Project was tested on python3.17 for now only on Windows 10.
Cross-platform support for macOS and Ubuntu Linux will be added later.

---

## Dependencies
Project does not use any side Python third-party libraries.
However external tools `yq` and `yml2dot` are required.

---

## Installation
Clone the repository
```
git clone https://github.com/LacaluD/YML-Validator-Scheme-converter
```

Create a virtual environment (optional but recommended)
```bash
python -m venv venv
source venv/bin/activate
```

### On Windows
```PowerShell
venv\Scripts\activate
```

Currently there is no automated run script.
See TODO block for usage instructions.

---

## Project Structure
```text
YML_Validator_Schemes/
│
├─ src/                       # Core logic and modules
│  ├─ logic.py                # Main logic
│  ├─ platform_check.py       # Corr-platform executable search
│  └─ constants.py            # Constants storage
│
├─ tests/                       # Unit tests (planned)
│
├─ main.py                    # entry point
├─ README.md
└─ gitignore
```

---

## TODO
- Change all prints to logging methods with separate logic
- Separate logic by classes
- Optimize
<!-- Скорее всего будет простой запрос в консоли для того,
чтоб можно было легко задать местоположение нужного конфиг файла -->