# 📖 Complete Installation Guide

This guide covers installing the **EV Battery SOH Analyzer** across different operating systems (**Linux, macOS, Windows**) using modern package managers (**uv, pip**).

---

## 📋 General Requirements

* **Python**: Version **3.9** or higher (supports Python 3.9, 3.10, 3.11, 3.12, 3.13, and 3.14+).
* **Git**: To clone the repository.

Verify your Python version:
```bash
python3 --version  # or 'python --version' on Windows
```

---

## 🛠️ Method 1: Installation with `uv` (Recommended - Fast & Isolated)

[`uv`](https://github.com/astral-sh/uv) is an extremely fast Python package manager.

### Linux / macOS:
```bash
# 1. Clone repository
git clone https://github.com/smilebob/ev-battery-experts.git
cd ev-battery-experts

# 2. Create virtual environment
uv venv

# 3. Activate virtual environment
source .venv/bin/activate

# 4. Install package in editable mode
uv pip install -e .
```

### Windows (PowerShell):
```powershell
# 1. Clone repository
git clone https://github.com/smilebob/ev-battery-experts.git
cd ev-battery-experts

# 2. Create virtual environment
uv venv

# 3. Activate virtual environment
.venv\Scripts\Activate.ps1

# 4. Install package
uv pip install -e .
```

---

## 🐍 Method 2: Standard Installation with `pip`

You can also use standard Python `venv` and `pip`.

### Linux / macOS:
```bash
git clone https://github.com/smilebob/ev-battery-experts.git
cd ev-battery-experts
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```

### Windows (Command Prompt or PowerShell):
```cmd
git clone https://github.com/smilebob/ev-battery-experts.git
cd ev-battery-experts
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -e .
```

---

## 🧪 Verifying Installation

With the environment activated, check the CLI:
```bash
ev-battery-soh --help
```
The help screen should display:
```text
usage: main.py [-h] [--output OUTPUT] [--min-delta MIN_DELTA]
               [--mapping [MAPPING ...]]
               csv_path

Electric Vehicle Battery State of Health (SOH) and Capacity Degradation Analyzer
...
```

---

## 🤖 Installing for Google Antigravity

To register this skill and agent persona globally inside your Google Antigravity environment:

```bash
# Link skill globally
mkdir -p ~/.gemini/config/skills
ln -sfn "$(pwd)/skills/ev-battery-soh" ~/.gemini/config/skills/ev-battery-soh

# Link agent persona globally
mkdir -p ~/.gemini/config/agents
ln -sfn "$(pwd)/agents/ev-battery-expert.md" ~/.gemini/config/agents/ev-battery-expert.md
```
