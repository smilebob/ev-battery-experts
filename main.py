#!/usr/bin/env python3
"""
CLI entry point for EV Battery SOH Analysis
Supports multilingual reporting: English (--lang en), French (--lang fr), Spanish (--lang es).
Supports future degradation forecasting with custom or auto-detected annual mileage (--annual-km).
"""

import argparse
import sys
from pathlib import Path
from analyzer import SOHAnalyzer
from i18n import TRANSLATIONS


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

    print(f"Loading and detecting columns from '{args.csv_path}'...")
    analyzer = SOHAnalyzer(
        custom_mapping=custom_mapping,
        min_delta_soc=args.min_delta,
        lang=args.lang,
        annual_km=args.annual_km,
        forecast_years=args.forecast_years,
    )

    try:
        clean_df = analyzer.load_data(args.csv_path)
        print(f"-> {len(clean_df)} valid charge sessions extracted.")

        print("Computing battery degradation, local regression, and electrochemical future projections...")
        result = analyzer.analyze(clean_df)

        print("\n" + "=" * 65)
        print(f"       BATTERY SOH ASSESSMENT & FORECAST RESULTS ({args.lang.upper()})       ")
        print("=" * 65)
        print(f"Period analyzed      : {result.date_min.strftime('%Y-%m-%d')} -> {result.date_max.strftime('%Y-%m-%d')}")
        print(f"Qualified sessions   : {result.qualified_charges} (threshold: Δ% ≥ {args.min_delta}%)")
        if result.odometer_max > 0:
            print(f"Current odometer     : {result.odometer_max:,.0f} km")
        print(f"Baseline capacity C0 : {result.initial_capacity:.2f} kWh")
        print(f"Current capacity     : {result.current_capacity:.2f} ± {result.current_capacity_err:.2f} kWh (95% CI)")
        print(f"Current SOH          : {result.current_soh:.2f}% ± {result.current_soh_err:.2f}%")
        print(f"Total degradation    : {result.total_degradation_pct:.2f}% ({result.initial_capacity - result.current_capacity:.2f} kWh lost)")
        print("-" * 65)
        print(f"Assumed Annual Rate  : {result.annual_km:,.0f} km/year" + (" (user override)" if args.annual_km else " (auto historical mean)"))
        print("ELECTROCHEMICAL FUTURE PROJECTIONS:")
        for fp in result.forecast_points:
            print(f"  {fp.horizon_label:8s} ({fp.target_date.strftime('%Y-%m-%d')}) | {fp.projected_odometer:,.0f} km : SOH {fp.projected_soh:.2f}% ± {fp.projected_soh_err:.2f}% (Cap: {fp.projected_capacity:.2f} kWh)")
        print("=" * 65 + "\n")

        print(f"Generating interactive professional HTML report in '{args.lang}'...")
        analyzer.generate_html_report(result, args.output)
        print(f"-> Report ready: {args.output.resolve()}\n")

    except Exception as e:
        print(f"Error during analysis: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
