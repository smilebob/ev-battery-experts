# 🔋 EV Battery SOH Analyzer & AI Agent

[![License](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)

An advanced, portable, telemetric battery capacity and **State of Health (SOH)** analyzer for electric vehicles. It estimates usable capacity trajectories, applies Gaussian local weighted regression with 95% uncertainty confidence bands, and generates an **executive-grade interactive HTML/PDF assessment report**.

Works seamlessly:
* **As a standalone CLI utility** on Linux, macOS, and Windows.
* **As an installable Python package** (`pip install .` or `uv pip install -e .`).
* **Within Google Antigravity** via its built-in skill and agent persona.
* **Within any AI Agent framework** (Claude Code, Cursor, AutoGPT, OpenAI Assistants).

---

## 📁 Repository Structure

```text
ev-battery-experts/
├── main.py                  # CLI executable entry point
├── analyzer.py              # Statistical engine, LOWESS regression, Plotly & Jinja2 report generator
├── chemistries.py           # Multi-chemistry battery database & vehicle pack catalog (LFP, NMC, NCA, Na-Ion)
├── parsers.py               # Polymorphic data ingestion (TeslaMate, ScanMyTesla, Tronity, Generic)
├── pdf_certificate.py       # Official signed PDF inspection certificate generator (ReportLab + QR Code)
├── crypto_signer.py         # ECDSA P-256 + SHA-256 cryptographic signing & key management engine
├── verifier.py              # Offline certificate verification & authenticity validator
├── web_app.py               # Standalone FastAPI web application with OpenAPI 3.1 & REST API
├── db.py                    # SQLite database models, bcrypt salted password hashing & JWT auth
├── templates/               # HTML5 & Tailwind CSS responsive UI templates (Public, Admin, Results)
├── mcp_server.py            # Model Context Protocol (MCP) server for AI assistants
├── Dockerfile               # Multi-stage lightweight production container
├── docker-compose.yml       # Local Docker Compose setup with persistent data volumes
├── portainer-stack.yml      # Portainer stack deployment template using GHCR image
├── pyproject.toml           # Standard PEP 517/621 packaging configuration
├── LICENSE                  # BSD 3-Clause License
├── docs/                    # 📚 Documentation
│   ├── INSTALLATION.md      # Installation guide (Linux, macOS, Windows, Docker, uv, pip)
│   ├── USAGE.md             # Practical guide, CLI options, REST API, Portainer & CSV formats
│   └── METHODOLOGY.md       # Physical principles & mathematical modeling
├── skills/
│   └── ev-battery-soh/
│       └── SKILL.md         # Universal Agent Skill definition
├── agents/
│   └── ev-battery-expert.md # AI Agent Persona specification
└── README.md
```

---

## 📚 Documentation

* **[Installation Guide](docs/INSTALLATION.md)**: Detailed step-by-step setup on Linux, macOS, and Windows.
* **[User Manual](docs/USAGE.md)**: CLI syntax, column mapping options, supported CSV formats, and PDF export.
* **[Scientific Methodology](docs/METHODOLOGY.md)**: Physical telemetry principles, discretization noise handling, and statistical confidence intervals.

---

## 📦 Quick Installation

Requires **Python 3.9 or higher**.

```bash
git clone https://github.com/smilebob/ev-battery-experts.git
cd ev-battery-experts

# Using standard pip:
pip install -e .

# Or using uv:
uv pip install -e .
```

---

## 🚀 Quick Usage

### 1. Automatic Column Detection (TeslaMate, Tronity, ABRP, etc.)
```bash
# English report (default)
ev-battery-soh /path/to/charging_logs.csv -o battery_report.html

# French report (Français)
ev-battery-soh /path/to/charging_logs.csv --lang fr -o rapport_fr.html

# Spanish report (Español)
ev-battery-soh /path/to/charging_logs.csv --lang es -o informe_es.html
```

### 2. Custom Column Mapping
For CSV files with non-standard column headers:
```bash
ev-battery-soh custom_export.csv \
  --mapping date=Timestamp energy_added=NetKwh soc_start=InitialSoC soc_end=FinalSoC odometer=MileageKm \
  -o battery_report.html
```

### 3. Adjusting Qualification Threshold
```bash
ev-battery-soh charges.csv --min-delta 30 -o battery_report.html
```

### 4. Signed Official PDF Certificate & VIN
Generate a sealed inspection certificate for vehicle resale signed with ECDSA P-256 and verified via QR-Code:
```bash
ev-battery-soh charges.csv --vin XP7YGCEK7PB123456 --pdf-certificate inspection_certificate.pdf
```

### 5. Standalone Web Portal & Portainer Deployment
Launch the interactive web UI and Admin panel:
```bash
# Locally:
uvicorn web_app:app --host 0.0.0.0 --port 8000

# Or via Docker:
docker compose up -d
```
Then visit `http://localhost:8000` (or `http://localhost:8000/docs` for the interactive Swagger OpenAPI documentation).

---

## 📊 Report Contents

The generated interactive HTML report provides:
1. **Executive Scorecard**: Current SOH with 95% margin of error ($\pm X\%$), current usable capacity ($\pm X\text{ kWh}$), baseline capacity $C_0$, and cumulative loss.
2. **Chart 1: Usable Capacity Trajectory & Projections (kWh)** with 95% confidence interval band and future predictive cone.
3. **Chart 2: State of Health (SOH %) & Multi-Year Forecast** over time.
4. **Chart 3: Degradation vs Odometer Mileage**.
5. **Section 4: Electrochemical Degradation Forecast Table**: Explicit breakdown (+1 yr, +2 yr, +3 yr) with projected dates, mileage, capacity, and SOH.
6. **Section 5: Certified Quarterly Breakdown Table**: Median, standard deviation, and reliability star ratings (★).
7. **Native Print-to-PDF**: Pre-styled for direct executive PDF exports via your browser (`Ctrl+P` / `Cmd+P`).

---

## 🤖 AI Agent Integration

* **Google Antigravity**: The skill is registered under [`skills/ev-battery-soh/SKILL.md`](skills/ev-battery-soh/SKILL.md) and can be invoked directly by Antigravity agents.
* **Claude Code / Cursor / OpenAI**: Point the agent to `skills/ev-battery-soh/SKILL.md` to grant autonomous battery telemetry assessment capabilities.

---

## 📄 License

This project is licensed under the **BSD 3-Clause License** - see the [LICENSE](LICENSE) file for details.
