---
name: ev-battery-soh
description: Advanced telemetric State of Health (SOH) and battery capacity degradation analyzer for electric vehicles (Tesla, Tronity, ABRP, or generic charging CSV exports). Calculates residual usable capacity, local statistical regression with 95% uncertainty band, quarterly breakdown with reliability ratings, and generates executive-grade interactive HTML/PDF reports.
---

# EV Battery SOH Analysis Skill

This skill allows any AI Agent (Google Antigravity, Claude Code, Cursor, AutoGPT, OpenAI Swarm/Assistants) to analyze EV charging session telemetric logs and produce a scientific, executive-grade battery health assessment report.

---

## 🚀 Universal Execution

Run the tool using the global command or the standalone Python entry point:
```bash
# Option 1: Via global CLI command (if installed via pip install -e .)
ev-battery-soh "/path/to/charges.csv" -o "/path/to/soh_report.html"

# Option 2: Via standalone script
python3 main.py "/path/to/charges.csv" -o "/path/to/soh_report.html"
```

---

## 📊 Core Features

1. **Automatic & Fault-Tolerant Column Detection**:
   Seamlessly parses CSV exports from:
   * **TeslaMate** (`Date`, `Energy added`, `% Start`, `% End`, `Odometer`, `Location`, `Type`)
   * **Tronity** (`timestamp`, `charged_kwh`, `start_soc`, `end_soc`, `mileage`)
   * **ABRP / OpenEVSE / Home Assistant / Generic Wallbox logs**.
   * Custom column mapping override supported via `--mapping`.

2. **Statistical Modeling & Uncertainty Bounds (95% CI)**:
   * **Noise Filtering**: Retains charging sessions with $\Delta\% \ge 40\%$ to eliminate integer percentage truncation noise from onboard BMS telemetry.
   * **Gaussian Kernel Local Regression (LOWESS)**: Non-parametric curve fitting capturing non-linear degradation and BMS recalibration plateaus without rigid modeling assumptions.
   * **95% Confidence Band**: Computed from local weighted residual variance ($\pm 1.96 \times \sigma_{\text{local}}$).

3. **Executive & Modern HTML/PDF Report**:
   * Interactive Plotly charts (zoom, hover tooltips, responsive).
   * Chart 1: Chronological usable capacity trajectory (kWh) with uncertainty band.
   * Chart 2: State of Health (SOH %) evolution over time.
   * Chart 3: Degradation correlated with odometer distance.
   * Quarterly certified breakdown table: Median, standard deviation, and reliability star ratings (★).
   * Print-optimized layout (native one-click PDF export via browser).

---

## ⚙️ CLI Arguments

* `-o`, `--output`: Output HTML report filepath (default: `battery_soh_report.html`).
* `--min-delta`: Minimum battery state of charge variation $\Delta\%$ required to qualify a session (default: `40.0`).
* `-m`, `--mapping`: Custom column override for unconventional CSV headers:
  ```bash
  ev-battery-soh data.csv -m date=timestamp energy_added=charge_kwh soc_start=initial_soc soc_end=final_soc odometer=km_counter
  ```

---

## 💡 Interpreting Results for the User
When presenting conclusions, the agent should structure the response around:
1. **Initial Baseline vs Current Usable Capacity**: in kWh with 95% error margin.
2. **Current SOH (%)**: with confidence interval.
3. **Aging Dynamics**: comparing degradation against fleet averages for the specific cell chemistry (e.g., LFP vs NMC/NCA, typically 3% to 5% loss at 60,000 km for LFP).
4. **Report Link**: absolute or relative link to the interactive HTML report.
