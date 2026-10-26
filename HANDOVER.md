# 🤝 Agent Handover & Architecture Memory (HANDOVER.md)

**Project:** `ev-battery-experts` (Universal EV Battery State of Health Analyzer & AI Agent Platform)  
**Location:** `/home/pierre/Projets/SOH`  
**GitHub Repository:** [https://github.com/smilebob/ev-battery-experts](https://github.com/smilebob/ev-battery-experts)  
**Author:** Pierre Roth (`smilebob`)  
**License:** BSD 3-Clause License  
**Last Updated:** October 26, 2026  

---

## 📌 Executive Summary

`ev-battery-experts` is an autonomous, scientifically grounded, and portable telemetric battery health (**State of Health - SOH**) assessment, certification, and forecasting platform for electric vehicles.

It processes raw charging session logs without requiring proprietary cloud tokens or physical CAN-bus hardware. Key features include:
1. **Multi-Source Ingestion (`parsers.py`)**: Automatic fingerprinting and parsing for **TeslaMate**, **ScanMyTesla (CAN-bus)**, **Tronity**, **ABRP**, **OpenEVSE**, and generic CSV loggers.
2. **Multi-Chemistry Pack Database (`chemistries.py`)**: Physical parameter modeling for **LFP**, **NMC/NCM**, **NCA**, and **Sodium-Ion**, with automated pack matching across Tesla, Stellantis, Renault, VW Group, MG, Hyundai, and Kia.
3. **Refined Physics & Statistical Engine (`analyzer.py`)**:
   - Noise filtering on shallow charges ($\Delta\% \ge 40\%$).
   - Statistical prioritization of 100% calibration sessions (weight $2.5\times$).
   - Arrhenius thermal kinetics modeling based on charge temperature (`Temp` column).
   - DC fast-charging stress weighting ($1.8\times r_{\text{DC}}$).
   - Non-linear end-of-life **Knee-point** acceleration beyond 12–15 years or 2,500+ equivalent full cycles.
4. **Multi-Scenario Predictive Forecasting**:
   - Compares **Optimistic (Gentle AC)**, **Realistic (Baseline)**, and **Severe (High DC)** trajectories with expanding 95% uncertainty cones.
5. **Certified Deliverables**:
   - Interactive multilingual HTML/PDF reports in **English**, **French**, and **Spanish** (`i18n.py`).
   - Tamper-evident **Battery Health Inspection Certificates** with SHA-256 cryptographic dataset hashing and condition grades (A+ to D) for vehicle resale (`certificate.py`).
6. **Native Model Context Protocol Server (`mcp_server.py`)**:
   - Directly exposes battery diagnostic and forecasting tools to AI agents (Antigravity, Claude Desktop, Cursor, etc.).

---

## 📂 Project Architecture & Component Inventory

| File / Component | Role & Architecture Details |
| :--- | :--- |
| [`main.py`](file:///home/pierre/Projets/SOH/main.py) | CLI entry point with argparse (`--output`, `--lang`, `--min-delta`, `--annual-km`, `--forecast-years`, `--certificate`, `--mapping`). |
| [`analyzer.py`](file:///home/pierre/Projets/SOH/analyzer.py) | Statistical & physical core: local LOWESS regression, Arrhenius kinetics, DC stress, knee-point, Plotly vector charts, Jinja2 template. |
| [`parsers.py`](file:///home/pierre/Projets/SOH/parsers.py) | Polymorphic ingestion engine auto-detecting TeslaMate, ScanMyTesla, Tronity, and generic charging CSVs. |
| [`chemistries.py`](file:///home/pierre/Projets/SOH/chemistries.py) | Chemistry profiles (LFP, NMC, NCA, Na-Ion) and vehicle catalog with automated capacity-based pack inference. |
| [`certificate.py`](file:///home/pierre/Projets/SOH/certificate.py) | Official sealed battery certificate generator with SHA-256 data fingerprint and condition grading (A+ to D). |
| [`mcp_server.py`](file:///home/pierre/Projets/SOH/mcp_server.py) | Model Context Protocol (MCP) server providing native agent tools (`analyze_battery`, `get_vehicle_pack_catalog`). |
| [`i18n.py`](file:///home/pierre/Projets/SOH/i18n.py) | Centralized translations for reports, charts, tables, and inspection sheets in English (`en`), French (`fr`), and Spanish (`es`). |
| [`pyproject.toml`](file:///home/pierre/Projets/SOH/pyproject.toml) | Standard PEP 517/621 packaging (Hatchling, Python $\ge 3.9$ compatible). Exposes `ev-battery-soh` executable. |
| [`LICENSE`](file:///home/pierre/Projets/SOH/LICENSE) | Official BSD 3-Clause open-source license. |
| [`skills/ev-battery-soh/SKILL.md`](file:///home/pierre/Projets/SOH/skills/ev-battery-soh/SKILL.md) | Universal Agent Skill specification for Antigravity and external agentic frameworks. |
| [`agents/ev-battery-expert.md`](file:///home/pierre/Projets/SOH/agents/ev-battery-expert.md) | Specialized AI Agent persona prompt for EV battery diagnostics and multi-scenario forecasting. |
| [`docs/INSTALLATION.md`](file:///home/pierre/Projets/SOH/docs/INSTALLATION.md) | Step-by-step setup guide for Linux, macOS, and Windows using `uv` or `pip`. |
| [`docs/USAGE.md`](file:///home/pierre/Projets/SOH/docs/USAGE.md) | Command-line manual, CSV header rules, multi-language flags, forecasting options, certificate generation, and MCP setup. |
| [`docs/METHODOLOGY.md`](file:///home/pierre/Projets/SOH/docs/METHODOLOGY.md) | Physical and mathematical documentation: discretization proof, local regression, Arrhenius kinetics, DC stress, and knee-point formulation. |

---

## ⚙️ Global Antigravity & System Configuration

* **Global CLI binary:** `~/.local/bin/ev-battery-soh` points directly to the virtual environment runner. Callable from any directory.
* **Global Skill Symlink:** `~/.gemini/config/skills/ev-battery-soh` $\to$ `/home/pierre/Projets/SOH/skills/ev-battery-soh`.
* **Global Agent Symlink:** `~/.gemini/config/agents/ev-battery-expert.md` $\to$ `/home/pierre/Projets/SOH/agents/ev-battery-expert.md`.

---

## 🧪 Current Verification & Test Status

1. **CLI Execution & Core Tests:**
   * Default run on real Tesla Model Y dataset (58,610 km): SOH $96.00\% \pm 1.99\%$.
   * Certificate generation: validated via `--certificate cert.html` with valid SHA-256 hash.
   * Multi-language rendering: verified in English (`--lang en`), French (`--lang fr`), and Spanish (`--lang es`).
   * Multi-scenario forecasting: validated up to 20 years with visible non-linear knee inflection.
   * MCP server test: validated with JSON output from `analyze_battery`.
2. **Git & Portability:**
   * Clean working tree on branch `main`.
   * Fully synchronised with GitHub `origin/main`.
   * Zero machine-specific hardcoded paths.

---

## 🔮 Future Roadmap & Ideas (TODO)

If future agents extend this project, consider:
- [ ] Connect `mcp_server.py` to Home Assistant via custom integration or WebSocket.
- [ ] Add direct automated PDF conversion using headless Chromium or `weasyprint`.
- [ ] Expand vehicle database with commercial electric trucks and vans (Rivian, Ford F-150 Lightning).
