"""
EV Battery State of Health (SOH) and Capacity Degradation Analyzer
Supports multilingual reporting: English (en), French (fr), Spanish (es).
Includes electrochemical degradation modeling (SEI growth ∝ √t + cyclic wear ∝ km)
and predictive future forecasting.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from jinja2 import Template
from i18n import TRANSLATIONS

# Synonyms for flexible column auto-detection
COLUMN_SYNONYMS = {
    "date": ["date", "datetime", "start_date", "timestamp", "heure", "time", "fecha"],
    "energy_added": ["energy added", "energy_added", "kwh_added", "energy", "charge_kwh", "energie_ajoutee", "energie_ajoute", "energia_añadida", "energia_agregada"],
    "soc_start": ["% start", "soc_start", "start_soc", "battery_start", "soc_initial", "%_start", "start_pct", "bateria_inicio"],
    "soc_end": ["% end", "soc_end", "end_soc", "battery_end", "soc_final", "%_end", "end_pct", "bateria_fin"],
    "odometer": ["odometer", "odo", "km", "mileage", "kilometrage", "compteur", "kilometraje", "odometro"],
    "location": ["location", "station", "lieu", "charge_location", "ubicacion"],
    "charge_type": ["type", "charge_type", "fast_charge", "ac_dc", "tipo"]
}


@dataclass
class ForecastPoint:
    horizon_label: str
    target_date: datetime
    projected_odometer: float
    projected_capacity: float
    projected_capacity_err: float
    projected_soh: float
    projected_soh_err: float
    total_degradation_pct: float


@dataclass
class SOHResult:
    analysis_date: datetime
    total_charges: int
    qualified_charges: int
    odometer_min: float
    odometer_max: float
    date_min: datetime
    date_max: datetime
    initial_capacity: float
    current_capacity: float
    current_capacity_err: float
    initial_soh: float
    current_soh: float
    current_soh_err: float
    total_degradation_pct: float
    annual_km: float
    forecast_points: List[ForecastPoint]
    quarterly_data: List[Dict[str, Any]]
    df_filtered: pd.DataFrame
    model_details: Dict[str, Any]
    min_delta_soc: float = 40.0


class SOHAnalyzer:
    def __init__(
        self,
        custom_mapping: Optional[Dict[str, str]] = None,
        min_delta_soc: float = 40.0,
        lang: str = "en",
        annual_km: Optional[float] = None,
        forecast_years: int = 3,
    ):
        self.custom_mapping = custom_mapping or {}
        self.min_delta_soc = min_delta_soc
        self.lang = lang if lang in TRANSLATIONS else "en"
        self.t = TRANSLATIONS[self.lang]
        self.custom_annual_km = annual_km
        self.forecast_years = forecast_years

    def detect_columns(self, df: pd.DataFrame) -> Dict[str, str]:
        cols = {c.strip().lower(): c for c in df.columns}
        mapping = {}

        for key, target_col in self.custom_mapping.items():
            if target_col in df.columns:
                mapping[key] = target_col
            elif target_col.strip().lower() in cols:
                mapping[key] = cols[target_col.strip().lower()]

        for key, syns in COLUMN_SYNONYMS.items():
            if key not in mapping:
                for s in syns:
                    if s in cols:
                        mapping[key] = cols[s]
                        break

        required = ["date", "energy_added", "soc_start", "soc_end"]
        missing = [r for r in required if r not in mapping]
        if missing:
            raise ValueError(
                f"Required columns not found: {missing}. Available columns: {list(df.columns)}. "
                f"Please specify custom mapping using --mapping date=... energy_added=..."
            )

        return mapping

    def parse_numeric(self, series: pd.Series) -> pd.Series:
        if pd.api.types.is_numeric_dtype(series):
            return series.astype(float)
        cleaned = series.astype(str).str.replace("%", "", regex=False)
        cleaned = cleaned.str.replace("km", "", regex=False)
        cleaned = cleaned.str.replace(" ", "", regex=False)
        cleaned = cleaned.str.replace(",", ".", regex=False)
        return pd.to_numeric(cleaned, errors="coerce")

    def load_data(self, file_path: Path) -> pd.DataFrame:
        df = pd.read_csv(file_path)
        col_map = self.detect_columns(df)

        clean_df = pd.DataFrame()
        date_series = pd.to_datetime(df[col_map["date"]], dayfirst=True, errors="coerce")
        clean_df["date"] = date_series

        clean_df["energy_added"] = self.parse_numeric(df[col_map["energy_added"]])
        clean_df["soc_start"] = self.parse_numeric(df[col_map["soc_start"]])
        clean_df["soc_end"] = self.parse_numeric(df[col_map["soc_end"]])

        if "odometer" in col_map:
            clean_df["odometer"] = self.parse_numeric(df[col_map["odometer"]])
        else:
            clean_df["odometer"] = np.nan

        if "location" in col_map:
            clean_df["location"] = df[col_map["location"]].astype(str)
        else:
            clean_df["location"] = "Unknown"

        if "charge_type" in col_map:
            clean_df["charge_type"] = df[col_map["charge_type"]].astype(str)
        else:
            clean_df["charge_type"] = "AC/DC"

        clean_df = clean_df.dropna(subset=["date", "energy_added", "soc_start", "soc_end"])
        clean_df["delta_soc"] = clean_df["soc_end"] - clean_df["soc_start"]
        clean_df = clean_df[clean_df["delta_soc"] > 0]

        clean_df["capacity_raw"] = (clean_df["energy_added"] / clean_df["delta_soc"]) * 100.0
        clean_df = clean_df.sort_values("date").reset_index(drop=True)
        return clean_df

    def _local_weighted_regression(
        self, x: np.ndarray, y: np.ndarray, x_eval: np.ndarray, bandwidth: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        y_fit = np.zeros_like(x_eval, dtype=float)
        y_std = np.zeros_like(x_eval, dtype=float)

        for i, target_x in enumerate(x_eval):
            diff = x - target_x
            weights = np.exp(-0.5 * (diff / bandwidth) ** 2)
            w_sum = np.sum(weights)
            if w_sum < 1e-6:
                y_fit[i] = np.mean(y)
                y_std[i] = np.std(y)
                continue

            W = np.diag(weights)
            X_mat = np.column_stack([np.ones_like(diff), diff])
            try:
                beta = np.linalg.pinv(X_mat.T @ W @ X_mat) @ (X_mat.T @ W @ y)
                y_fit[i] = beta[0]
                residuals = y - (beta[0] + beta[1] * diff)
                eff_n = (w_sum**2) / np.sum(weights**2)
                var = np.sum(weights * (residuals**2)) / max(1e-6, (w_sum * (1 - 1 / max(eff_n, 2))))
                y_std[i] = np.sqrt(max(0.05, var))
            except Exception:
                y_fit[i] = np.average(y, weights=weights)
                y_std[i] = np.std(y)

        return y_fit, y_std

    def _fit_electrochemical_model(
        self, t_years: np.ndarray, km_total: np.ndarray, cap_observed: np.ndarray, c0: float
    ) -> Tuple[float, float]:
        """
        Fits C(t, km) = C0 - (alpha * sqrt(t) + beta * km)
        where alpha = SEI passivation growth rate (calendar aging)
              beta = cyclic loss per km (cycling wear)
        """
        # Loss in kWh
        loss = np.maximum(0.0, c0 - cap_observed)
        # Features matrix: [sqrt(t), km]
        feat_sei = np.sqrt(np.maximum(0.01, t_years))
        feat_km = km_total

        X = np.column_stack([feat_sei, feat_km])
        # Non-negative least squares or bounded ridge regression
        try:
            # Linear regression without intercept (loss is 0 at t=0, km=0)
            res = np.linalg.lstsq(X, loss, rcond=None)[0]
            alpha, beta = float(res[0]), float(res[1])
            # Physical bounds check for LFP chemistry
            if alpha < 0 or beta < 0:
                # Fallback to dominant calendar SEI aging
                alpha = float(np.mean(loss / feat_sei))
                beta = 0.0
        except Exception:
            alpha = 1.2
            beta = 1.5e-5

        alpha = max(0.2, min(3.0, alpha))
        beta = max(0.0, min(5e-5, beta))
        return alpha, beta

    def analyze(self, df_raw: pd.DataFrame) -> SOHResult:
        df_filtered = df_raw[df_raw["delta_soc"] >= self.min_delta_soc].copy()

        median_cap = df_filtered["capacity_raw"].median()
        df_filtered = df_filtered[
            (df_filtered["capacity_raw"] >= median_cap * 0.70)
            & (df_filtered["capacity_raw"] <= median_cap * 1.30)
        ].copy()

        if len(df_filtered) < 3:
            raise ValueError("Insufficient qualified charging sessions to model SOH trajectory.")

        # Baseline capacity C0
        early_subset = df_filtered.head(max(5, int(len(df_filtered) * 0.12)))
        initial_capacity = float(early_subset["capacity_raw"].median())

        df_filtered["soh_raw"] = (df_filtered["capacity_raw"] / initial_capacity) * 100.0

        # Time features
        t_timestamps = df_filtered["date"].map(pd.Timestamp.timestamp).values
        t_days = (t_timestamps - t_timestamps[0]) / 86400.0
        y_cap = df_filtered["capacity_raw"].values

        bandwidth_days = max(45.0, (t_days[-1] - t_days[0]) * 0.15)
        eval_days = np.linspace(t_days[0], t_days[-1], 200)
        eval_dates = [datetime.fromtimestamp(t_timestamps[0] + d * 86400.0) for d in eval_days]

        cap_fit, cap_std = self._local_weighted_regression(t_days, y_cap, eval_days, bandwidth_days)

        current_capacity = float(cap_fit[-1])
        current_capacity_err = float(1.96 * cap_std[-1])

        current_soh = (current_capacity / initial_capacity) * 100.0
        current_soh_err = (current_capacity_err / initial_capacity) * 100.0
        total_degradation = 100.0 - current_soh

        # Odometer & Annual km calculation
        has_odometer = df_filtered["odometer"].notna().sum() > len(df_filtered) * 0.6
        total_days = max(1.0, (df_filtered["date"].max() - df_filtered["date"].min()).total_seconds() / 86400.0)
        total_years = total_days / 365.25

        if self.custom_annual_km is not None and self.custom_annual_km > 0:
            annual_km = float(self.custom_annual_km)
        elif has_odometer:
            odo_span = float(df_filtered["odometer"].max() - df_filtered["odometer"].min())
            annual_km = float((odo_span / total_days) * 365.25)
            annual_km = max(3000.0, annual_km)
        else:
            annual_km = 15000.0

        current_odometer = float(df_filtered["odometer"].max()) if has_odometer else 0.0

        # Electrochemical model fitting: C = C0 - (alpha * sqrt(t) + beta * km)
        t_years_series = t_days / 365.25
        km_series = (df_filtered["odometer"].values - df_filtered["odometer"].min()) if has_odometer else (t_years_series * annual_km)
        alpha, beta = self._fit_electrochemical_model(t_years_series, km_series, y_cap, initial_capacity)

        # Future forecasting
        last_date = df_filtered["date"].max()
        forecast_points: List[ForecastPoint] = []
        forecast_dates_dense: List[datetime] = []
        forecast_cap_dense: List[float] = []
        forecast_upper_dense: List[float] = []
        forecast_lower_dense: List[float] = []

        # Current calibration offset so prediction starts smoothly from current_capacity
        current_model_cap = initial_capacity - (alpha * np.sqrt(total_years) + beta * (current_odometer - (df_filtered['odometer'].min() if has_odometer else 0.0)))
        offset = current_capacity - current_model_cap

        # Dense evaluation points for smooth chart line
        dense_days = np.linspace(0, self.forecast_years * 365.25, 100)
        for d in dense_days:
            f_date = last_date + timedelta(days=float(d))
            t_f = total_years + (d / 365.25)
            km_f = (current_odometer - (df_filtered['odometer'].min() if has_odometer else 0.0)) + (d / 365.25) * annual_km
            pred_cap = initial_capacity - (alpha * np.sqrt(t_f) + beta * km_f) + offset
            # Uncertainty expands slightly with horizon
            uncert = current_capacity_err * np.sqrt(1.0 + 0.35 * (d / 365.25))

            forecast_dates_dense.append(f_date)
            forecast_cap_dense.append(pred_cap)
            forecast_upper_dense.append(pred_cap + uncert)
            forecast_lower_dense.append(pred_cap - uncert)

        # Milestone annual points (+1 yr, +2 yr, +3 yr, ...)
        for yr in range(1, self.forecast_years + 1):
            target_dt = last_date + timedelta(days=int(yr * 365.25))
            t_f = total_years + yr
            proj_odo = current_odometer + (yr * annual_km)
            km_delta = (current_odometer - (df_filtered['odometer'].min() if has_odometer else 0.0)) + (yr * annual_km)
            pred_cap = initial_capacity - (alpha * np.sqrt(t_f) + beta * km_delta) + offset
            uncert = current_capacity_err * np.sqrt(1.0 + 0.35 * yr)
            pred_soh = (pred_cap / initial_capacity) * 100.0
            pred_soh_err = (uncert / initial_capacity) * 100.0
            deg_pct = 100.0 - pred_soh

            label = f"+{yr} yr" if self.lang == "en" else (f"+{yr} an" if self.lang == "fr" else f"+{yr} año")
            forecast_points.append(
                ForecastPoint(
                    horizon_label=label,
                    target_date=target_dt,
                    projected_odometer=proj_odo,
                    projected_capacity=round(pred_cap, 2),
                    projected_capacity_err=round(uncert, 2),
                    projected_soh=round(pred_soh, 2),
                    projected_soh_err=round(pred_soh_err, 2),
                    total_degradation_pct=round(deg_pct, 2),
                )
            )

        # Odometer regression if available
        odo_eval = None
        cap_fit_odo = None
        cap_std_odo = None
        if has_odometer:
            df_odo = df_filtered.dropna(subset=["odometer"]).sort_values("odometer")
            x_odo = df_odo["odometer"].values
            y_cap_odo = df_odo["capacity_raw"].values
            if len(x_odo) >= 3 and (x_odo[-1] - x_odo[0]) > 100:
                odo_eval = np.linspace(x_odo[0], x_odo[-1], 200)
                bw_odo = max(2000.0, (x_odo[-1] - x_odo[0]) * 0.15)
                cap_fit_odo, cap_std_odo = self._local_weighted_regression(x_odo, y_cap_odo, odo_eval, bw_odo)

        # Quarterly breakdown
        df_filtered["quarter"] = df_filtered["date"].dt.to_period("Q").astype(str)
        quarterly_list = []
        for q, grp in df_filtered.groupby("quarter"):
            n_charges = len(grp)
            n_100 = int((grp["soc_end"] == 100).sum())
            c_med = float(grp["capacity_raw"].median())
            c_std = float(grp["capacity_raw"].std()) if n_charges > 1 else 0.0
            soh_med = float(grp["soh_raw"].median())
            soh_std = float(grp["soh_raw"].std()) if n_charges > 1 else 0.0
            odo_mean = float(grp["odometer"].mean()) if grp["odometer"].notna().any() else 0.0

            score = 3
            if n_charges >= 10:
                score += 1
            if n_charges >= 15 and n_100 >= 5:
                score += 1
            if c_std > 2.0 or n_charges < 3:
                score = max(1, score - 1)

            quarterly_list.append({
                "quarter": q,
                "n_charges": n_charges,
                "n_100": n_100,
                "odometer_mean": odo_mean,
                "capacity_median": c_med,
                "capacity_std": c_std,
                "soh_median": soh_med,
                "soh_std": soh_std,
                "reliability_score": min(5, max(1, score))
            })

        return SOHResult(
            analysis_date=datetime.now(),
            total_charges=len(df_raw),
            qualified_charges=len(df_filtered),
            odometer_min=float(df_filtered["odometer"].min()) if has_odometer else 0.0,
            odometer_max=float(df_filtered["odometer"].max()) if has_odometer else 0.0,
            date_min=df_filtered["date"].min(),
            date_max=df_filtered["date"].max(),
            initial_capacity=initial_capacity,
            current_capacity=current_capacity,
            current_capacity_err=current_capacity_err,
            initial_soh=100.0,
            current_soh=current_soh,
            current_soh_err=current_soh_err,
            total_degradation_pct=total_degradation,
            annual_km=annual_km,
            forecast_points=forecast_points,
            quarterly_data=quarterly_list,
            df_filtered=df_filtered,
            min_delta_soc=self.min_delta_soc,
            model_details={
                "eval_dates": [d.strftime("%Y-%m-%d") for d in eval_dates],
                "cap_fit": [round(v, 2) for v in cap_fit],
                "cap_upper": [round(v + 1.96 * s, 2) for v, s in zip(cap_fit, cap_std)],
                "cap_lower": [round(v - 1.96 * s, 2) for v, s in zip(cap_fit, cap_std)],
                "soh_fit": [round((v / initial_capacity) * 100.0, 2) for v in cap_fit],
                "soh_upper": [round(((v + 1.96 * s) / initial_capacity) * 100.0, 2) for v, s in zip(cap_fit, cap_std)],
                "soh_lower": [round(((v - 1.96 * s) / initial_capacity) * 100.0, 2) for v, s in zip(cap_fit, cap_std)],
                "forecast_dates": [d.strftime("%Y-%m-%d") for d in forecast_dates_dense],
                "forecast_cap": [round(v, 2) for v in forecast_cap_dense],
                "forecast_cap_upper": [round(v, 2) for v in forecast_upper_dense],
                "forecast_cap_lower": [round(v, 2) for v in forecast_lower_dense],
                "forecast_soh": [round((v / initial_capacity) * 100.0, 2) for v in forecast_cap_dense],
                "forecast_soh_upper": [round((v / initial_capacity) * 100.0, 2) for v in forecast_upper_dense],
                "forecast_soh_lower": [round((v / initial_capacity) * 100.0, 2) for v in forecast_lower_dense],
                "has_odometer": has_odometer,
                "odo_eval": [round(v, 0) for v in odo_eval] if odo_eval is not None else [],
                "cap_fit_odo": [round(v, 2) for v in cap_fit_odo] if cap_fit_odo is not None else [],
                "cap_upper_odo": [round(v + 1.96 * s, 2) for v, s in zip(cap_fit_odo, cap_std_odo)] if cap_fit_odo is not None else [],
                "cap_lower_odo": [round(v - 1.96 * s, 2) for v, s in zip(cap_fit_odo, cap_std_odo)] if cap_fit_odo is not None else [],
            }
        )

    def generate_figures(self, result: SOHResult) -> Dict[str, go.Figure]:
        figs = {}
        df = result.df_filtered
        m = result.model_details
        t = self.t

        # 1. Capacity vs Time (Historical + Forecast)
        fig_cap_time = go.Figure()
        # Historical confidence band
        fig_cap_time.add_trace(go.Scatter(
            x=m["eval_dates"] + m["eval_dates"][::-1],
            y=m["cap_upper"] + m["cap_lower"][::-1],
            fill="toself",
            fillcolor="rgba(14, 165, 233, 0.15)",
            line=dict(color="rgba(255,255,255,0)"),
            name=t["chart_cap_ci"],
            hoverinfo="skip"
        ))
        # Forecast confidence band
        fig_cap_time.add_trace(go.Scatter(
            x=m["forecast_dates"] + m["forecast_dates"][::-1],
            y=m["forecast_cap_upper"] + m["forecast_cap_lower"][::-1],
            fill="toself",
            fillcolor="rgba(249, 115, 22, 0.12)",
            line=dict(color="rgba(255,255,255,0)"),
            name=t["chart_cap_forecast_ci"],
            hoverinfo="skip"
        ))
        # Historical trend line
        fig_cap_time.add_trace(go.Scatter(
            x=m["eval_dates"],
            y=m["cap_fit"],
            mode="lines",
            line=dict(color="#0284c7", width=3),
            name=t["chart_cap_trend"]
        ))
        # Forecast projection line (dashed)
        fig_cap_time.add_trace(go.Scatter(
            x=m["forecast_dates"],
            y=m["forecast_cap"],
            mode="lines",
            line=dict(color="#ea580c", width=3, dash="dash"),
            name=t["chart_cap_forecast"]
        ))
        # Raw data points
        fig_cap_time.add_trace(go.Scatter(
            x=df["date"],
            y=df["capacity_raw"],
            mode="markers",
            marker=dict(color="#0f172a", size=6, opacity=0.45),
            name=t["chart_cap_points"].format(min_delta=result.min_delta_soc),
            hovertemplate="<b>" + t["axis_date"] + "</b>: %{x|%Y-%m-%d}<br><b>" + t["axis_capacity"] + "</b>: %{y:.2f} kWh<extra></extra>"
        ))
        fig_cap_time.update_layout(
            title=t["chart_cap_title"],
            xaxis_title=t["axis_date"],
            yaxis_title=t["axis_capacity"],
            template="plotly_white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=40, t=80, b=40),
            hovermode="x unified"
        )
        figs["capacity_time"] = fig_cap_time

        # 2. SOH vs Time (Historical + Forecast)
        fig_soh_time = go.Figure()
        # Historical band
        fig_soh_time.add_trace(go.Scatter(
            x=m["eval_dates"] + m["eval_dates"][::-1],
            y=m["soh_upper"] + m["soh_lower"][::-1],
            fill="toself",
            fillcolor="rgba(16, 185, 129, 0.15)",
            line=dict(color="rgba(255,255,255,0)"),
            name=t["chart_cap_ci"],
            hoverinfo="skip"
        ))
        # Forecast band
        fig_soh_time.add_trace(go.Scatter(
            x=m["forecast_dates"] + m["forecast_dates"][::-1],
            y=m["forecast_soh_upper"] + m["forecast_soh_lower"][::-1],
            fill="toself",
            fillcolor="rgba(249, 115, 22, 0.12)",
            line=dict(color="rgba(255,255,255,0)"),
            name=t["chart_cap_forecast_ci"],
            hoverinfo="skip"
        ))
        # Historical trend
        fig_soh_time.add_trace(go.Scatter(
            x=m["eval_dates"],
            y=m["soh_fit"],
            mode="lines",
            line=dict(color="#059669", width=3),
            name=t["chart_soh_trend"]
        ))
        # Forecast trend
        fig_soh_time.add_trace(go.Scatter(
            x=m["forecast_dates"],
            y=m["forecast_soh"],
            mode="lines",
            line=dict(color="#ea580c", width=3, dash="dash"),
            name=t["chart_soh_forecast"]
        ))
        # Raw points
        fig_soh_time.add_trace(go.Scatter(
            x=df["date"],
            y=df["soh_raw"],
            mode="markers",
            marker=dict(color="#0f172a", size=6, opacity=0.45),
            name=t["chart_soh_points"],
            hovertemplate="<b>" + t["axis_date"] + "</b>: %{x|%Y-%m-%d}<br><b>" + t["axis_soh"] + "</b>: %{y:.2f} %<extra></extra>"
        ))
        min_soh_plot = min(min(m["soh_lower"]), min(m["forecast_soh_lower"]))
        fig_soh_time.update_layout(
            title=t["chart_soh_title"],
            xaxis_title=t["axis_date"],
            yaxis_title=t["axis_soh"],
            yaxis_range=[max(70, min_soh_plot - 2), 103],
            template="plotly_white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=40, t=80, b=40),
            hovermode="x unified"
        )
        figs["soh_time"] = fig_soh_time

        # 3. Capacity vs Odometer
        if m["has_odometer"] and len(m["odo_eval"]) > 0:
            fig_odo = go.Figure()
            fig_odo.add_trace(go.Scatter(
                x=m["odo_eval"] + m["odo_eval"][::-1],
                y=m["cap_upper_odo"] + m["cap_lower_odo"][::-1],
                fill="toself",
                fillcolor="rgba(99, 102, 241, 0.15)",
                line=dict(color="rgba(255,255,255,0)"),
                name=t["chart_cap_ci"],
                hoverinfo="skip"
            ))
            fig_odo.add_trace(go.Scatter(
                x=m["odo_eval"],
                y=m["cap_fit_odo"],
                mode="lines",
                line=dict(color="#4f46e5", width=3),
                name=t["chart_odo_trend"]
            ))
            fig_odo.add_trace(go.Scatter(
                x=df["odometer"],
                y=df["capacity_raw"],
                mode="markers",
                marker=dict(color="#0f172a", size=6, opacity=0.45),
                name=t["chart_cap_points"].format(min_delta=result.min_delta_soc),
                hovertemplate="<b>" + t["axis_odometer"] + "</b>: %{x:,.0f} km<br><b>" + t["axis_capacity"] + "</b>: %{y:.2f} kWh<extra></extra>"
            ))
            fig_odo.update_layout(
                title=t["chart_odo_title"],
                xaxis_title=t["axis_odometer"],
                yaxis_title=t["axis_capacity"],
                template="plotly_white",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=40, r=40, t=80, b=40),
                hovermode="x unified"
            )
            figs["capacity_odometer"] = fig_odo

        return figs

    def generate_html_report(self, result: SOHResult, output_path: Path):
        figs = self.generate_figures(result)
        chart_cap_time_html = figs["capacity_time"].to_html(full_html=False, include_plotlyjs="cdn")
        chart_soh_time_html = figs["soh_time"].to_html(full_html=False, include_plotlyjs=False)
        chart_odo_html = figs["capacity_odometer"].to_html(full_html=False, include_plotlyjs=False) if "capacity_odometer" in figs else ""

        # Average annual SOH loss in forecast
        final_fp = result.forecast_points[-1]
        annual_loss = round((result.current_soh - final_fp.projected_soh) / len(result.forecast_points), 2)

        html_template = """<!DOCTYPE html>
