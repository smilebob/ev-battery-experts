#!/usr/bin/env python3
"""
CLI entry point for EV Battery SOH Analysis
Supports multilingual reporting: English (--lang en), French (--lang fr), Spanish (--lang es).
Supports refined multi-scenario degradation forecasting (Optimistic, Realistic, Severe)
incorporating DC fast-charging ratio, Arrhenius thermal kinetics, and 100% calibration weighting.
"""

import argparse
import sys
from pathlib import Path
from analyzer import SOHAnalyzer
from i18n import TRANSLATIONS
from chemistries import infer_pack_from_capacity
from certificate import generate_certificate_html


def parse_mapping(mapping_args):
    """
    Parses key=value arguments into a dict.
    Example: --mapping date=Date energy_added="Energy added"
    """
    mapping = {}
    if not mapping_args:
        return mapping
    for item in mapping_args:
        if "=" in item:
            k, v = item.split("=", 1)
            mapping[k.strip()] = v.strip()
    return mapping


def main():
    parser = argparse.ArgumentParser(
        description="Electric Vehicle Battery State of Health (SOH) and Capacity Degradation Analyzer"
    )
    parser.add_argument("csv_path", type=Path, help="Path to the charging telemetry CSV file")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("battery_soh_report.html"),
        help="Path for output HTML report (default: battery_soh_report.html)",
    )
    parser.add_argument(
        "--lang",
        "-l",
        type=str,
        default="en",
        choices=["en", "fr", "es"],
        help="Report language: en (English), fr (French), es (Spanish). Default: en",
    )
    parser.add_argument(
        "--min-delta",
        type=float,
        default=40.0,
        help="Minimum battery %% variation to qualify a charge session (default: 40)",
    )
    parser.add_argument(
        "--annual-km",
        type=float,
        default=None,
        help="Annual mileage in km for degradation projection (default: automatically computed from historical odometer data)",
    )
    parser.add_argument(
        "--forecast-years",
        type=int,
        default=3,
        help="Number of future years to project degradation (default: 3)",
    )
    parser.add_argument(
        "--certificate",
        "-c",
        type=Path,
        default=None,
        help="Generate a tamper-evident certified battery inspection sheet HTML (e.g., certificate.html)",
    )
    parser.add_argument(
        "--vin",
        type=str,
        default=None,
        help="Vehicle Identification Number (VIN - 17 alphanumeric characters, ISO 3779)",
    )
    parser.add_argument(
        "--mapping",
        "-m",
        nargs="*",
        help="Custom column mapping in key=value format (e.g., date=Date energy_added='Energy added')",
    )

    args = parser.parse_args()

    if not args.csv_path.exists():
        print(f"Error: File '{args.csv_path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    custom_mapping = parse_mapping(args.mapping)

    # VIN format check (ISO 3779: 17 characters, no I, O, Q)
    normalized_vin = None
    if args.vin:
        v = args.vin.strip().upper()
        if len(v) != 17 or any(c in v for c in ("I", "O", "Q")):
            print(f"Warning: Specified VIN '{v}' does not strictly match standard ISO 3779 (17 alphanumeric chars without I, O, Q).", file=sys.stderr)
        normalized_vin = v

    print(f"Loading and detecting columns from '{args.csv_path}'...")
    analyzer = SOHAnalyzer(
        custom_mapping=custom_mapping,
        min_delta_soc=args.min_delta,
        lang=args.lang,
        annual_km=args.annual_km,
        forecast_years=args.forecast_years,
        vin=normalized_vin,
    )

    try:
        clean_df = analyzer.load_data(args.csv_path)
        print(f"-> {len(clean_df)} valid charge sessions extracted.")

        print("Computing refined electrochemical degradation with Arrhenius thermal kinetics & DC stress factors...")
        result = analyzer.analyze(clean_df)

        print("\n" + "=" * 70)
        print(f"       BATTERY SOH ASSESSMENT & MULTI-SCENARIO FORECAST ({args.lang.upper()})       ")
        print("=" * 70)
        print(f"Period analyzed      : {result.date_min.strftime('%Y-%m-%d')} -> {result.date_max.strftime('%Y-%m-%d')}")
        print(f"Qualified sessions   : {result.qualified_charges} (threshold: Δ% ≥ {args.min_delta}%)")
        if result.odometer_max > 0:
            print(f"Current odometer     : {result.odometer_max:,.0f} km")
        if result.vin:
            print(f"Vehicle VIN          : {result.vin}")
        print(f"DC fast-charge share : {result.dc_energy_pct:.1f}% energy ({result.dc_charges_count} DC sessions)")
        print(f"Mean charge temp     : {result.mean_temperature:.1f} °C (Arrhenius factor applied)")
        print(f"Baseline capacity C0 : {result.initial_capacity:.2f} kWh")
        print(f"Current capacity     : {result.current_capacity:.2f} ± {result.current_capacity_err:.2f} kWh (95% CI)")
        print(f"Current SOH          : {result.current_soh:.2f}% ± {result.current_soh_err:.2f}%")
        print(f"Total degradation    : {result.total_degradation_pct:.2f}% ({result.initial_capacity - result.current_capacity:.2f} kWh lost)")
        print("-" * 70)
        print(f"Projected Annual Rate: {result.annual_km:,.0f} km/year" + (" (user override)" if args.annual_km else " (auto historical mean)"))
        print("MULTI-SCENARIO PROJECTIONS (Optimistic / Realistic / Severe):")
        for sm in result.scenario_milestones:
            print(f"  {sm.horizon_label:8s} ({sm.target_date.strftime('%Y-%m-%d')}) | {sm.projected_odometer:,.0f} km : "
                  f"Opt: {sm.soh_optimistic:.2f}% ({sm.cap_optimistic:.2f}k) | "
                  f"Real: {sm.soh_realistic:.2f}% ({sm.cap_realistic:.2f}k) | "
                  f"Sev: {sm.soh_severe:.2f}% ({sm.cap_severe:.2f}k)")
        print("=" * 70 + "\n")

        print(f"Generating interactive professional HTML report in '{args.lang}'...")
        analyzer.generate_html_report(result, args.output)
        print(f"-> Report ready: {args.output.resolve()}\n")

        if args.certificate:
            pack_key, pack_info = infer_pack_from_capacity(result.initial_capacity)
            v_info = {
                "make": pack_info.make,
                "model": f"{pack_info.model} {pack_info.variant}",
                "chemistry": pack_info.chemistry.name
            }
            generate_certificate_html(result, args.csv_path, args.certificate, v_info, lang=args.lang, vin=result.vin)
            print(f"-> Certificate ready: {args.certificate.resolve()}\n")

    except Exception as e:
        print(f"Error during analysis: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
