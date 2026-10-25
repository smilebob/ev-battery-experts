# 📖 Guide d'Installation Complet

Ce guide détaille l'installation de la suite **EV Battery SOH Analyzer** sur différents systèmes d'exploitation (**Linux, macOS, Windows**) et avec différents gestionnaires de paquets (**pip, uv, Docker/CLI**).

---

## 📋 Prérequis Généraux

* **Python** : Version **3.9** ou supérieure (Python 3.10, 3.11, 3.12, 3.13, 3.14 pris en charge).
* **Git** : Pour cloner le dépôt.

Vérifiez votre version de Python :
```bash
python3 --version  # ou 'python --version' sous Windows
```

---

## 🛠️ Méthode 1 : Installation avec `uv` (Recommandé - Rapide & Isolé)

[`uv`](https://github.com/astral-sh/uv) est un gestionnaire d'environnement Python ultra-rapide.

### Sur Linux / macOS :
```bash
# 1. Cloner le dépôt
git clone https://github.com/smilebob/ev-battery-experts.git
cd ev-battery-experts

# 2. Créer l'environnement virtuel
uv venv

# 3. Activer l'environnement
source .venv/bin/activate

# 4. Installer le package en mode éditable
uv pip install -e .
```

### Sur Windows (PowerShell) :
```powershell
# 1. Cloner le dépôt
git clone https://github.com/smilebob/ev-battery-experts.git
cd ev-battery-experts

# 2. Créer l'environnement virtuel
uv venv

# 3. Activer l'environnement
.venv\Scripts\Activate.ps1

# 4. Installer le package
uv pip install -e .
```

---

## 🐍 Méthode 2 : Installation standard avec `pip`

Si vous n'utilisez pas `uv`, vous pouvez utiliser le système standard `venv` et `pip`.

### Sur Linux / macOS :
```bash
git clone https://github.com/smilebob/ev-battery-experts.git
cd ev-battery-experts
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```

### Sur Windows (Invite de commandes ou PowerShell) :
```cmd
git clone https://github.com/smilebob/ev-battery-experts.git
cd ev-battery-experts
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -e .
```

---

## 🧪 Vérification de l'Installation

Une fois l'environnement activé, testez la commande :
```bash
ev-battery-soh --help
```
Le menu d'aide doit s'afficher sans erreur :
```text
usage: main.py [-h] [--output OUTPUT] [--min-delta MIN_DELTA]
               [--mapping [MAPPING ...]]
               csv_path

Analyse de State of Health (SOH) et dégradation de batterie pour véhicule électrique
...
```

---

## 🤖 Installation pour Google Antigravity

Pour que l'agent et la compétence soient détectés globalement dans votre environnement Antigravity :

```bash
# Lier la skill globalement
mkdir -p ~/.gemini/config/skills
ln -sfn "$(pwd)/skills/ev-battery-soh" ~/.gemini/config/skills/ev-battery-soh

# Lier l'agent globalement
mkdir -p ~/.gemini/config/agents
ln -sfn "$(pwd)/agents/ev-battery-expert.md" ~/.gemini/config/agents/ev-battery-expert.md
```