<html lang="{{ lang }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ t.title }}</title>
    <style>
        :root {
            --primary: #0f172a;
            --primary-light: #1e293b;
            --accent: #0284c7;
            --success: #059669;
            --warning: #ea580c;
            --border: #e2e8f0;
            --bg-card: #ffffff;
            --bg-page: #f8fafc;
            --text-main: #0f172a;
            --text-muted: #64748b;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-page);
            color: var(--text-main);
            line-height: 1.5;
            padding: 30px 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
            color: #ffffff;
            padding: 40px;
            border-radius: 16px;
            box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.2);
            margin-bottom: 30px;
            position: relative;
        }
        .header .badge {
            display: inline-block;
            background: rgba(2, 132, 199, 0.3);
            border: 1px solid rgba(2, 132, 199, 0.6);
            color: #38bdf8;
            font-size: 0.78rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            padding: 4px 12px;
            border-radius: 20px;
            margin-bottom: 12px;
        }
        .header h1 {
            font-size: 2.2rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            margin-bottom: 8px;
        }
        .header p {
            color: #94a3b8;
            font-size: 1rem;
        }
        .meta-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-top: 24px;
            padding-top: 24px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
        }
        .meta-item {
            font-size: 0.85rem;
        }
        .meta-item .label {
            color: #94a3b8;
            display: block;
            margin-bottom: 2px;
        }
        .meta-item .val {
            color: #ffffff;
            font-weight: 600;
            font-size: 1rem;
        }
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .kpi-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 24px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .kpi-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 16px rgba(0,0,0,0.05);
        }
        .kpi-card .kpi-title {
            color: var(--text-muted);
            font-size: 0.82rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 8px;
        }
        .kpi-card .kpi-val {
            font-size: 2.3rem;
            font-weight: 800;
            color: var(--primary);
            letter-spacing: -0.03em;
            line-height: 1.1;
        }
        .kpi-card .kpi-sub {
            margin-top: 8px;
            font-size: 0.85rem;
            color: var(--text-muted);
        }
        .kpi-card.highlight {
            border-left: 4px solid var(--success);
        }
        .kpi-card.highlight .kpi-val {
            color: var(--success);
        }
        .section-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 28px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        }
        .section-card h2 {
            font-size: 1.35rem;
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 6px;
        }
        .section-card .section-desc {
            color: var(--text-muted);
            font-size: 0.9rem;
            margin-bottom: 20px;
        }
        .chart-container {
            margin: 20px 0;
            min-height: 440px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
            margin-top: 10px;
        }
        th, td {
            padding: 12px 14px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }
        th {
            background-color: #f1f5f9;
            color: var(--primary);
            font-weight: 700;
            font-size: 0.82rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }
        tr:hover td {
            background-color: #f8fafc;
        }
        .star-rating {
            color: #f59e0b;
            font-size: 1rem;
            letter-spacing: 2px;
        }
        .callout {
            background: #f0fdf4;
            border: 1px solid #bbf7d0;
            border-radius: 10px;
            padding: 18px 20px;
            color: #166534;
            font-size: 0.92rem;
            margin-top: 20px;
            line-height: 1.6;
        }
        .callout.forecast {
            background: #fff7ed;
            border: 1px solid #fed7aa;
            color: #9a3412;
        }
        .footer {
            text-align: center;
            color: var(--text-muted);
            font-size: 0.85rem;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid var(--border);
        }
        @media print {
            body { background: #ffffff; padding: 0; }
            .kpi-card, .section-card, .header { box-shadow: none; border: 1px solid #cbd5e1; }
            .header { background: #0f172a !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
            .chart-container { page-break-inside: avoid; }
        }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <span class="badge">{{ t.header_badge }}</span>
        <h1>{{ t.header_title }}</h1>
        <p>{{ t.header_subtitle }}</p>
        <div class="meta-grid">
            <div class="meta-item">
                <span class="label">{{ t.meta_date }}</span>
                <span class="val">{{ result.analysis_date.strftime('%Y-%m-%d %H:%M') }}</span>
            </div>
            <div class="meta-item">
                <span class="label">{{ t.meta_timeframe }}</span>
                <span class="val">{{ result.date_min.strftime('%Y-%m-%d') }} &rarr; {{ result.date_max.strftime('%Y-%m-%d') }}</span>
            </div>
            <div class="meta-item">
                <span class="label">{{ t.meta_sessions }}</span>
                <span class="val">{{ t.sessions_qualified.format(qualified=result.qualified_charges, total=result.total_charges) }}</span>
            </div>
            <div class="meta-item">
                <span class="label">{{ t.meta_mileage }}</span>
                <span class="val">{{ "{:,.0f}".format(result.odometer_max) }} km</span>
            </div>
        </div>
    </div>

    <!-- KPI GRID -->
    <div class="kpi-grid">
        <div class="kpi-card highlight">
            <div class="kpi-title">{{ t.kpi_soh_title }}</div>
            <div class="kpi-val">{{ "%.2f"|format(result.current_soh) }}%</div>
            <div class="kpi-sub">{{ t.kpi_soh_sub.format(err="%.2f"|format(result.current_soh_err))|safe }}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">{{ t.kpi_cap_title }}</div>
            <div class="kpi-val">{{ "%.2f"|format(result.current_capacity) }} <span style="font-size: 1.2rem; font-weight: 500;">kWh</span></div>
            <div class="kpi-sub">{{ t.kpi_cap_sub.format(err="%.2f"|format(result.current_capacity_err))|safe }}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">{{ t.kpi_baseline_title }}</div>
            <div class="kpi-val">{{ "%.2f"|format(result.initial_capacity) }} <span style="font-size: 1.2rem; font-weight: 500;">kWh</span></div>
            <div class="kpi-sub">{{ t.kpi_baseline_sub }}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">{{ t.kpi_deg_title }}</div>
            <div class="kpi-val">{{ "%.2f"|format(result.total_degradation_pct) }}%</div>
            <div class="kpi-sub">{{ t.kpi_deg_sub.format(loss="%.2f"|format(result.initial_capacity - result.current_capacity))|safe }}</div>
        </div>
    </div>

    <!-- CHARTS -->
    <div class="section-card">
        <h2>{{ t.sec1_title }}</h2>
        <p class="section-desc">{{ t.sec1_desc }}</p>
        <div class="chart-container">{{ chart_cap_time_html|safe }}</div>
    </div>

    <div class="section-card">
        <h2>{{ t.sec2_title }}</h2>
        <p class="section-desc">{{ t.sec2_desc.format(c0="%.2f"|format(result.initial_capacity)) }}</p>
        <div class="chart-container">{{ chart_soh_time_html|safe }}</div>
    </div>

    {% if chart_odo_html %}
    <div class="section-card">
        <h2>{{ t.sec3_title }}</h2>
        <p class="section-desc">{{ t.sec3_desc }}</p>
        <div class="chart-container">{{ chart_odo_html|safe }}</div>
    </div>
    {% endif %}

    <!-- FORECAST SECTION -->
    <div class="section-card">
        <h2>{{ t.sec4_title }}</h2>
        <p class="section-desc">{{ t.sec4_desc.format(annual_km=result.annual_km|round|int) }}</p>
        <table>
            <thead>
                <tr>
                    <th>{{ t.th_horizon }}</th>
                    <th>{{ t.th_target_date }}</th>
                    <th>{{ t.th_proj_km }}</th>
                    <th>{{ t.th_proj_cap }}</th>
                    <th>{{ t.th_proj_soh }}</th>
                    <th>{{ t.th_proj_loss }}</th>
                </tr>
            </thead>
            <tbody>
                {% for fp in result.forecast_points %}
                <tr>
                    <td><strong>{{ fp.horizon_label }}</strong></td>
                    <td>{{ fp.target_date.strftime('%Y-%m-%d') }}</td>
                    <td>{{ "{:,.0f}".format(fp.projected_odometer) }} km</td>
                    <td>{{ "%.2f"|format(fp.projected_capacity) }} ± {{ "%.2f"|format(fp.projected_capacity_err) }} kWh</td>
                    <td><strong>{{ "%.2f"|format(fp.projected_soh) }}% ± {{ "%.2f"|format(fp.projected_soh_err) }}%</strong></td>
                    <td>{{ "%.2f"|format(fp.total_degradation_pct) }}%</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        <div class="callout forecast">
            {{ t.forecast_callout.format(annual_loss=annual_loss, end_date=final_fp.target_date.strftime('%Y-%m-%d'), end_soh="%.2f"|format(final_fp.projected_soh), end_soh_err="%.2f"|format(final_fp.projected_soh_err))|safe }}
        </div>
    </div>

    <!-- QUARTERLY BREAKDOWN -->
    <div class="section-card">
        <h2>{{ t.sec5_title }}</h2>
        <p class="section-desc">{{ t.sec5_desc }}</p>
        <table>
            <thead>
                <tr>
                    <th>{{ t.th_quarter }}</th>
                    <th>{{ t.th_sessions }}</th>
                    <th>{{ t.th_100 }}</th>
                    <th>{{ t.th_mean_odo }}</th>
                    <th>{{ t.th_med_cap }}</th>
                    <th>{{ t.th_std_cap }}</th>
                    <th>{{ t.th_med_soh }}</th>
                    <th>{{ t.th_rating }}</th>
                </tr>
            </thead>
            <tbody>
                {% for q in result.quarterly_data %}
                <tr>
                    <td><strong>{{ q.quarter }}</strong></td>
                    <td>{{ q.n_charges }}</td>
                    <td>{{ q.n_100 }}</td>
                    <td>{{ "{:,.0f}".format(q.odometer_mean) }} km</td>
                    <td>{{ "%.2f"|format(q.capacity_median) }} kWh</td>
                    <td>&plusmn; {{ "%.2f"|format(q.capacity_std) }} kWh</td>
                    <td><strong>{{ "%.2f"|format(q.soh_median) }}%</strong></td>
                    <td><span class="star-rating">{{ "★" * q.reliability_score }}{{ "☆" * (5 - q.reliability_score) }}</span></td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        <div class="callout">
            {{ t.callout_text.format(soh="%.2f"|format(result.current_soh), soh_err="%.2f"|format(result.current_soh_err), odo="{:,.0f}".format(result.odometer_max))|safe }}
        </div>
    </div>

    <div class="footer">
        {{ t.footer_text.format(year=result.analysis_date.strftime('%Y')) }}
    </div>
</div>
</body>
</html>"""

        template = Template(html_template)
        rendered = template.render(
            t=self.t,
            lang=self.lang,
            result=result,
            annual_loss=annual_loss,
            final_fp=final_fp,
            chart_cap_time_html=chart_cap_time_html,
            chart_soh_time_html=chart_soh_time_html,
            chart_odo_html=chart_odo_html
        )

        output_path.write_text(rendered, encoding="utf-8")
        print(f"HTML report successfully generated ({self.lang.upper()}): {output_path}")
