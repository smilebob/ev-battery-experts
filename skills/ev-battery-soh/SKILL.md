---
name: ev-battery-soh
description: Analyse télémétrique avancée de State of Health (SOH) et dégradation de capacité de batterie pour véhicule électrique (Tesla, Tronity, ABRP ou tout export CSV de recharge). Calcule la capacité utile résiduelle, la régression statistique locale avec bande d'incertitude à 95%, la synthèse trimestrielle avec indice de fiabilité et génère un rapport HTML interactif et imprimable haut de gamme.
---

# EV Battery SOH Analysis Skill

Cette compétence permet à tout agent IA (Antigravity, Claude Code, Cursor, AutoGPT, OpenAI Swarm/Assistants) d'analyser l'historique de recharge d'un véhicule électrique et d'éditer un rapport d'expertise officiel de dégradation de batterie.

## Emplacement de l'outil
Le moteur d'analyse se trouve dans `/home/pierre/Projets/SOH` :
* Script principal : `main.py`
* Moteur statistique : `analyzer.py`
* Environnement Python : `/home/pierre/Projets/SOH/.venv/bin/python`

---

## Fonctionnalités Principales

1. **Détection automatique et tolérante des colonnes** :
   Gère automatiquement les exports issus de :
   * **TeslaMate** (`Date`, `Energy added`, `% Start`, `% End`, `Odometer`, `Location`, `Type`)
   * **Tronity** (`timestamp`, `charged_kwh`, `start_soc`, `end_soc`, `mileage`)
   * **ABRP / OpenEVSE / Home Assistant / Formats personnalisés**.
   * Possibilité de fournir un mapping manuel via `--mapping`.

2. **Modélisation Statistique & Marge d'Erreur (IC 95%)** :
   * **Filtrage de bruit** : Ne retient que les charges profondes ($\Delta\% \ge 40\,\%$) pour éliminer le bruit d'arrondi des entiers de pourcentage de batterie.
   * **Régression locale gaussienne pondérée (LOWESS)** : Ajuste la courbe de tendance sur la capacité réelle sans supposer a priori une fonction rigide.
   * **Bandes de confiance à 95%** : Calculées à partir de la variance résiduelle locale ($\pm 1{,}96 \times \sigma_{\text{local}}$).

3. **Rapport d'Expertise Professionnel & Moderne (HTML/PDF)** :
   * Dashboard interactif Plotly (zoom, survol, infobulles précises).
   * Courbe 1 : Évolution de la capacité utile dans le temps (kWh) avec bande d'incertitude.
   * Courbe 2 : Évolution du State of Health (SOH %) avec bande d'incertitude.
   * Courbe 3 : Dégradation en fonction du kilométrage (odomètre).
   * Tableau de bord trimestriel : Médiane, écart-type et indice de fiabilité de 1 à 5 étoiles (★).
   * Mise en page print-friendly (compatible impression PDF direct ou `weasyprint`).

---

## Instructions d'Exécution pour l'Agent

Pour exécuter une analyse sur un fichier CSV fourni par l'utilisateur :

```bash
cd /home/pierre/Projets/SOH
.venv/bin/python main.py "/chemin/vers/fichier.csv" -o "/chemin/vers/rapport_soh.html"
```

### Options CLI disponibles :
* `-o`, `--output` : Chemin du fichier HTML de sortie (par défaut : `rapport_soh.html`).
* `--min-delta` : Seuil minimal de variation de batterie $\Delta\%$ pour qualifier une session (défaut : `40.0`).
* `-m`, `--mapping` : Spécification manuelle des colonnes si les noms sont exotiques :
  ```bash
  .venv/bin/python main.py data.csv -m date=horodatage energy_added=kwh_recus soc_start=batterie_debut soc_end=batterie_fin odometer=compteur
  ```

---

## Interprétation des Résultats pour l'Utilisateur
Quand l'agent présente les résultats, il doit structurer sa réponse en 4 points :
1. **Capacité initiale vs Capacité actuelle** : en kWh avec la marge d'erreur à 95%.
2. **SOH actuel (%)** : avec son intervalle de confiance.
3. **Qualité du vieillissement** : comparer la perte de capacité avec les moyennes de la chimie de batterie (LFP vs NMC/NCA, typiquement 3 à 5% à 50 000 km pour LFP).
4. **Lien vers le rapport généré** : chemin absolu vers le rapport HTML navigable.
