# 🔋 EV Battery SOH Analyzer & AI Agent

Un système complet et autonome d'analyse de télémétrie de recharge pour véhicules électriques. Il calcule avec précision la capacité utile résiduelle, le **State of Health (SOH)**, modélise la tendance avec régression locale pondérée et bande d'incertitude à 95%, et génère un **rapport d'expertise professionnel et interactif (HTML/PDF)**.

Conçu pour fonctionner :
* **En ligne de commande autonome** (CLI Python via `uv` ou `python3`).
* **Dans Google Antigravity** via le skill et l'agent intégrés.
* **Dans toute autre plateforme d'IA agentique** (Claude Code, Cursor, AutoGPT, OpenAI Assistants, etc.).

---

## 📁 Structure du Projet

```text
/home/pierre/Projets/SOH/
├── main.py                  # Point d'entrée CLI
├── analyzer.py              # Moteur statistique, régressions LOWESS, génération Plotly & Jinja2
├── pyproject.toml           # Configuration projet et dépendances Python (uv / pip)
├── rapport_soh.html         # Exemple de rapport généré
├── skills/
│   └── ev-battery-soh/
│       └── SKILL.md         # Définition universelle de la compétence (Agent Skill)
├── agents/
│   └── ev-battery-expert.md # Définition de l'Agent IA Expert Batterie
└── .venv/                   # Environnement virtuel isolé (numpy, scipy, pandas, plotly, jinja2)
```

---

## 🚀 Utilisation en Ligne de Commande (CLI)

### 1. Analyse automatique (TeslaMate, Tronity, ABRP, etc.)
L'outil détecte automatiquement les colonnes de date, énergie, SoC et odomètre :

```bash
cd /home/pierre/Projets/SOH
.venv/bin/python main.py /chemin/vers/fichier.csv -o mon_rapport_soh.html
```

### 2. Spécification d'un mapping personnalisé
Si le CSV possède des entêtes inhabituels :

```bash
.venv/bin/python main.py donnees.csv \
  --mapping date=Horodatage energy_added=Kwh_Charges soc_start=Niveau_Debut soc_end=Niveau_Fin odometer=Compteur_Km \
  -o rapport.html
```

### 3. Ajustement du seuil de qualification
Par défaut, seules les charges avec une variation de batterie $\ge 40\,\%$ sont retenues (pour éliminer l'erreur d'arrondi numérique du BMS) :

```bash
.venv/bin/python main.py donnees.csv --min-delta 30 -o rapport.html
```

---

## 📊 Contenu du Rapport Produit

Le rapport HTML généré propose un rendu moderne et officiel :
1. **Cartouche d'expertise & KPIs clés** :
   * State of Health (SOH) actuel avec intervalle de confiance à 95% ($\pm X\,\%$).
   * Capacité utile actuelle avec incertitude ($\pm X\text{ kWh}$).
   * Capacité initiale de référence $C_0$.
   * Taux de dégradation global.
2. **Courbe 1 : Évolution de la capacité utile dans le temps (kWh)** avec bande d'incertitude (régression locale gaussienne LOWESS).
3. **Courbe 2 : Évolution du State of Health (SOH %)** avec bande de confiance.
4. **Courbe 3 : Dégradation en fonction du kilométrage (odomètre)**.
5. **Tableau trimestriel certifié** : Médiane, écart-type et indice de fiabilité de 1 à 5 étoiles (★).
6. **Impression PDF native** : Rendu optimisé lors de l'impression (`Ctrl+P` ou export PDF du navigateur).

---

## 🤖 Intégration dans les plateformes d'IA Agentique

* **Antigravity** : La compétence est documentée dans [`skills/ev-battery-soh/SKILL.md`](skills/ev-battery-soh/SKILL.md). L'agent peut invoquer directement le script CLI.
* **Claude Code / Cursor / Assistants OpenAI** : Il suffit de pointer l'assistant vers `skills/ev-battery-soh/SKILL.md` ou d'inclure le fichier dans le contexte système pour lui donner l'autonomie d'exécuter l'analyse et d'interpréter les résultats.
