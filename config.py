# =============================================================================
# config.py — Configuración global del proyecto de monitoreo
# =============================================================================
# Se agrega el path del archivo a analizar indivualmente al correr el main.py
# (para la aplicación web no se usa el path)
EXCEL_PATH = "KP 151+850 Monitoreo topográfico ventanas.xlsx" 
OUTPUT_DIR  = "output"
PROJECT_SISTEMA = "Sistema UTM PSAD56"

ALERT_COLORS = {
    "NORMAL":   "#2D9E5C",
    "ATENCIÓN": "#F0B429",
    "CRÍTICO":  "#E53E3E",
}

PALETTE = {
    "bg":    "#F8F9FA",
    "panel": "#FFFFFF",
    "grid":  "#E8ECF0",
    "text":  "#1A202C",
    "muted": "#718096",
}

# Umbrales de alerta (en metros para tasas, en mm para acumulados) 
THRESH_H_WARN_RATE  = None
THRESH_H_CRIT_RATE  = None
THRESH_H_WARN_ACCUM = None
THRESH_H_CRIT_ACCUM = None

THRESH_V_WARN_RATE  = None
THRESH_V_CRIT_RATE  = None
THRESH_V_WARN_ACCUM = None
THRESH_V_CRIT_ACCUM = None

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
    # --- Errores de tipeo comunes en campo ---
    "fefrero": 2, 
    "setiembre": 9
}