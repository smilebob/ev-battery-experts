# 📘 Manuel d'Utilisation & Guide Pratique

Ce manuel explique comment utiliser **EV Battery SOH Analyzer**, interpréter les rapports générés et adapter le traitement à différents formats de données.

---

## 🚀 1. Utilisation de Base (Ligne de Commande)

La commande principale est `ev-battery-soh` (ou `python3 main.py`).

### Syntaxe générale :
```bash
ev-battery-soh <chemin_du_fichier.csv> [options]
```

### Exemple simple :
```bash
ev-battery-soh charges_2026.csv -o rapport_expertise.html
```
Cette commande :
1. Lit le fichier `charges_2026.csv`.
2. Détecte automatiquement les colonnes de recharges.
3. Filtre les sessions pour éliminer le bruit.
4. Calcule les régressions et bandes de confiance à 95%.
5. Écrit le rapport interactif dans `rapport_expertise.html`.

---

## 🗂️ 2. Formats de Fichiers CSV Reconnus

L'analyseur intègre un moteur de détection basé sur des synonymes.

### Formats nativement pris en charge :
* **TeslaMate** : Colonnes `Date`, `Energy added`, `% Start`, `% End`, `Odometer`, `Location`, `Type`.
* **Tronity** : Colonnes `timestamp`, `charged_kwh`, `start_soc`, `end_soc`, `mileage`.
* **ABRP (A Better Routeplanner)** : Logs de session de recharge.
* **OpenEVSE / Home Assistant / Wallbox** : Exports de sessions avec énergie injectée et SoC.

### Colonnes minimales requises :
| Donnée | Exemples de noms reconnus |
| :--- | :--- |
| **Date & Heure** | `Date`, `datetime`, `timestamp`, `start_date`, `time` |
| **Énergie injectée** | `Energy added`, `kwh_added`, `charge_kwh`, `energie_ajoutee` |
| **SoC Début** | `% Start`, `soc_start`, `battery_start`, `start_soc` |
| **SoC Fin** | `% End`, `soc_end`, `battery_end`, `end_soc` |
| **Kilométrage** *(Optionnel)* | `Odometer`, `mileage`, `km`, `compteur` |

---

## 🛠️ 3. Options Avancées

### A. Spécification manuelle des colonnes (`--mapping` ou `-m`)
Si votre fichier provient d'une application exotique avec des noms de colonnes inhabituels :
```bash
ev-battery-soh export_brut.csv \
  -m date="Horodatage_Session" \
     energy_added="Net_Kwh_Batterie" \
     soc_start="Niveau_Initial_Pct" \
     soc_end="Niveau_Final_Pct" \
     odometer="Index_Kilometres" \
  -o rapport.html
```

### B. Ajuster le seuil de qualification de recharge (`--min-delta`)
Par défaut, seules les charges avec une amplitude $\Delta\% \ge 40\,\%$ sont prises en compte (pour éliminer l'erreur d'arrondi numérique du BMS sur les petites recharges).
* Si vous avez peu de longues charges et souhaitez inclure les charges moyennes :
  ```bash
  ev-battery-soh charges.csv --min-delta 30 -o rapport.html
  ```
* Si vous ne voulez conserver que les charges quasi-complètes :
  ```bash
  ev-battery-soh charges.csv --min-delta 60 -o rapport.html
  ```

---

## 📊 4. Comprendre le Rapport Généré

Le rapport HTML contient 4 sections majeures :

### 1. Cartouche officiel & KPIs
* **SOH Actuel & Marge d'erreur** : Ex. `96.33% ± 1.25% (IC 95%)`. Signifie qu'il y a 95% de certitude statistique que la capacité réelle se trouve dans cet intervalle.
* **Capacité Utile Actuelle** : Quantité maximale de kWh que la batterie peut stocker aujourd'hui.
* **Capacité Initiale ($C_0$)** : Référence médiane calculée sur le premier décile de charges (véhicule neuf).

### 2. Courbe 1 : Capacité utile (kWh) vs Temps
* **Points gris** : Sessions de recharges réelles observées.
* **Ligne bleue continue** : Tendance centrale (régression locale gaussienne LOWESS).
* **Bande bleue transparente** : Intervalle d'incertitude locale à 95%.

### 3. Courbe 2 : State of Health (%) vs Temps
* Même représentation normalisée en pourcentage par rapport au neuf.

### 4. Courbe 3 : Dégradation vs Kilométrage
* Évolution en fonction des kilomètres parcourus sur l'odomètre.

### 5. Synthèse Trimestrielle & Indice de Fiabilité (★)
* Chaque trimestre bénéficie d'une note de 1 à 5 étoiles :
  * ★★★★★ : Échantillon important, nombreuses charges à 100%, dispersion très faible.
  * ★★★☆☆ : Échantillon réduit ou période avec plus forte dispersion thermique (hiver).

---

## 🖨️ 5. Export en PDF Officiel

Le rapport HTML est optimisé pour les feuilles de style d'impression (`@media print`) :
1. Ouvrez `rapport_soh.html` dans Chrome, Firefox ou Safari.
2. Appuyez sur `Ctrl + P` (ou `Cmd + P` sur Mac).
3. Choisissez **"Enregistrer au format PDF"**.
4. Cochez **"Graphismes d'arrière-plan"** pour préserver les couleurs et styles.
5. Vous obtenez un rapport PDF multipage propre et imprimable.
