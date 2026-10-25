#!/home/pierre/Projets/SOH/.venv/bin/python
"""
CLI entry point for EV Battery SOH Analysis
"""

import argparse
import sys
from pathlib import Path
from analyzer import SOHAnalyzer


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
        description="Analyse de State of Health (SOH) et dégradation de batterie pour véhicule électrique"
    )
    parser.add_argument("csv_path", type=Path, help="Chemin vers le fichier CSV de sessions de recharge")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("rapport_soh.html"),
        help="Chemin de sortie du rapport HTML (par défaut : rapport_soh.html)",
    )
    parser.add_argument(
        "--min-delta",
        type=float,
        default=40.0,
        help="Variation minimale de pourcentage de charge pour qualifier une session (par defaut : 40)",
    )
    parser.add_argument(
        "--mapping",
        "-m",
        nargs="*",
        help="Mapping personnalisé de colonnes au format clé=valeur (ex: date=Date energy_added='Energy added')",
    )

    args = parser.parse_args()

    if not args.csv_path.exists():
        print(f"Erreur : Le fichier '{args.csv_path}' n'existe pas.", file=sys.stderr)
        sys.exit(1)

    custom_mapping = parse_mapping(args.mapping)

    print(f"Chargement et détection des colonnes depuis '{args.csv_path}'...")
    analyzer = SOHAnalyzer(custom_mapping=custom_mapping, min_delta_soc=args.min_delta)

    try:
        clean_df = analyzer.load_data(args.csv_path)
        print(f"-> {len(clean_df)} sessions valides extraites.")

        print("Calcul de la dégradation et régression statistique...")
        result = analyzer.analyze(clean_df)

        print("\n" + "=" * 55)
        print("          RÉSULTATS DE L'EXPERTISE SOH          ")
        print("=" * 55)
        print(f"Période analysée     : {result.date_min.strftime('%d/%m/%Y')} -> {result.date_max.strftime('%d/%m/%Y')}")
        print(f"Sessions qualifiées  : {result.qualified_charges} (seuil: Δ% ≥ {args.min_delta}%)")
        if result.odometer_max > 0:
            print(f"Kilométrage total    : {result.odometer_max:,.0f} km")
        print(f"Capacité initiale C0 : {result.initial_capacity:.2f} kWh")
        print(f"Capacité actuelle    : {result.current_capacity:.2f} ± {result.current_capacity_err:.2f} kWh (IC 95%)")
        print(f"SOH Actuel           : {result.current_soh:.2f}% ± {result.current_soh_err:.2f}%")
        print(f"Perte de capacité    : {result.total_degradation_pct:.2f}% ({result.initial_capacity - result.current_capacity:.2f} kWh)")
        print("=" * 55 + "\n")

        print(f"Génération du rapport professionnel avec visualisations interactives...")
        analyzer.generate_html_report(result, args.output)
        print(f"-> Rapport prêt : {args.output.resolve()}\n")

    except Exception as e:
        print(f"Erreur lors de l'analyse : {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
