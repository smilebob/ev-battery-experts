"""
FastMCP Server for EV Battery State of Health (SOH) Analysis
Exposes battery diagnostic, multi-chemistry pack lookup, forecasting,
and certificate generation tools via the Model Context Protocol (MCP).
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any

from analyzer import SOHAnalyzer
from chemistries import VEHICLE_CATALOG, infer_pack_from_capacity
from certificate import generate_certificate_html


def analyze_battery(
    csv_path: str,
    output_html: Optional[str] = None,
    lang: str = "en",
    annual_km: Optional[float] = None,
    forecast_years: int = 3,
    min_delta: float = 40.0,
    vin: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyzes an EV charging telemetry CSV file, models battery capacity and SOH degradation,
    evaluates statistical confidence intervals, and optionally generates an interactive report.
    """
    path = Path(csv_path)
    if not path.exists():
        return {"error": f"File '{csv_path}' does not exist."}

    analyzer = SOHAnalyzer(
        min_delta_soc=min_delta,
        lang=lang,
        annual_km=annual_km,
        forecast_years=forecast_years,
        vin=vin
    )

    clean_df = analyzer.load_data(path)
    result = analyzer.analyze(clean_df)

    pack_key, pack_info = infer_pack_from_capacity(result.initial_capacity)

    report_path_str = None
    if output_html:
        out_p = Path(output_html)
        analyzer.generate_html_report(result, out_p)
        report_path_str = str(out_p.resolve())

    return {
        "status": "success",
        "vehicle_inferred": {
            "make": pack_info.make,
            "model": pack_info.model,
            "variant": pack_info.variant,
            "chemistry": pack_info.chemistry.code,
            "nominal_kwh": pack_info.nominal_usable_kwh
        },
        "soh": {
            "current_soh_pct": round(result.current_soh, 2),
            "soh_margin_err_pct": round(result.current_soh_err, 2),
            "current_capacity_kwh": round(result.current_capacity, 2),
            "capacity_margin_err_kwh": round(result.current_capacity_err, 2),
            "baseline_capacity_kwh": round(result.initial_capacity, 2),
            "total_degradation_pct": round(result.total_degradation_pct, 2)
        },
        "telemetry": {
            "total_charges": result.total_charges,
            "qualified_charges": result.qualified_charges,
            "odometer_km": result.odometer_max,
            "annual_km_pace": round(result.annual_km, 0),
            "dc_charge_energy_pct": result.dc_energy_pct,
            "mean_charge_temp_celsius": result.mean_temperature
        },
        "forecast_realistic": [
            {
                "horizon": sm.horizon_label,
                "target_date": sm.target_date.strftime("%Y-%m-%d"),
                "projected_odometer_km": round(sm.projected_odometer, 0),
                "soh_pct": sm.soh_realistic,
                "capacity_kwh": sm.cap_realistic
            }
            for sm in result.scenario_milestones
        ],
        "report_file": report_path_str
    }


def get_vehicle_pack_catalog() -> Dict[str, Any]:
    """
    Returns available electric vehicle battery packs, nominal capacities, and chemistry profiles.
    """
    return {
        key: {
            "make": p.make,
            "model": p.model,
            "variant": p.variant,
            "usable_kwh": p.nominal_usable_kwh,
            "gross_kwh": p.gross_kwh,
            "chemistry": p.chemistry.code,
            "typical_cycle_life": p.chemistry.typical_cycle_life_80
        }
        for key, p in VEHICLE_CATALOG.items()
    }


if __name__ == "__main__":
    # Test execution
    res = analyze_battery(
        "/home/pierre/.gemini/antigravity/brain/971ff791-e6d6-46ec-9dd1-ffe2e4e62f4a/.user_uploaded/media_1792945222586_550f994e.csv"
    )
    print(json.dumps(res, indent=2))
