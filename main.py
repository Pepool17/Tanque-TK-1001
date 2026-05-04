# =============================================================================
# main.py — Generador de datos filtrados
# =============================================================================

import os
import sys
from src.extract import extract_data 

def main(excel_path: str):
    if not os.path.exists(excel_path):
        print(f"Error: No se encontró el archivo '{excel_path}'")
        return

    print(f"\nExtrayendo datos de: {excel_path}...")
    df = extract_data(excel_path)

    if df.empty:
        print("No se encontraron datos con la estructura esperada.")
        return

    # 1. Forzar el orden y filtro estricto de columnas requeridas
    columnas_finales = ["Monitoreo", "Nombre_punto", "Norte", "Este", "Elevacion", "Fecha", "Altura_tanque"]
    df_final = df[columnas_finales]

    # 2. Exportar
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "resultados_tanque.xlsx")
    
    df_final.to_excel(output_path, index=False)
    
    print(f"Extracción completada.")
    print(f"Se encontraron {len(df_final)} registros.")
    print(f"Archivo guardado en: {output_path}")

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "TK-1001 Puntos de monitoreo dique cunetas 26 Marzo 2026 (control 25).xlsx"
    main(path)