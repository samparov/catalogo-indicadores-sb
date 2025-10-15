
# Streamlit Catalog App v2 (SB)

- Saves every submission to **data/records.xlsx** (append mode).
- Auto **code/id** computed from Tipo + Categoría with a rolling sequence per pair.
- Attachments saved to **uploads/<AUTO_CODE>/** and paths recorded in Excel.
- Multiselect fields: **Niveles de desagregación** and **Visualización**.
- Required fields: Gestor (all), Nombre, Tipo, Categoría, Definición, Periodicidad, Unidad, Fórmula, Fecha Inicio Disponibilidad, and at least **one of** (Código fuente | Query SQL | Fuente Oracle).
