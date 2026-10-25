# 📘 User Manual & Practical Guide

This manual explains how to operate the **EV Battery SOH Analyzer**, interpret generated assessment reports, and configure custom data sources.

---

## 🚀 1. Basic CLI Usage

The primary command is `ev-battery-soh` (or `python3 main.py`).

### Syntax:
```bash
ev-battery-soh <path_to_file.csv> [options]
```

### Example:
```bash
ev-battery-soh charging_logs.csv -o battery_assessment.html
```
This command automatically:
1. Reads `charging_logs.csv`.
2. Auto-detects telemetric columns.
3. Filters shallow sessions to remove BMS integer rounding noise.
4. Performs Gaussian local regression and computes 95% confidence bands.
5. Emits the interactive report to `battery_assessment.html`.

---

## 🗂️ 2. Supported CSV File Formats

The analyzer features an intelligent synonym dictionary supporting popular EV telemetry loggers.

### Native Support:
* **TeslaMate**: Columns `Date`, `Energy added`, `% Start`, `% End`, `Odometer`, `Location`, `Type`.
* **Tronity**: Columns `timestamp`, `charged_kwh`, `start_soc`, `end_soc`, `mileage`.
* **ABRP (A Better Routeplanner)**: Standard charging session exports.
* **OpenEVSE / Home Assistant / Wallbox**: Generic charging session logs with net energy and SoC.

### Required Fields:
| Metric | Supported Header Examples |
| :--- | :--- |
| **Date & Time** | `Date`, `datetime`, `timestamp`, `start_date`, `time` |
| **Net Energy Added** | `Energy added`, `kwh_added`, `charge_kwh`, `energie_ajoutee` |
| **Start State of Charge** | `% Start`, `soc_start`, `battery_start`, `start_soc` |
| **End State of Charge** | `% End`, `soc_end`, `battery_end`, `end_soc` |
| **Odometer** *(Optional)* | `Odometer`, `mileage`, `km`, `compteur` |

---

## 🛠️ 3. Advanced CLI Options

### A. Custom Column Mapping (`--mapping` or `-m`)
If your file uses custom or localized column names, map them explicitly:
```bash
ev-battery-soh raw_export.csv \
  -m date="Session_Timestamp" \
     energy_added="Delivered_Kwh" \
     soc_start="Initial_SoC_Pct" \
     soc_end="Final_SoC_Pct" \
     odometer="Odo_Reading_Km" \
  -o report.html
```

### B. Adjusting Qualification Threshold (`--min-delta`)
By default, sessions with $\Delta\% \ge 40\%$ are analyzed to eliminate integer rounding noise.
* To relax the threshold and include moderate charges:
  ```bash
  ev-battery-soh charges.csv --min-delta 30 -o report.html
  ```
* To restrict strictly to deep full charges:
  ```bash
  ev-battery-soh charges.csv --min-delta 60 -o report.html
  ```

---

## 📊 4. Interpreting the Report

The generated HTML report includes 4 core sections:

### 1. Executive Summary & KPIs
* **Current SOH & Margin of Error**: e.g., `95.81% ± 2.42% (95% CI)`. Indicates 95% statistical certainty that true battery health lies within this range.
* **Current Usable Capacity**: Maximum deliverable energy when charged to 100%.
* **Baseline Capacity ($C_0$)**: Median capacity established when the battery was new.

### 2. Chart 1: Usable Capacity (kWh) vs Time
* **Dark points**: Actual recorded charging sessions.
* **Solid blue line**: Central trend trajectory (Gaussian weighted local regression).
* **Translucent blue band**: 95% confidence uncertainty interval.

### 3. Chart 2: State of Health (%) vs Time
* Normalized percentage health over time relative to baseline ($C_0$).

### 4. Chart 3: Degradation vs Odometer Distance
* Battery capacity correlated directly with vehicle travel distance.

### 5. Quarterly Breakdown Table & Reliability Rating (★)
* Each quarter receives a 1 to 5 star rating based on sample size, 100% calibration events, and residual variance.

---

## 🖨️ 5. Exporting to PDF

The report stylesheet includes dedicated `@media print` rules:
1. Open the `.html` report in Chrome, Firefox, Safari, or Edge.
2. Press `Ctrl + P` (or `Cmd + P` on macOS).
3. Select **"Save as PDF"**.
4. Enable **"Background graphics"**.
5. Save a clean, multi-page executive assessment PDF document.
