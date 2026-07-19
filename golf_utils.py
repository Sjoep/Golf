"""
golf_utils.py
Gedeelde functies voor het Golf Driving Range Dashboard.
Wordt gebruikt door zowel Golf.py als Pages/New_Upload.py.

Plaats dit bestand in dezelfde map als Golf.py (naast de Pages-map).
"""

import pandas as pd

SESSION_MAP = {
    "13_aug_2023.csv": "13 aug 2023",
    "14_aug_2023.csv": "14 aug 2023",
    "15_aug_2023.csv": "15 aug 2023",
    "30_sept_2023.csv": "30 sept 2023",
    "4_sept_2023.csv": "4 sept 2023",
    "16_aug_2024.csv": "16 aug 2024",
    "5_okt_2024.csv": "5 okt 2024",
    "21_maart_2025.csv": "21 maart 2025",
    "29_maart_2025.csv": "29 maart 2025",
    "20_april_2025.csv": "20 april 2025",
    "21_april_2025.csv": "21 april 2025",
    "4_april_2026.csv": "4 april 2026",
}


def parse_bocht(val) -> int:
    """Converteert '3L' -> -3, '2R' -> 2, '0' -> 0."""
    if pd.isna(val):
        return 0
    val = str(val).strip().upper()
    if val in ("0", "-", ""):
        return 0
    if val.endswith("L"):
        return -int(val[:-1])
    if val.endswith("R"):
        return int(val[:-1])
    return 0


def sessie_label_from_name(bestandsnaam: str) -> str:
    """Geeft een mooie sessienaam terug als die in SESSION_MAP staat, anders de bestandsnaam zonder .csv."""
    return SESSION_MAP.get(bestandsnaam, bestandsnaam.replace(".csv", ""))


def clean_dataframe(df: pd.DataFrame, bestandsnaam: str) -> pd.DataFrame:
    """Voegt Sessie- en Bocht_num-kolommen toe en maakt Club-waarden schoon."""
    df = df.copy()
    df["Sessie"] = sessie_label_from_name(bestandsnaam)

    if "Club" in df.columns:
        df["Club"] = df["Club"].replace("?", "Onbekend")

    df["Bocht_num"] = df["Bocht"].apply(parse_bocht)
    return df


def add_shot_quality(df: pd.DataFrame) -> pd.DataFrame:
    """Berekent Afstand_score, Richting_score en Shot_score (0-100) per slag."""
    df = df.copy()

    max_afstand = df["Totale Afst. Premium (m)"].max()
    if pd.notna(max_afstand) and max_afstand > 0:
        df["Afstand_score"] = df["Totale Afst. Premium (m)"] / max_afstand * 100
    else:
        df["Afstand_score"] = 0

    df["Richting_score"] = (100 - df["Bocht_num"].abs() * 15).clip(lower=0, upper=100)

    df["Shot_score"] = (
        0.6 * df["Afstand_score"] + 0.4 * df["Richting_score"]
    ).clip(lower=0, upper=100).round(1)

    return df


def dispersion_per_club(df: pd.DataFrame) -> pd.DataFrame:
    """
    Berekent per club de spreiding (dispersion) in totale afstand:
    het verschil tussen de langste en kortste slag met die club.
    Geeft een lege DataFrame terug als er geen (bruikbare) Club-kolom is.
    """
    if "Club" not in df.columns:
        return pd.DataFrame()

    bruikbaar = df[df["Club"].notna() & (df["Club"] != "Onbekend")]
    if bruikbaar.empty:
        return pd.DataFrame()

    grouped = (
        bruikbaar.groupby("Club")["Totale Afst. Premium (m)"]
        .agg(Min="min", Max="max", Gemiddelde="mean", Aantal="count")
        .reset_index()
    )
    grouped["Dispersion (m)"] = (grouped["Max"] - grouped["Min"]).round(1)
    grouped["Gemiddelde"] = grouped["Gemiddelde"].round(1)

    return grouped.sort_values("Dispersion (m)", ascending=False).reset_index(drop=True)
