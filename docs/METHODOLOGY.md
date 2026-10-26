# 🔬 Scientific Methodology & Mathematical Modeling

This document details the physical principles and statistical methods implemented by **EV Battery SOH Analyzer** to compute capacity degradation and State of Health (SOH).

---

## 1. Physical Principle of Charging Telemetry

Unlike intrusive and costly bench testing, telemetric charging session analysis leverages real-world operational logs.

### Key Distinction: Net Energy Added vs Gross AC Energy Used
* **`Energy used` (Wall meter energy)**: Accounts for on-board charger efficiency (85–95%), cable Joule heating, and thermal preconditioning (heating/cooling). **It must never be used to calculate cell capacity.**
* **`Energy added` (Pack intake energy)**: The actual net energy stored electrochemically in the battery cells.

For each charging session $i$:
$$\Delta\%_i = \%_{\text{End}, i} - \%_{\text{Start}, i}$$
$$C_i = \frac{E_{\text{added}, i}}{\Delta\%_i} \times 100$$

Where $C_i$ is the apparent total battery pack capacity during session $i$ (in kWh).

---

## 2. Digital Discretization Noise & Thresholding

Consumer EV telemetry loggers typically store State of Charge as **integer values** ($80\%$, $81\%$, etc.).

### Discretization Error Analysis:
Consider a shallow charge from $50\%$ to $55\%$ ($\Delta\% = 5\%$):
* True unrounded values could be $50.4\%$ and $54.6\%$, meaning $\Delta\%_{\text{true}} = 4.2\%$.
* The relative error in capacity estimation is:
  $$\text{Relative Error} = \frac{5 - 4.2}{4.2} \approx 19\%$$
* Conversely, on a charge with $\Delta\% \ge 40\%$, the boundary discretization error is bounded by:
  $$\frac{\pm 0.5 + \pm 0.5}{40} = \frac{\pm 1}{40} = \pm 2.5\%$$
  *(and falls below $\pm 1\%$ on deep $80\%$ charges)*.

**Applied Rule:** Only sessions with $\Delta\% \ge 40\%$ are admitted into the statistical regression model.

---

## 3. Gaussian Kernel Local Regression (LOWESS) & Error Bounds

EV battery degradation does not follow a simple linear path. It exhibits:
1. An initial steeper slope during the first 10,000 to 20,000 km (Solid Electrolyte Interphase - SEI layer stabilization).
2. Plateaus and apparent capacity recovery phases associated with BMS high-voltage recalibrations.
3. A very gradual, steady degradation phase thereafter.

To capture these dynamics without imposing rigid model constraints, we apply **Gaussian local polynomial regression**:

For each target evaluation date $t_0$, we solve:
$$\min_{\beta_0, \beta_1} \sum_{i=1}^n w_i(t_0) \left( C_i - (\beta_0 + \beta_1 (t_i - t_0)) \right)^2$$

Where weights follow a Gaussian kernel:
$$w_i(t_0) = \exp\left( -\frac{1}{2}\left(\frac{t_i - t_0}{h}\right)^2 \right)$$
With an adaptive bandwidth parameter $h$.

### 95% Confidence Interval (Error Margin):
For each fitted estimate $\hat{C}(t_0) = \hat{\beta}_0$, the local weighted residual variance is computed:
$$s^2(t_0) = \frac{\sum w_i (C_i - \hat{C}_i)^2}{\sum w_i \left(1 - \frac{1}{\text{eff\_n}}\right)}$$
$$\text{Margin of Error (95\% CI)} = \pm 1.96 \times s(t_0)$$

This confidence band captures seasonal temperature shifts, measurement dispersion, and statistical variance.

---

## 4. State of Health (SOH) Computation

The baseline capacity when new ($C_0$) is determined by the median capacity of initial sessions (first 10% of qualifying data or first 5,000 km).

$$\text{SOH}(t) = \frac{\hat{C}(t)}{C_0} \times 100$$
$$\text{SOH Uncertainty}(t) = \frac{1.96 \times s(t)}{C_0} \times 100$$

---

## 5. Semi-Empirical Electrochemical Aging Forecasting

To project future degradation over 1 to 5+ years without assuming linear decay, we implement a semi-empirical model based on lithium-ion degradation kinetics:

$$C_{\text{pred}}(t, \text{km}) = C_0 - \left( \alpha \sqrt{t} \cdot f_{\text{Arrh}}(T) + \beta \cdot (1 + 1.8 \cdot r_{\text{DC}}) \cdot \text{km} + L_{\text{knee}}(t, \text{km}) \right)$$

Where:
* **$\alpha \sqrt{t} \cdot f_{\text{Arrh}}(T)$ (Calendar Aging & SEI Passivation)**: Governed by the parabolic diffusion rate of solvent molecules through the solid electrolyte interphase (SEI) on the negative electrode, modulated by Arrhenius thermal activation.
* **$\beta \cdot (1 + 1.8 \cdot r_{\text{DC}}) \cdot \text{km}$ (Cyclic Aging & Active Material Loss)**: Mechanical particle cracking and lithium loss scaled by the DC fast-charging stress ratio $r_{\text{DC}}$.
* **$L_{\text{knee}}(t, \text{km})$ (Non-Linear End-of-Life Knee Point)**: Represents late-stage cell exhaustion (loss of cyclable lithium inventory, electrolyte dry-out, and active material degradation):
  $$L_{\text{knee}}(t, \text{km}) = 0.50 \left[ \left(\max\left(0, \frac{\text{cycles} - \text{cycle\_threshold}}{350}\right)\right)^2 + \left(\max\left(0, \frac{t - 12.0}{3.0}\right)\right)^2 \right]$$
  This captures the pronounced downward curvature (knee) naturally observed after 12–15 years or beyond 2,500–3,000 equivalent full cycles.

### Future Confidence Cone:
Because future uncertainty naturally compounds over time, the predictive confidence cone expands asymptotically:
$$\text{Uncertainty}(t_{\text{future}}) = \pm 1.96 \cdot s(t_0) \sqrt{1 + 0.35 \cdot \Delta t_{\text{years}}}$$
This accurately bounds potential deviations in driving habits, extreme seasonal temperatures, or DC fast-charging intensity.
