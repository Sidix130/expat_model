#!/usr/bin/env python3
"""Small, standalone capital-runway calculator.

Model boundary: fixed monthly expenses, no income, no interest, no inflation.
It does not choose an option or manage the user's wider planning process.

Usage:
  python capital_runway.py scenario.json
  python capital_runway.py scenario.json --months 24
  python capital_runway.py scenario.json --csv trajectory.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Scenario:
    name: str
    starting_capital_eur: float
    protected_reserve_eur: float
    one_off_costs_eur: float
    monthly_expenses_eur: dict[str, float]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Scenario":
        expenses = data.get("monthly_expenses_eur", {})
        if not isinstance(expenses, dict):
            raise ValueError("'monthly_expenses_eur' must be an object of category: amount pairs")
        parsed_expenses: dict[str, float] = {}
        for category, amount in expenses.items():
            parsed = _nonnegative_number(amount, f"monthly_expenses_eur.{category}")
            parsed_expenses[str(category)] = parsed
        return cls(
            name=str(data.get("name", "Unnamed scenario")),
            starting_capital_eur=_nonnegative_number(data.get("starting_capital_eur"), "starting_capital_eur"),
            protected_reserve_eur=_nonnegative_number(data.get("protected_reserve_eur", 0), "protected_reserve_eur"),
            one_off_costs_eur=_nonnegative_number(data.get("one_off_costs_eur", 0), "one_off_costs_eur"),
            monthly_expenses_eur=parsed_expenses,
        )

    @property
    def monthly_total_eur(self) -> float:
        return sum(self.monthly_expenses_eur.values())

    @property
    def capital_after_one_off_costs_eur(self) -> float:
        return self.starting_capital_eur - self.one_off_costs_eur

    @property
    def spendable_capital_eur(self) -> float:
        return max(0.0, self.capital_after_one_off_costs_eur - self.protected_reserve_eur)

    @property
    def reserve_shortfall_eur(self) -> float:
        return max(0.0, self.one_off_costs_eur + self.protected_reserve_eur - self.starting_capital_eur)

    def trajectory(self, max_months: int | None = None) -> list[dict[str, float | int | bool]]:
        """Return month 0 and each month until reserve is reached or max_months.

        Month 0 is after one-off costs. The protected reserve is not spent in this
        trajectory; it is the threshold at which the model stops.
        """
        balance = self.capital_after_one_off_costs_eur
        rows: list[dict[str, float | int | bool]] = [{
            "month": 0,
            "capital_eur": round(balance, 2),
            "above_reserve_eur": round(balance - self.protected_reserve_eur, 2),
            "reserve_reached": balance <= self.protected_reserve_eur,
        }]
        if self.monthly_total_eur <= 0:
            return rows
        month = 0
        while balance > self.protected_reserve_eur and (max_months is None or month < max_months):
            month += 1
            balance -= self.monthly_total_eur
            rows.append({
                "month": month,
                "capital_eur": round(balance, 2),
                "above_reserve_eur": round(balance - self.protected_reserve_eur, 2),
                "reserve_reached": balance <= self.protected_reserve_eur,
            })
        return rows

    def months_until_reserve(self) -> float | None:
        if self.monthly_total_eur <= 0:
            return None
        return self.spendable_capital_eur / self.monthly_total_eur


def _nonnegative_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"'{field}' must be a number")
    if value < 0:
        raise ValueError(f"'{field}' must be >= 0")
    return float(value)


def load_scenario(path: Path) -> Scenario:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"Cannot read scenario file: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ValueError("Scenario JSON root must be an object")
    return Scenario.from_dict(data)


def euros(value: float) -> str:
    return f"{value:,.2f} €".replace(",", "\u202f").replace(".", ",")


def print_report(s: Scenario, max_months: int | None) -> list[dict[str, float | int | bool]]:
    print(f"SCÉNARIO : {s.name}")
    print("=" * (10 + len(s.name)))
    print(f"Capital initial                 : {euros(s.starting_capital_eur)}")
    print(f"Dépenses initiales              : {euros(s.one_off_costs_eur)}")
    print(f"Capital après dépenses initiales: {euros(s.capital_after_one_off_costs_eur)}")
    print(f"Réserve protégée                : {euros(s.protected_reserve_eur)}")
    print("\nDÉPENSES MENSUELLES FIXES")
    if s.monthly_expenses_eur:
        for category, amount in s.monthly_expenses_eur.items():
            print(f"  {category:<31} {euros(amount):>14}")
    else:
        print("  (aucune dépense renseignée)")
    print(f"  {'TOTAL':<31} {euros(s.monthly_total_eur):>14}")
    print("\nRÉSULTAT")
    print(f"Capital mobilisable avant réserve: {euros(s.spendable_capital_eur)}")
    if s.reserve_shortfall_eur > 0:
        print(f"ATTENTION : le capital est inférieur de {euros(s.reserve_shortfall_eur)} au coût initial + réserve.")
    if s.monthly_total_eur == 0:
        print("Autonomie : non calculable (dépenses mensuelles nulles).")
    else:
        months = s.months_until_reserve()
        assert months is not None
        print(f"Autonomie théorique avant réserve: {months:.2f} mois ({months / 12:.2f} ans)")
        print(f"Mois complets financés avant passage sous la réserve: {int(months)}")
    print("\nTRAJECTOIRE (solde après dépenses initiales, puis chaque fin de mois)")
    rows = s.trajectory(max_months=max_months)
    print(f"{'Mois':>5}  {'Capital restant':>18}  {'Au-dessus réserve':>19}  {'Réserve atteinte':>17}")
    for row in rows:
        print(f"{row['month']:>5}  {euros(float(row['capital_eur'])):>18}  {euros(float(row['above_reserve_eur'])):>19}  {('oui' if row['reserve_reached'] else 'non'):>17}")
    if max_months is not None and rows and rows[-1]["month"] == max_months and not rows[-1]["reserve_reached"]:
        print(f"(Affichage arrêté à {max_months} mois ; le calcul d'autonomie reste celui indiqué plus haut.)")
    print("\nLIMITES DU MODÈLE")
    print("- Aucun revenu, rendement, inflation ou variation des prix.")
    print("- Les dépenses mensuelles sont fixes et supposées complètes.")
    print("- Les dépenses initiales sont payées avant le mois 0.")
    print("- La réserve est un seuil protégé, pas une somme consommée dans le calcul d'autonomie.")
    print("- Les dépenses imprévues doivent être ajoutées aux coûts initiaux ou au budget mensuel.")
    return rows


def write_csv(path: Path, rows: list[dict[str, float | int | bool]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["month", "capital_eur", "above_reserve_eur", "reserve_reached"])
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Calculateur transparent d'autonomie financière à dépenses fixes.")
    parser.add_argument("scenario", type=Path, help="Chemin vers un fichier de scénario JSON")
    parser.add_argument("--months", type=int, default=24, help="Nombre maximal de mois à afficher dans la trajectoire (défaut : 24)")
    parser.add_argument("--csv", type=Path, help="Exporter la trajectoire affichée au format CSV")
    args = parser.parse_args(argv)
    if args.months < 0:
        parser.error("--months doit être >= 0")
    try:
        scenario = load_scenario(args.scenario)
        rows = print_report(scenario, args.months)
        if args.csv:
            write_csv(args.csv, rows)
            print(f"\nCSV écrit : {args.csv}")
    except (ValueError, OSError) as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
