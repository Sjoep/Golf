"""
Golf Driving Range Dashboard
Vereisten: pip install streamlit pandas plotly
Gebruik:    streamlit run Golf.py

Nieuwe sessies uploaden doe je via de "New Upload"-pagina in de sidebar-navigatie.
"""

import glob
import os

import pandas as pd
try:
    import plotly.express as px
except Exception:  # pragma: no cover - inform user to install package
    px = None
    if 'st' in globals():
        st.error("Missing dependency: plotly. Install with `pip install plotly` and restart.")
        st.stop()
    else:
        raise
import plotly.graph_objects as go
import streamlit as st

from golf_utils import parse_bocht, sessie_label_from_name

# ── Pagina-instellingen ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="Golf Driving Range Dashboard",
    page_icon="⛳",
    layout="wide",
)

st.title("⛳ Golf Driving Range Dashboard")
st.caption("Sessiedata 2023 - 2026 · Inrange/simulator export")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


# ── Data laden ────────────────────────────────────────────────────────────────
@st.cache_data
def load_data(folder: str = SCRIPT_DIR) -> pd.DataFrame:
    files = glob.glob(os.path.join(folder, "*.csv"))
    frames = []

    for path in files:
        df = pd.read_csv(path)
        bestandsnaam = os.path.basename(path)
        df["Sessie"] = sessie_label_from_name(bestandsnaam)
        frames.append(df)

    if not frames:
        st.error("Geen CSV-bestanden gevonden.")
        st.stop()

    all_data = pd.concat(frames, ignore_index=True)

    if "Club" in all_data.columns:
        all_data["Club"] = all_data["Club"].replace("?", "Onbekend")

    all_data["Bocht_num"] = all_data["Bocht"].apply(parse_bocht)

    return all_data


df_all = load_data()

# ── Sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filters")

    sessies = ["Alle sessies"] + sorted(df_all["Sessie"].dropna().unique().tolist())
    sel_sessie = st.selectbox("Sessie", sessies)

    st.divider()
    st.caption("Tip: analyseer eerst alle sessies, en zoom daarna in op één sessie.")
    st.caption("Nieuwe sessie uploaden? Ga naar de 'New Upload'-pagina in het menu hierboven.")

# ── Data filteren ─────────────────────────────────────────────────────────────
df = df_all.copy()

if sel_sessie != "Alle sessies":
    df = df[df["Sessie"] == sel_sessie]

# ── Beveiliging bij lege selectie ─────────────────────────────────────────────
if df.empty:
    st.warning("Geen data beschikbaar voor deze selectie.")
    st.stop()

# ── Shot Quality Score ────────────────────────────────────────────────────────
# Copy voorkomt een pandas SettingWithCopyWarning na het filteren
df = df.copy()

max_afstand = df["Totale Afst. Premium (m)"].max()

if pd.notna(max_afstand) and max_afstand > 0:
    df["Afstand_score"] = (
        df["Totale Afst. Premium (m)"] / max_afstand * 100
    )
else:
    df["Afstand_score"] = 0

df["Richting_score"] = (
    100 - df["Bocht_num"].abs() * 15
).clip(lower=0, upper=100)

df["Shot_score"] = (
    0.6 * df["Afstand_score"]
    + 0.4 * df["Richting_score"]
).clip(lower=0, upper=100).round(1)

# ── KPI-berekeningen ──────────────────────────────────────────────────────────
avg_dist = df["Totale Afst. Premium (m)"].mean()
avg_speed = df["Balsnelheid (km/u) Premium"].mean()
best_slag = df["Totale Afst. Premium (m)"].max()

pct_recht = (df["Bocht_num"] == 0).mean() * 100 if len(df) else 0
consistentie = df["Totale Afst. Premium (m)"].std() if len(df) > 1 else 0

carry_ratio = (
    (df["Vlucht Afst. Premium (m)"] / df["Totale Afst. Premium (m)"])
    .replace([float("inf"), -float("inf")], pd.NA)
    .dropna()
    .mean() * 100
    if len(df)
    else 0
)

sessie_progress = (
    df_all.groupby("Sessie")["Totale Afst. Premium (m)"]
    .mean()
    .dropna()
)

if len(sessie_progress) >= 2:
    progressie = sessie_progress.iloc[-1] - sessie_progress.iloc[0]
else:
    progressie = 0

avg_shot_score = df["Shot_score"].mean()
best_shot_score = df["Shot_score"].max()

best_quality_idx = df["Shot_score"].idxmax()
best_quality_shot = df.loc[best_quality_idx]

# ── KPI-kaarten ───────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)

k1.metric("Totaal slagen", f"{len(df)}")
k2.metric("Gem. totale afstand", f"{avg_dist:.0f} m")
k3.metric("Gem. balsnelheid", f"{avg_speed:.0f} km/u")
k4.metric("Beste slag", f"{best_slag:.0f} m")

