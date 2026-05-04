"""
app.py — Aplicación Streamlit de monitoreo topográfico (fuente: CSV)
"""
import os
import sys
import pandas as pd
import streamlit as st
import plotly.express as px
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import ALERT_COLORS, PROJECT_SISTEMA
from src.enrich import enrich

# ── Rutas fijas a los CSV ────────────────────────────────────────────────────
CSV_OPTIONS = {
    "Control Tanque": os.path.join(os.path.dirname(__file__), "data", "control_tanque_dataframe.csv"),
    "Cunetas":        os.path.join(os.path.dirname(__file__), "data", "cunetas_dataframe.csv"),
}

st.set_page_config(page_title="Monitoreo Topográfico", page_icon="📡", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stApp { background-color: #F8F9FA; }
    [data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 1px solid #E8ECF0; }
    .kpi-card { background: white; border-radius: 12px; padding: 1rem 1.2rem; border: 1px solid #E8ECF0; margin-bottom: 0.5rem; height: 100%; }
    .kpi-label  { font-size: 0.85rem; color: #1A202C; margin-bottom: 0.2rem; }
    .kpi-value  { font-size: 1.6rem;  font-weight: 700; color: #1A202C; line-height: 1.2;}
    .kpi-delta  { font-size: 0.85rem; color: #718096; margin-top: 0.15rem; }
    .kpi-alert  { font-size: 0.9rem;  font-weight: 600; margin-top: 0.6rem; }
    div[data-testid="stPlotlyChart"] { background: white; border-radius: 10px; border: 1px solid #E8ECF0; padding: 4px; }
    .section-header { font-size: 1rem; font-weight: 600; color: #1A202C; margin: 1.5rem 0 0.5rem 0; padding-bottom: 0.4rem; border-bottom: 2px solid #E8ECF0; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(show_spinner="⚙️ Procesando datos…")
def run_pipeline(csv_path: str) -> pd.DataFrame:
    df_raw = pd.read_csv(csv_path)
    return enrich(df_raw)

with st.sidebar:
    st.markdown("## 📡 Monitoreo Topográfico")
    st.divider()

    dataset_name = st.selectbox("📁 Seleccionar dataset", options=list(CSV_OPTIONS.keys()))
    csv_path = CSV_OPTIONS[dataset_name]

    if not os.path.exists(csv_path):
        st.error(f"Archivo no encontrado: {csv_path}")
        st.stop()

    df_full = run_pipeline(csv_path)
    n_campaigns = df_full[df_full["Monitoring_Number"] > 0]["Monitoring_Number"].nunique()
    st.success(f"✅ {n_campaigns} campañas · {df_full['Number'].nunique()} puntos")
    st.divider()

    st.markdown("**📌 Puntos de medición**")
    puntos_en_csv = df_full["Number"].dropna().unique().tolist()
    selected_points = st.multiselect("Seleccionar puntos", options=puntos_en_csv, default=puntos_en_csv, label_visibility="collapsed")
    st.divider()

    st.markdown("**📅 Rango temporal**")
    campaign_dates = sorted(df_full[df_full["Monitoring_Number"] > 0]["Date"].dt.date.unique())
    if not campaign_dates:
        st.warning("No hay suficientes fechas válidas.")
        st.stop()

    date_labels = [d.strftime("%d/%m/%Y") for d in campaign_dates]
    start_label, end_label = st.select_slider("Rango", options=date_labels, value=(date_labels[0], date_labels[-1]), label_visibility="collapsed")

    start_date = dict(zip(date_labels, campaign_dates))[start_label]
    end_date   = dict(zip(date_labels, campaign_dates))[end_label]

    df_filtrado_rango = df_full[
        (df_full["Monitoring_Number"] > 0) &
        (df_full["Date"].dt.date >= start_date) &
        (df_full["Date"].dt.date <= end_date)
    ]
    n_range = df_filtrado_rango["Monitoring_Number"].nunique()
    st.markdown(f"<p style='font-size:0.8rem;color:#718096'>📊 {n_range} campañas<br>De {start_label} a {end_label}</p>", unsafe_allow_html=True)

    st.divider()
    st.markdown("**🪣 Nivel del tanque**")
    nivel_default = 0 if dataset_name == "Control Tanque" else 2
    nivel_sel = st.radio(
        "Nivel",
        options=[0, 1, 2],
        format_func=lambda x: {0: "🔵 Low", 1: "🟠 Full", 2: "⚪ Ambas"}[x],
        index=nivel_default,
        horizontal=True,
        label_visibility="collapsed",
    )

st.markdown(
    f"<h1 style='font-size:1.6rem;color:#1A202C;margin-bottom:0'>Monitoreo Topográfico · {dataset_name}</h1>"
    f"<p style='color:#718096;margin-top:0.2rem;font-size:0.9rem'>Baseline: {df_full['Date'].min().strftime('%d/%m/%Y')} · Último: {df_full[df_full['Monitoring_Number']>0]['Date'].max().strftime('%d/%m/%Y')}</p>",
    unsafe_allow_html=True,
)
st.divider()

# ── Si hay puntos seleccionados, renderizamos las gráficas ────────────────────
if not selected_points:
    st.warning("⚠️ Selecciona al menos un punto en el menú lateral para ver las métricas y gráficas.")
else:
    df = df_full[
        (df_full["Monitoring_Number"] == 0) |
        (
            (df_full["Date"].dt.date >= start_date) &
            (df_full["Date"].dt.date <= end_date) &
            (df_full["Monitoring_Number"] > 0)
        )
    ].copy()

    if nivel_sel in (0, 1):
        df = df[(df["Monitoring_Number"] == 0) | (df["Nivel_tanque"] == nivel_sel)].copy()

    from src.plots import (
        plot_desplazamiento_horizontal, plot_desplazamiento_vertical,
        plot_vectores, plot_vector_single,
    )

    CHART_CONFIG = dict(width="stretch", config={"displayModeBar": True, "modeBarButtonsToRemove": ["lasso2d", "select2d"], "toImageButtonOptions": {"format": "png", "scale": 2, "filename": f"Monitoreo_{dataset_name}"}, "scrollZoom": True})

    charts = [
        ("Desplazamiento Horizontal", plot_desplazamiento_horizontal),
        ("Desplazamiento Vertical",   plot_desplazamiento_vertical),
    ]

    for label, plot_fn in charts:
        st.markdown(f"<p class='section-header'>{label}</p>", unsafe_allow_html=True)
        st.plotly_chart(plot_fn(df, selected_points), **CHART_CONFIG)

    # ── Vectores en Planta ───────────────────────────────────────────────────────
    st.markdown("<p class='section-header'>Vectores en Planta</p>", unsafe_allow_html=True)
    st.plotly_chart(plot_vectores(df, selected_points), **CHART_CONFIG)

    # ── Vector individual por punto ──────────────────────────
    st.markdown("<p class='section-header'>🎯 Vector individual por punto</p>", unsafe_allow_html=True)

    all_points = df["Number"].dropna().unique().tolist()
    num_cols = min(3, len(all_points)) if len(all_points) > 0 else 1

    ind_cols = st.columns(num_cols)
    ind_points = []
    for col, default in zip(ind_cols, all_points[:num_cols]):
        with col:
            ind_points.append(st.selectbox("Punto", options=all_points, index=all_points.index(default), key=f"ind_{default}"))

    ind_chart_cols = st.columns(num_cols)
    for col, point in zip(ind_chart_cols, ind_points):
        with col:
            fig, info = plot_vector_single(df, point)
            st.plotly_chart(fig, **CHART_CONFIG)

            if info:
                st.markdown(f"""<div style='background-color:white; padding:12px 18px; border-radius:10px; border:1px solid #E8ECF0; font-size:0.85rem; margin-top:-10px; margin-bottom: 20px;'>
    <div style='font-weight:600; color:#1A202C; margin-bottom:6px;'>📍 ÚLTIMO MONITOREO ({info['date']})</div>
    <div style='color:#718096; display:flex; justify-content:space-between; flex-wrap: wrap;'>
        <span>Norte: <b>{info['n_abs']:.3f}</b></span>
        <span>Este: <b>{info['e_abs']:.3f}</b></span>
        <span>Elevación: <b>{info['z_abs']:.3f}</b></span>
    </div>
    <div style='margin:10px 0; border-top:1px solid #E8ECF0;'></div>
    <div style='color:#E53E3E; font-weight:600; margin-bottom:4px;'>Último Movimiento (Flecha Roja):</div>
    <div style='display:flex; justify-content:space-between; color:#1A202C; margin-bottom:4px;'>
        <span>Δ Norte: <b>{info['step_dy']:+.1f} mm</b></span>
        <span>Δ Este: <b>{info['step_dx']:+.1f} mm</b></span>
    </div>
    <div style='color:#1A202C; margin-bottom:8px;'>
        <span>Δ Elevación: <b>{info['step_dz']:+.1f} mm</b></span>
    </div>
    <div style='color:#1A202C; font-weight: 600; background-color:#F8F9FA; padding:8px 10px; border-radius:4px; display:flex; flex-direction:column; gap:4px;'>
        <span>Desplazamiento: {info['step_disp']:.1f} mm</span>
        <span>Hundimiento: {info['step_hundimiento']:.1f} mm</span>
    </div>
    </div>""", unsafe_allow_html=True)


# ── Imagen Interactiva del Tanque (SIEMPRE VISIBLE AL FINAL) ─────────────────
st.divider()
st.markdown("<p class='section-header'>Plano de Referencia del Tanque</p>", unsafe_allow_html=True)

TANQUE_IMG_PATH = os.path.join(os.path.dirname(__file__), "tanque.png")

if os.path.exists(TANQUE_IMG_PATH):
    try:
        # Abrimos la imagen con PIL
        img = Image.open(TANQUE_IMG_PATH)
        
        # Renderizamos la imagen usando Plotly para habilitar la interactividad
        fig_img = px.imshow(img)
        
        # Aumentamos el parámetro 'height' para darle espacio vertical y 
        # que el aspect ratio le permita usar todo el ancho de la pantalla
        fig_img.update_layout(
            coloraxis_showscale=False,
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis=dict(showticklabels=False, showgrid=False, zeroline=False, visible=False),
            yaxis=dict(showticklabels=False, showgrid=False, zeroline=False, visible=False, scaleanchor="x"),
            hovermode=False,
            dragmode="pan",
            autosize=True,
            height=900  # <--- Agregamos una altura base alta (puedes subirla a 1000 o 1200 si la imagen es muy alargada)
        )
        
        # config={"scrollZoom": True} habilita el zoom con la rueda del ratón
        st.plotly_chart(fig_img, use_container_width=True, config={"scrollZoom": True, "displayModeBar": True})
    except Exception as e:
        st.error(f"Error al cargar la imagen interactiva: {e}")
else:
    st.info("No se encontró la imagen del tanque en la ruta especificada.")