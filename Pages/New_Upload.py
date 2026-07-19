"""
Pages/New_Upload.py

Upload-pagina voor nieuwe driving range sessies.
Upload een CSV en bekijk direct dezelfde volledige analyse als in het hoofddashboard
(Golf.py), vóórdat je de sessie definitief opslaat.
"""

import os
import sys

import pandas as pd
import streamlit as st

# Golf/ map = één niveau boven Pages/ — expliciet toevoegen aan sys.path zodat
# golf_utils vindbaar is, zowel bij `streamlit run` als bij statische analyse (Pylance).
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from golf_utils import add_shot_quality, clean_dataframe, sessie_label_from_name

st.set_page_config(page_title="Nieuwe sessie uploaden", page_icon="📤", layout="wide")

st.title("📤 Nieuwe sessie uploaden")
st.caption("Upload een CSV-export uit Inrange en bekijk direct dezelfde analyse als in het hoofddashboard.")

uploaded_file = st.file_uploader("Kies een CSV-bestand", type="csv")

if uploaded_file is None:
    st.info("Upload een CSV-bestand om te beginnen.")
    st.stop()

# ── Inlezen en valideren ──────────────────────────────────────────────────────
try:
    df_raw = pd.read_csv(uploaded_file)
except Exception as e:
    st.error(f"Kon het bestand niet lezen: {e}")
    st.stop()

required_cols = {"Bocht", "Slag #", "Totale Afst. Premium (m)", "Balsnelheid (km/u) Premium"}
missing = required_cols - set(df_raw.columns)
if missing:
    st.error(f"Verplichte kolommen ontbreken in dit CSV-bestand: {', '.join(missing)}")
    st.stop()

df = clean_dataframe(df_raw, uploaded_file.name)
df = add_shot_quality(df)

st.success(f"{len(df)} slagen ingelezen uit **{uploaded_file.name}**.")

# ── Sessienaam aanpasbaar maken ───────────────────────────────────────────────
default_label = sessie_label_from_name(uploaded_file.name)
sessie_naam = st.text_input("Sessienaam (zoals die in het dashboard komt te staan)", value=default_label)
df["Sessie"] = sessie_naam

st.divider()

# ── KPI-berekeningen (alleen de kerncijfers) ─────────────────────────────────
avg_dist = df["Totale Afst. Premium (m)"].mean()
best_slag = df["Totale Afst. Premium (m)"].max()
avg_shot_score = df["Shot_score"].mean()

# ── KPI-kaarten: 4 kerncijfers ────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("Totaal slagen", f"{len(df)}")
k2.metric("Gem. totale afstand", f"{avg_dist:.0f} m")
k3.metric("Beste slag", f"{best_slag:.0f} m")
k4.metric("Gem. shot score", f"{avg_shot_score:.1f}/100")

st.divider()

# ── Centrale tabel: alle slagen, sorteerbaar, met kleur op Shot Score ────────
st.subheader("Alle slagen")
st.caption("Klik op een kolomkop om te sorteren. Groen = hoge Shot Score, rood = lage Shot Score.")

table_cols = [
    c for c in
    [
        "Slag #", "Totale Afst. Premium (m)", "Vlucht Afst. Premium (m)",
        "Balsnelheid (km/u) Premium", "Bocht_num", "Shot_score",
    ]
    if c in df.columns
]

tabel_df = df[table_cols].rename(columns={"Bocht_num": "Bocht (num)"}).reset_index(drop=True)

styled = tabel_df.style.background_gradient(
    subset=["Shot_score"], cmap="RdYlGn", vmin=0, vmax=100
).format(precision=1)

st.dataframe(styled, use_container_width=True, hide_index=True)

with st.expander("Ruwe data (alle originele kolommen)"):
    st.dataframe(df, use_container_width=True, hide_index=True)

st.divider()

# ── Opslaan zodat sessie in het hoofddashboard verschijnt ────────────────────
st.subheader("Sessie opslaan")
st.caption(
    "Slaat het originele CSV-bestand op in de Golf-map, zodat Golf.py het "
    "automatisch meepakt bij het laden van alle sessies."
)

save_name = st.text_input("Bestandsnaam voor opslag", value=uploaded_file.name)

if st.button("💾 Opslaan in dashboard", type="primary"):
    save_path = os.path.join(SCRIPT_DIR, save_name)
    if os.path.exists(save_path):
        st.warning(
            f"Bestand **{save_name}** bestaat al in de Golf-map. "
            "Kies een andere naam als je niet wilt overschrijven."
        )
    else:
        df_raw.to_csv(save_path, index=False)
        st.cache_data.clear()
        st.success(
            f"Opgeslagen als `{save_name}`. Ga naar het hoofddashboard "
            "(of herlaad de pagina) om de nieuwe sessie te zien."
        )
        