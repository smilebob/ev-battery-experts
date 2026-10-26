# 🤝 Agent Handover & Architecture Memory (HANDOVER.md)

**Project:** `ev-battery-experts` (EV Battery State of Health Analyzer & AI Agent)  
**Location:** `/home/pierre/Projets/SOH`  
**GitHub Repository:** [https://github.com/smilebob/ev-battery-experts](https://github.com/smilebob/ev-battery-experts)  
**Author:** Pierre Roth (`smilebob`)  
**License:** BSD 3-Clause License  
**Last Updated:** October 26, 2026  

---

## 📌 Executive Summary

This repository provides an autonomous, mathematically rigorous, and portable telemetric battery health (**State of Health - SOH**) assessment and forecasting suite for electric vehicles. 

It processes raw charging session logs (CSV from TeslaMate, Tronity, ABRP, OpenEVSE, or generic sources) without requiring CAN-bus hardware or cloud API tokens. The tool:
1. Filters out discretization noise from integer SoC readings ($\Delta\% \ge 40\%$).
2. Models degradation trajectories using non-parametric Gaussian local regression (LOWESS) with 95% confidence intervals (CI).
3. Forecasts future multi-year aging using a semi-empirical electrochemical kinetic model:
   $$\text{Capacity}(t, \text{km}) = C_0 - \left(\alpha \sqrt{t} + \beta \cdot \text{km}\right)$$
4. Emits executive-grade interactive HTML/PDF assessment reports in **English**, **French**, or **Spanish**.

---

## 📂 Project Architecture & Component Inventory

| File / Folder | Role & Description |
| :--- | :--- |
| [`main.py`](file:///home/pierre/Projets/SOH/main.py) | Standalone CLI entry point with argparse (`--output`, `--lang`, `--min-delta`, `--annual-km`, `--forecast-years`, `--mapping`). |
| [`analyzer.py`](file:///home/pierre/Projets/SOH/analyzer.py) | Core engine: data parsing, column auto-detection, LOWESS regression, electrochemical fitting, Plotly chart generation, Jinja2 report rendering. |
| [`i18n.py`](file:///home/pierre/Projets/SOH/i18n.py) | Centralized translation dictionary for reports, charts, infobulles, and tables in `en`, `fr`, and `es`. |
| [`pyproject.toml`](file:///home/pierre/Projets/SOH/pyproject.toml) | Standard PEP 517/621 packaging file (managed via `hatchling`, Python $\ge 3.9$ compatible). Exposes `ev-battery-soh` binary. |
| [`LICENSE`](file:///home/pierre/Projets/SOH/LICENSE) | Official BSD 3-Clause open-source license. |
| [`skills/ev-battery-soh/SKILL.md`](file:///home/pierre/Projets/SOH/skills/ev-battery-soh/SKILL.md) | Universal Agent Skill specification for Antigravity, Claude Code, Cursor, and OpenAI. |
| [`agents/ev-battery-expert.md`](file:///home/pierre/Projets/SOH/agents/ev-battery-expert.md) | Specialized AI Agent persona prompt for EV battery diagnostics and forecasting. |
| [`docs/INSTALLATION.md`](file:///home/pierre/Projets/SOH/docs/INSTALLATION.md) | Step-by-step setup guide for Linux, macOS, and Windows using `uv` or `pip`. |
| [`docs/USAGE.md`](file:///home/pierre/Projets/SOH/docs/USAGE.md) | Practical command-line manual, CSV header rules, custom mappings, and PDF export guide. |
| [`docs/METHODOLOGY.md`](file:///home/pierre/Projets/SOH/docs/METHODOLOGY.md) | Physical and mathematical documentation: discretization error proof, local regression, and SEI kinetics. |

---

## ⚙️ Global Antigravity & System Configuration

* **Global CLI command:** `~/.local/bin/ev-battery-soh` points directly to the virtual environment runner. Any user or subagent can run `ev-battery-soh` from any terminal directory.
* **Global Skill Symlink:** `~/.gemini/config/skills/ev-battery-soh` $\to$ `/home/pierre/Projets/SOH/skills/ev-battery-soh`.
* **Global Agent Symlink:** `~/.gemini/config/agents/ev-battery-expert.md` $\to$ `/home/pierre/Projets/SOH/agents/ev-battery-expert.md`.

---

## 🧪 Current Verification & Test Status

1. **CLI Execution Tests:**
   * Executed with default options on real Tesla Model Y dataset (58,610 km). Output: $95.76\% \pm 2.19\%$ SOH.
   * Multi-language rendering: verified in English (`--lang en`), French (`--lang fr`), and Spanish (`--lang es`).
   * Custom mileage projection: verified with `--annual-km 25000 --forecast-years 4`.
2. **Git & Portability:**
   * Clean working tree on branch `main`.
   * Fully synchronised with GitHub `origin/main`.
   * No hardcoded machine paths (`/home/pierre/...`) in published repository files.
   * Universal shebang: `#!/usr/bin/env python3`.

---

## 🔮 Future Roadmap & Ideas (TODO)

If future agents extend this project, consider:
- [ ] Add direct CAN-bus / ScanMyTesla log ingestion (`cell_temp_avg`, `nominal_full_pack`).
- [ ] Support temperature normalization via Arrhenius reaction kinetics when battery pack internal temperatures are available.
- [ ] Implement automated PDF generation via headless Chromium or `weasyprint` (currently done via browser native print-to-PDF).
