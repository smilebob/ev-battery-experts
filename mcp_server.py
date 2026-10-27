"""
Official Model Context Protocol (MCP) Server for EV Battery State of Health (SOH) Analysis.
Built on MCP Python SDK (v2 / MCPServer).
Exposes tools for:
  - Battery capacity and SOH degradation analysis (CSV ingestion)
  - Official signed PDF certificate generation with QR code and SHA-256 seal
  - Vehicle pack & multi-chemistry catalog lookup
  - Cryptographic token verification
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any

from mcp.server.mcpserver import MCPServer

from analyzer import SOHAnalyzer
from chemistries import VEHICLE_CATALOG, infer_pack_from_capacity
from pdf_certificate import generate_certified_pdf
from verifier import verify_certificate_token

# Initialize MCP Server
mcp = MCPServer(name="ev-battery-soh-server")


@mcp.tool()
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
    Analyzes EV charging session telemetry (CSV), filters discretization noise,
    models capacity degradation using Gaussian local regression (LOWESS) with 95% confidence intervals,
    and returns comprehensive electrochemical indicators and multi-scenario forecasts.

    Args:
        csv_path: Absolute or relative path to the charging CSV export.
        output_html: Optional path to save an interactive Plotly HTML report.
        lang: Language for reports ('en', 'fr', 'es').
        annual_km: Optional override for projected annual mileage in km.
        forecast_years: Number of years for predictive degradation forecasting (default 3).
        min_delta: Minimum SoC variation % to admit charge session into model (default 40.0).
        vin: Optional 17-character Vehicle Identification Number.
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


@mcp.tool()
def generate_inspection_certificate(
    csv_path: str,
    output_pdf_path: str,
    vin: Optional[str] = None,
    lang: str = "fr",
    private_key_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates an official, tamper-evident, cryptographically signed battery inspection PDF certificate
    using ECDSA P-256 and SHA-256 with an embedded verification QR code.

    Args:
        csv_path: Path to the vehicle charging telemetry CSV.
        output_pdf_path: Output file path for the signed PDF certificate.
        vin: Optional 17-character Vehicle Identification Number.
        lang: Language of the certificate ('fr', 'en', 'es').
        private_key_path: Optional path to custom ECDSA private key PEM file.
    """
    path = Path(csv_path)
    if not path.exists():
        return {"error": f"File '{csv_path}' does not exist."}

    analyzer = SOHAnalyzer(lang=lang, vin=vin)
    clean_df = analyzer.load_data(path)
    result = analyzer.analyze(clean_df)

    pack_key, pack_info = infer_pack_from_capacity(result.initial_capacity)
    v_info = {
        "make": pack_info.make,
        "model": f"{pack_info.model} {pack_info.variant}",
        "chemistry": pack_info.chemistry.name
    }

    pdf_out = Path(output_pdf_path)
    priv_p = Path(private_key_path) if private_key_path else None

    cert_info = generate_certified_pdf(
        result=result,
        csv_file=path,
        output_pdf_path=pdf_out,
        vehicle_info=v_info,
        lang=lang,
        vin=result.vin,
        private_key_path=priv_p
    )

    return {
        "status": "success",
        "certificate_id": cert_info["certificate_id"],
        "pdf_path": cert_info["pdf_path"],
        "dataset_hash": cert_info["dataset_hash"],
        "signature_b64": cert_info["signature_b64"],
        "verification_uri": cert_info["verification_uri"]
    }


@mcp.tool()
def verify_certificate(token_or_uri: str) -> Dict[str, Any]:
    """
    Verifies the cryptographic authenticity and integrity of a certificate URI or QR payload.

    Args:
        token_or_uri: The verification URI or QR content (e.g. 'ev-soh://verify?id=...&sig=...').
    """
    return verify_certificate_token(token_or_uri)


@mcp.tool()
def get_vehicle_pack_catalog() -> Dict[str, Any]:
    """
    Returns available electric vehicle battery packs, nominal capacities, and chemistry profiles
    (LFP, NMC, NCA, Sodium-Ion) for Tesla, Stellantis, Renault, VW Group, MG, Hyundai, and Kia.
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
    # Runs standard stdio MCP transport for AI agent pairing
    mcp.run()
