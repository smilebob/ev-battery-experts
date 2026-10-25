# 🔬 Méthodologie Scientifique & Modélisation Mathématique

Ce document détaille les fondements physiques et statistiques utilisés par **EV Battery SOH Analyzer** pour estimer la dégradation de capacité et le State of Health (SOH).

---

## 1. Principe Physique de la Mesure Télémétrique

Contrairement aux tests de décharge complets en laboratoire sous banc d'essai (très coûteux et immobilisants), la méthode par télémétrie de recharge exploite les données en conditions réelles de roulage.

### Distinction cruciale : Énergie stockée vs Énergie consommée
* **`Energy used` (Énergie au compteur)** : Inclut le rendement du chargeur AC/DC (typiquement 85-95%), l'effet Joule dans le câble, et la climatisation/chauffage de la batterie pendant la charge. **Elle ne doit pas être utilisée pour calculer la capacité.**
* **`Energy added` (Énergie dans le pack)** : Représente la quantité nette de coulombs/énergie effectivement acceptée par la chimie de la batterie.

Pour chaque recharge $i$ :
$$\Delta\%_i = \%_{\text{End}, i} - \%_{\text{Start}, i}$$
$$C_i = \frac{E_{\text{added}, i}}{\Delta\%_i} \times 100$$

Où $C_i$ est la capacité totale apparente du pack lors de la session $i$ (en kWh).

---

## 2. Traitement du Bruit Numérique & Échantillonnage

Dans les exports grand public (ex. TeslaMate, Tronity), les états de charge (`% Start`, `% End`) sont des **entiers arrondis** ($80\,\%$, $81\,\%$, etc.).

### Analyse d'erreur d'arrondi :
Soit une session mesurée de $50\,\%$ à $55\,\%$ ($\Delta\% = 5\,\%$).
* Les vraies valeurs peuvent être $50{,}4\,\%$ et $54{,}6\,\%$, soit $\Delta\%_{\text{réel}} = 4{,}2\,\%$.
* L'erreur relative est alors de :
  $$\text{Erreur} = \frac{5 - 4{,}2}{4{,}2} \approx 19\,\%$$
* En revanche, pour une session où $\Delta\% \ge 40\,\%$, l'erreur maximale d'arrondi sur les bornes est au maximum de :
  $$\frac{\pm 0{,}5 + \pm 0{,}5}{40} = \frac{\pm 1}{40} = \pm 2{,}5\,\%$$
  *(et inférieure à $\pm 1\,\%$ sur des charges de 80%)*.

**Règle appliquée :** Seules les sessions avec $\Delta\% \ge 40\,\%$ sont admises dans la modélisation statistique.

---

## 3. Régression Locale Pondérée (LOWESS) & Marge d'Erreur

La dégradation d'une batterie ne suit pas une droite simple. Elle présente souvent :
1. Une chute plus rapide dans les premiers 10 000 à 20 000 km (formation de la couche SEI).
2. Un plateau ou des ondulations liées au recalibrage périodique du BMS.
3. Une décroissance très lente par la suite.

Pour capturer cette dynamique sans biais de modèle, nous utilisons une **régression polynomiale locale à noyau gaussien** :

Pour chaque point d'évaluation $t_0$, nous minimisons la somme pondérée des carrés :
$$\min_{\beta_0, \beta_1} \sum_{i=1}^n w_i(t_0) \left( C_i - (\beta_0 + \beta_1 (t_i - t_0)) \right)^2$$

Avec le poids gaussien :
$$w_i(t_0) = \exp\left( -\frac{1}{2}\left(\frac{t_i - t_0}{h}\right)^2 \right)$$
Où $h$ est la largeur de bande temporelle adaptative (bandwidth).

### Intervalle de Confiance à 95% (Marge d'erreur) :
Pour chaque point estimé $\hat{C}(t_0) = \hat{\beta}_0$, la variance locale pondérée des résidus est calculée :
$$s^2(t_0) = \frac{\sum w_i (C_i - \hat{C}_i)^2}{\sum w_i \left(1 - \frac{1}{\text{eff\_n}}\right)}$$
$$\text{Marge d'erreur (IC 95\%)} = \pm 1{,}96 \times s(t_0)$$

Cette bande d'incertitude reflète les variations saisonnières de température, la dispersion des mesures et l'incertitude statistique intrinsèque.

---

## 4. Calcul du State of Health (SOH)

La capacité initiale de référence $C_0$ est déterminée par la médiane des sessions de recharge initiales (véhicule neuf, premiers 10% des données ou 5 000 premiers km).

$$\text{SOH}(t) = \frac{\hat{C}(t)}{C_0} \times 100$$
$$\text{Incertitude SOH}(t) = \frac{1{,}96 \times s(t)}{C_0} \times 100$$
