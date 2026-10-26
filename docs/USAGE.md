# 📘 User Manual & Practical Guide

This manual explains how to operate the **EV Battery SOH Analyzer**, interpret generated assessment reports, and configure custom data sources.

---

## 🚀 1. Basic CLI Usage

The primary command is `ev-battery-soh` (or `python3 main.py`).

### Syntax:
```bash
ev-battery-soh <path_to_file.csv> [options]
```

### Multi-language Reports (`--lang` or `-l`):
Generate executive reports in **English**, **French**, or **Spanish**:
```bash
# English (Default)
ev-battery-soh charges.csv --lang en -o report_en.html

# French (Français) with explicit Vehicle Identification Number (VIN)
ev-battery-soh charges.csv --lang fr --vin XP7YGCEK7PB123456 -o rapport_fr.html

# Spanish (Español)
ev-battery-soh charges.csv --lang es -o informe_es.html
```

### Future Degradation Forecasting (`--annual-km` and `--forecast-years`):
By default, the tool calculates the historical annual mileage from your odometer data and projects degradation over 3 years.
You can customize the projection horizon and annual driving pace:
```bash
# Project 4 years ahead assuming 25,000 km/year
ev-battery-soh charges.csv --annual-km 25000 --forecast-years 4 -o report_forecast.html
```

### Official Resale Certificate Generation (`--certificate` or `-c`):
Generate a tamper-evident, sealed battery inspection certificate with SHA-256 fingerprint, VIN, and condition grade (A+, A, B, C, D) for vehicle resale:
```bash
ev-battery-soh charges.csv --vin XP7YGCEK7PB123456 -c certificate_resale.html
```

---

## 🤖 2. Model Context Protocol (MCP) Integration

The project includes a native MCP server (`mcp_server.py`) exposing battery diagnostics to AI environments (Antigravity, Claude Desktop, Cursor):

* **Available MCP Tools**:
  * `analyze_battery`: Analyzes CSV, models degradation, and outputs structured JSON diagnostics.
  * `get_vehicle_pack_catalog`: Returns nominal capacities and chemistry profiles for all registered EV models.

* **Starting the MCP Server**:
```bash
python3 mcp_server.py
```

---

## 🗂️ 3. Supported CSV Formats & Auto-Detection

The analyzer features polymorphic ingestion (`parsers.py`) and an intelligent synonym dictionary supporting popular EV telemetry loggers.

### Native Loggers Auto-Detected:
* **TeslaMate**: Columns `Date`, `Energy added`, `% Start`, `% End`, `Odometer`, `Location`, `Type`.
* **ScanMyTesla (CAN-bus)**: Columns `timestamp`, `nominal_full_pack`, `odometer`, `soc`, `cell_temp`.
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

## 🔬 4. Multi-Chemistry & Vehicle Pack Catalog

The analyzer incorporates a comprehensive vehicle pack and electrochemical profile database (`chemistries.py`). It automatically infers or applies specific degradation parameters:

* **Chemistries modeled**:
  * `LFP` (Lithium Ferrophosphate - CATL, BYD Blade): High cyclability (3000-5000 cycles), sensitive to calendar aging and flat OCV calibration drift.
  * `NMC_811` / `NMC_622` (Nickel Manganese Cobalt): High energy density, higher Arrhenius sensitivity ($E_a \approx 28.5\text{ kJ/mol}$), accelerated cyclic fade at high C-rate.
  * `NCA` (Nickel Cobalt Aluminum - Panasonic Tesla): High power performance, linear initial degradation followed by distinct rollover.
  * `SODIUM_ION` (Na-Ion - CATL Na-pack): Zero cobalt/lithium, robust low-temperature resilience, high cycle stability.

* **Supported Vehicle Packs**:
  * Tesla Model Y / Model 3 (LFP 60 kWh, Long Range NMC 78.1 kWh, Performance NCA 82 kWh).
  * Renault Mégane E-Tech / Scénic (60 kWh & 87 kWh NMC).
  * Stellantis e-208 / e-2008 / e-308 (50 kWh & 54 kWh NMC).
  * Volkswagen ID.3 / ID.4 / ID.Buzz (58 kWh & 77 kWh NMC).
  * MG 4 Electric (51 kWh LFP & 64 kWh NMC).
  * Hyundai Ioniq 5 / Kia EV6 (58 kWh, 77.4 kWh, 84 kWh NMC).

---

## 🛠️ 5. Advanced CLI Options

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

## 📊 6. Interpreting the Report

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

## 🌐 8. Web Application & Docker Deployment

The solution includes a full-featured, standalone web portal powered by **FastAPI** with Tailwind CSS and an authenticated **Administration Dashboard**.

### Running Locally without Docker:
```bash
uvicorn web_app:app --host 0.0.0.0 --port 8000
```
Then open `http://localhost:8000` in your web browser.

### Running with Docker Compose:
```bash
docker compose up -d
```
* **Public Interface (`http://localhost:8000`)**: Web drag-and-drop CSV upload, VIN entry, interactive SOH visualization, and direct downloads of signed PDF certificates and HTML reports.
* **Admin Dashboard (`http://localhost:8000/admin`)**:
  * Default Credentials: Username `admin` / Password `admin1234` *(prompted to update on first login)*.
  * Runtime algorithmic tuning (minimum $\Delta\% \text{SoC}$, 100% calibration multiplier, knee-point switch).
  * Cryptographic key management: ECDSA P-256 public key export and keypair regeneration.
  * Multi-user management (Admin, Auditor, Viewer roles) with salted `bcrypt` password protection.
* **Data Persistence**: Telemetry data, SQLite database, and cryptographic keys are safely persisted in `./data` and `./keys`.

The report stylesheet includes dedicated `@media print` rules:
1. Open the `.html` report in Chrome, Firefox, Safari, or Edge.
2. Press `Ctrl + P` (or `Cmd + P` on macOS).
3. Select **"Save as PDF"**.
4. Enable **"Background graphics"**.
5. Save a clean, multi-page executive assessment PDF document.
