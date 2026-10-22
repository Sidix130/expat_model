# Calculateur d'autonomie financière à dépenses fixes

Petit modèle autonome en Python, sans dépendance externe. Il calcule une autonomie théorique avec un capital initial, une réserve protégée, des dépenses initiales et un budget mensuel fixe. Il n'intègre volontairement aucun revenu ni la gestion d'autres décisions.

## Prérequis

Python 3.10 ou supérieur. Aucune bibliothèque tierce.

## Lancer

```bash
python3 capital_runway.py scenario_exemple.json
```

Afficher une trajectoire de 120 mois :

```bash
python3 capital_runway.py scenario_exemple.json --months 120
```

Exporter la trajectoire affichée en CSV :

```bash
python3 capital_runway.py scenario_exemple.json --months 120 --csv trajectoire.csv
```

## Modifier un scénario

Copier `scenario_exemple.json`, puis modifier les valeurs :

- `starting_capital_eur` : capital disponible au départ.
- `protected_reserve_eur` : réserve à ne pas consommer dans l'autonomie calculée.
- `one_off_costs_eur` : achats et frais payés avant le début de la trajectoire.
- `monthly_expenses_eur` : dépenses fixes mensuelles, détaillées par catégorie.

Le budget mensuel est la somme des valeurs de `monthly_expenses_eur`.

Formules :

```text
capital_apres_frais_initiaux = capital_initial - depenses_initiales
capital_mobilisable = max(0, capital_apres_frais_initiaux - reserve)
budget_mensuel = somme(depenses_mensuelles)
autonomie_mois = capital_mobilisable / budget_mensuel
```

L'autonomie est théorique : dépenses fixes, aucun revenu, aucun rendement, aucune inflation. Les coûts inconnus ne sont pas automatiquement estimés à zéro ; ils doivent être renseignés explicitement dans le scénario.
