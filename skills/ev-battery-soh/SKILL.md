---
name: ev-battery-soh
description: Advanced telemetric State of Health (SOH) and battery capacity degradation analyzer for electric vehicles (Tesla, Tronity, ABRP, or generic charging CSV exports). Calculates residual usable capacity, local statistical regression with 95% uncertainty band, quarterly breakdown with reliability ratings, electrochemical future forecasting (SEI growth ∝ √t + cyclic wear ∝ km), and generates executive-grade interactive HTML/PDF reports in English, French, or Spanish.
---

# EV Battery SOH Analysis & Forecasting Skill

This skill allows any AI Agent (Google Antigravity, Claude Code, Cursor, AutoGPT, OpenAI Swarm/Assistants) to analyze EV charging session telemetric logs, evaluate current SOH, model statistical uncertainty, and project future degradation trajectories based on driving habits.

---

## 🚀 Execution & Usage

Run the tool using the global CLI command or standalone Python:
```bash
# Basic run (automatic annual mileage from data, English report)
ev-battery-soh "/path/to/charges.csv" -o "/path/to/soh_report.html"

# French report with user-defined annual mileage (e.g. 20,000 km/year) for 4 years
ev-battery-soh "/path/to/charges.csv" --lang fr --annual-km 20000 --forecast-years 4 -o rapport.html

# Spanish report
ev-battery-soh "/path/to/charges.csv" --lang es -o informe.html
```

---

## 📊 Core Capabilities

1. **Automatic & Fault-Tolerant Column Detection**:
   Seamlessly parses CSV exports from **TeslaMate**, **Tronity**, **ABRP**, **OpenEVSE**, and custom loggers.
   Custom column mapping override supported via `--mapping`.

2. **Statistical Modeling & Uncertainty Bounds (95% CI)**:
   * **Noise Filtering**: Retains charging sessions with $\Delta\% \ge 40\%$ to eliminate integer percentage truncation noise from onboard BMS telemetry.
   * **Gaussian Kernel Local Regression (LOWESS)**: Non-parametric curve fitting capturing non-linear degradation and BMS recalibration plateaus without rigid modeling assumptions.
   * **95% Confidence Band**: Computed from local weighted residual variance ($\pm 1.96 \times \sigma_{\text{local}}$).

3. **Electrochemical Future Forecasting**:
   * Combines **parabolic calendar passivation** (SEI layer growth $\propto \sqrt{t}$) with **cyclic degradation** ($\propto \text{km}$).
   * Automatically derives baseline annual mileage from historical odometer logs, or accepts user custom projections via `--annual-km`.
   * Projects future capacity and SOH milestones (+1 yr, +2 yr, +3 yr, up to `--forecast-years`).
   * Visualizes the future trajectory on Plotly charts with a dashed projection line and expanding 95% uncertainty cone.

4. **Official Tamper-Evident & Signed PDF Certificate**:
   * Generates a standalone, vector PDF inspection certificate with ReportLab.
   * Signed with **ECDSA P-256** and SHA-256 (supports custom user private key or auto-generated agent key).
   * Encodes verifiable payload into an embedded high-resolution **QR-Code**.
   * Instant verification via `--verify-token` CLI or mobile scanner.

5. **Standalone Web Portal & Portainer Docker Stack**:
   * Complete web application powered by **FastAPI** (`http://localhost:8000`).
   * Authenticated Admin dashboard for runtime physical tuning, ECDSA key management, and multi-user access (bcrypt/JWT).
   * Deployable via Docker Compose and Portainer Stacks (`portainer-stack.yml`) with automated multi-arch GitHub Actions image builds.

6. **Executive & Modern Multilingual HTML Report**:
   * Languages: English (`--lang en`), French (`--lang fr`), Spanish (`--lang es`).
   * Interactive Plotly charts (zoom, hover tooltips, responsive).
   * Certified Quarterly breakdown table with 1 to 5 star reliability ratings (★).
   * Dedicated future projections table with target dates, projected mileage, and confidence intervals.
   * Print-optimized layout (native one-click PDF export via browser).

---

## ⚙️ CLI Arguments

* `-o`, `--output`: Output HTML report filepath (default: `battery_soh_report.html`).
* `-l`, `--lang`: Report language: `en`, `fr`, or `es` (default: `en`).
* `--vin`: Vehicle Identification Number (VIN - 17 alphanumeric characters, ISO 3779 standard).
* `--pdf-certificate`: Generate an official, tamper-evident, cryptographically signed inspection PDF certificate with embedded QR-Code.
* `--private-key`: Custom ECDSA/RSA private key PEM file for signing (default: autonomous local agent key).
* `--verify-token`: Cryptographically verifies the authenticity of a certificate URI or QR payload.
* `--annual-km`: Projected annual driving distance in km (default: automatically computed from odometer logs).
* `--forecast-years`: Number of years to project forward (default: `3`).
* `--certificate`, `-c`: Generate a tamper-evident certified battery inspection sheet HTML (e.g. `cert.html`).
* `--min-delta`: Minimum battery state of charge variation $\Delta\%$ required to qualify a session (default: `40.0`).
* `-m`, `--mapping`: Custom column override for unconventional CSV headers.

---

## 💡 Interpreting Results for the User
When presenting conclusions, the agent should structure the response around:
1. **Current Usable Capacity & SOH**: in kWh and % with 95% error margin.
2. **Current Aging Evaluation**: comparing against fleet benchmarks for the specific cell chemistry (e.g. LFP vs NMC).
3. **Future Projections**: state the assumed annual mileage, and provide expected SOH and capacity at +1, +2, and +3 years.
4. **Report Link**: absolute or relative link to the interactive HTML report.