# ── KPI-rij 2 ─────────────────────────────────────────────────────────────────
k5, k6, k7, k8 = st.columns(4)

k5.metric("Rechte slagen", f"{pct_recht:.1f}%")
k6.metric("Consistentie", f"{consistentie:.1f} m")
k7.metric("Carry ratio", f"{carry_ratio:.1f}%")
k8.metric("Progressie", f"{progressie:+.1f} m")


# ── KPI-rij 3: Shot Quality ───────────────────────────────────────────────────
q1, q2, q3, q4 = st.columns(4)

q1.metric("Gem. shot score", f"{avg_shot_score:.1f}/100")
q2.metric("Beste shot score", f"{best_shot_score:.1f}/100")
q3.metric(
    "Afstand beste kwaliteitsslag",
    f"{best_quality_shot['Totale Afst. Premium (m)']:.0f} m",
)
q4.metric(
    "Beste kwaliteitsslag",
    f"Slag #{best_quality_shot['Slag #']}",
)
st.divider()

# ── Rij 1: Afstand per slag + Bochtverdeling ─────────────────────────────────
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Afstand per slag")

    fig_scatter = px.scatter(
        df,
        x="Slag #",
        y="Totale Afst. Premium (m)",
        hover_data={"Sessie": True, "Balsnelheid (km/u) Premium": True},
        labels={
            "Totale Afst. Premium (m)": "Afstand (m)",
            "Slag #": "Slag #",
        },
    )
    fig_scatter.update_traces(marker=dict(size=8))
    fig_scatter.update_layout(
        margin=dict(t=10, b=10),
        height=340,
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

with col_b:
    st.subheader("Bochtverdeling")

    bocht_counts = (
        df["Bocht_num"]
        .value_counts()
        .reindex(range(-5, 6), fill_value=0)
        .reset_index()
    )
    bocht_counts.columns = ["Bocht", "Aantal"]
    bocht_counts["Label"] = bocht_counts["Bocht"].apply(
        lambda b: "Recht" if b == 0 else (f"{abs(b)}L" if b < 0 else f"{b}R")
    )
    bocht_counts["Kleur"] = bocht_counts["Bocht"].apply(
        lambda b: "#1D9E75" if b == 0 else ("#BA7517" if abs(b) <= 2 else "#D85A30")
    )

    fig_bocht = go.Figure(
        go.Bar(
            x=bocht_counts["Label"],
            y=bocht_counts["Aantal"],
            marker_color=bocht_counts["Kleur"],
            hovertemplate="%{x}: %{y} slagen<extra></extra>",
        )
    )
    fig_bocht.update_layout(
        xaxis_title="Bocht",
        yaxis_title="Aantal slagen",
        margin=dict(t=10, b=10),
        height=340,
    )
    st.plotly_chart(fig_bocht, use_container_width=True)

# ── Rij 2: Shot pattern + Balsnelheid vs. afstand ────────────────────────────
col_c = st.columns(1)[0]
with col_c:
    st.subheader("Balsnelheid vs. afstand")

    fig_speed = px.scatter(
        df,
        x="Balsnelheid (km/u) Premium",
        y="Totale Afst. Premium (m)",
        hover_data={"Sessie": True, "Slag #": True},
        labels={
            "Balsnelheid (km/u) Premium": "Balsnelheid (km/u)",
            "Totale Afst. Premium (m)": "Afstand (m)",
        },
    )
    fig_speed.update_traces(marker=dict(size=7))
    fig_speed.update_layout(
        margin=dict(t=10, b=10),
        height=280,
    )
    st.plotly_chart(fig_speed, use_container_width=True)

# ── Rij 3: Progressie per sessie ──────────────────────────────────────────────
st.subheader("Progressie per sessie")

sessie_avg = (
    df_all.groupby("Sessie", observed=True)[
        ["Totale Afst. Premium (m)", "Balsnelheid (km/u) Premium"]
    ]
    .mean()
    .reset_index()
)

fig_prog = go.Figure()
fig_prog.add_trace(
    go.Scatter(
        x=sessie_avg["Sessie"],
        y=sessie_avg["Totale Afst. Premium (m)"].round(1),
        mode="lines+markers",
        name="Gem. afstand (m)",
        line=dict(color="#378ADD", width=2),
        marker=dict(size=8),
    )
)
fig_prog.add_trace(
    go.Scatter(
        x=sessie_avg["Sessie"],
        y=sessie_avg["Balsnelheid (km/u) Premium"].round(1),
        mode="lines+markers",
        name="Gem. balsnelheid (km/u)",
        line=dict(color="#1D9E75", width=2, dash="dot"),
        marker=dict(size=8),
        yaxis="y2",
    )
)
fig_prog.update_layout(
    yaxis=dict(title="Gem. afstand (m)"),
    yaxis2=dict(title="Gem. balsnelheid (km/u)", overlaying="y", side="right"),
    legend=dict(orientation="h", y=1.1),
    margin=dict(t=30, b=10),
    height=300,
)
st.plotly_chart(fig_prog, use_container_width=True)

# ── Rij 4: Histogram + Heatmap ────────────────────────────────────────────────
col_e, col_f = st.columns(2)

with col_e:
    st.subheader("Histogram totale afstand")

    fig_hist = px.histogram(
        df,
        x="Totale Afst. Premium (m)",
        nbins=20,
        labels={"Totale Afst. Premium (m)": "Totale afstand (m)"},
    )
    fig_hist.update_layout(
        xaxis_title="Totale afstand (m)",
        yaxis_title="Aantal slagen",
        margin=dict(t=10, b=10),
        height=320,
    )
    st.plotly_chart(fig_hist, use_container_width=True)

with col_f:
    st.subheader("Heatmap shot pattern")

    fig_heat = px.density_heatmap(
        df,
        x="Bocht_num",
        y="Totale Afst. Premium (m)",
        labels={
            "Bocht_num": "Links (-) / Rechts (+)",
            "Totale Afst. Premium (m)": "Totale afstand (m)",
        },
    )
    fig_heat.update_layout(
        xaxis_title="Links (-) / Rechts (+)",
        yaxis_title="Totale afstand (m)",
        margin=dict(t=10, b=10),
        height=320,
    )
    st.plotly_chart(fig_heat, use_container_width=True)

# ── Rij 5: Carry vs totale afstand ────────────────────────────────────────────
st.subheader("Vluchtafstand vs. totale afstand")

fig_carry_total = px.scatter(
    df,
    x="Vlucht Afst. Premium (m)",
    y="Totale Afst. Premium (m)",
    hover_data={"Sessie": True, "Slag #": True},
    labels={
        "Vlucht Afst. Premium (m)": "Vluchtafstand (m)",
        "Totale Afst. Premium (m)": "Totale afstand (m)",
    },
)
fig_carry_total.update_layout(margin=dict(t=10, b=10), height=320)
st.plotly_chart(fig_carry_total, use_container_width=True)

# ── Rij 6: Nauwkeurigheid bochtcategorieën ───────────────────────────────────
st.subheader("Nauwkeurigheid bochtcategorieën")

bocht_cat = df["Bocht_num"].apply(
    lambda b: "Recht"
    if b == 0 else ("Lichte afwijking" if abs(b) <= 2 else "Grote afwijking")
)

bocht_pct = (
    bocht_cat.value_counts(normalize=True)
    .mul(100)
    .reset_index()
)
bocht_pct.columns = ["Categorie", "Percentage"]

fig_bocht_pct = px.pie(
    bocht_pct,
    names="Categorie",
    values="Percentage",
    hole=0.4,
)
fig_bocht_pct.update_layout(margin=dict(t=10, b=10), height=320)
st.plotly_chart(fig_bocht_pct, use_container_width=True)


# ── Shot Quality analyse ──────────────────────────────────────────────────────
st.subheader("Shot Quality analyse")

quality_cols = [
    "Sessie",
    "Slag #",
    "Totale Afst. Premium (m)",
    "Balsnelheid (km/u) Premium",
    "Bocht_num",
    "Afstand_score",
    "Richting_score",
    "Shot_score",
]

quality_cols = [col for col in quality_cols if col in df.columns]

col_best, col_worst = st.columns(2)

with col_best:
    st.markdown("#### Beste 5 slagen")

    beste_slagen = (
        df.nlargest(5, "Shot_score")[quality_cols]
        .reset_index(drop=True)
    )

    st.dataframe(
        beste_slagen,
        use_container_width=True,
        hide_index=True,
    )

with col_worst:
    st.markdown("#### Slechtste 5 slagen")

    slechtste_slagen = (
        df.nsmallest(5, "Shot_score")[quality_cols]
        .reset_index(drop=True)
    )

    st.dataframe(
        slechtste_slagen,
        use_container_width=True,
        hide_index=True,
    )

# ── Ruwe data tabel ───────────────────────────────────────────────────────────
with st.expander("Bekijk ruwe data"):
    cols_show = [
        "Sessie",
        "Slag #",
        "Totale Afst. Premium (m)",
        "Vlucht Afst. Premium (m)",
        "Balsnelheid (km/u) Premium",
        "Apex (m) Premium",
        "Bocht_num",
        "Lanceerhoek (graden) Premium",
    ]

    bestaande_cols = [col for col in cols_show if col in df.columns]

    st.dataframe(
        df[bestaande_cols].rename(columns={"Bocht_num": "Bocht (num)"}),
        use_container_width=True,
        hide_index=True,
    )