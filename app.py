
import os, json, sqlite3, re, unicodedata
from datetime import datetime
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Catálogo SB v2", layout="wide")

DB_PATH = os.getenv("DB_PATH", "catalog.db")
DATA_DIR = os.getenv("DATA_DIR", "data")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
DICT_PATH = os.getenv("DICT_PATH", "dictionary.json")
EXCEL_PATH = os.path.join(DATA_DIR, "records.xlsx")

# ---------- helpers
@st.cache_resource
def get_conn():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS gestor(
        id INTEGER PRIMARY KEY CHECK (id=1),
        departamento TEXT, division TEXT, persona TEXT, updated_at TEXT
    );""")
    return conn

def load_dict():
    try:
        with open(DICT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def tip(key):
    return st.session_state.get("_dict", {}).get(key, None)

def slugify(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii","ignore").decode("ascii")
    s = re.sub(r"[^A-Za-z0-9]+", ".", s.upper()).strip(".")
    return s[:15] if s else "NA"

TIPO_CODES = {
    "Serie":"SER",
    "Indicador simple":"IND",
    "Indicador compuesto":"COM",
    "Modelado":"MOD",
    "Otro":"OTR"
}

def next_code(tipo, categoria):
    # Code pattern: <TIPO>.<CAT>.<SEQ3>
    t = TIPO_CODES.get(tipo, "OTR")
    c = slugify(categoria)[:6]
    prefix = f"{t}.{c}"
    # Scan Excel if exists for highest seq for this prefix
    seq = 1
    if os.path.exists(EXCEL_PATH):
        try:
            df = pd.read_excel(EXCEL_PATH)
            if "AutoCode" in df.columns:
                matches = df[df["AutoCode"].astype(str).str.startswith(prefix + ".")]
                if not matches.empty:
                    nums = matches["AutoCode"].str.extract(r"\.(\d{3})$")[0].dropna().astype(int)
                    if not nums.empty:
                        seq = int(nums.max()) + 1
        except Exception:
            pass
    return f"{prefix}.{seq:03d}"

def ensure_excel():
    if not os.path.exists(EXCEL_PATH):
        cols = ["AutoCode","Tipo","Categoría","Nombre","Definición","Periodicidad","Unidad","Fórmula",
                "Fecha_Inicio_Disponibilidad","Código_fuente","Query_SQL","Fuente_Oracle",
                "Desagregación","Visualización","Ref_Metodológica_link","Ref_Metodológica_file",
                "Ref_Regulatoria_link","Ref_Regulatoria_file",
                "Departamento","División","Persona","Creado","Actualizado"]
        pd.DataFrame(columns=cols).to_excel(EXCEL_PATH, index=False)

def append_excel(row_dict):
    ensure_excel()
    df = pd.read_excel(EXCEL_PATH)
    df = pd.concat([df, pd.DataFrame([row_dict])], ignore_index=True)
    df.to_excel(EXCEL_PATH, index=False)

def save_upload_to(code, file):
    if not file:
        return ""
    folder = os.path.join(UPLOAD_DIR, code)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, file.name)
    with open(path, "wb") as f:
        f.write(file.read())
    return path

# ---------- init
conn = get_conn()
st.session_state["_dict"] = load_dict()

# ---------- sidebar
with st.sidebar:
    st.header("📖 Diccionario")
    q = st.text_input("Buscar")
    for k,v in st.session_state["_dict"].items():
        if not q or q.lower() in k.lower() or q.lower() in v.lower():
            with st.expander(k.replace("."," → ")):
                st.write(v)
    st.caption("Los tooltips en el formulario usan este diccionario.")

st.title("🗂️ Catálogo de Series e Indicadores — v2")

# ---------- Gestor (required once)
st.subheader("1) Gestor (obligatorio)")
cur = conn.execute("SELECT departamento, division, persona FROM gestor WHERE id=1")
row = cur.fetchone()
dep0, div0, per0 = (row or ["","",""])

with st.form("gestor", clear_on_submit=False):
    c1,c2,c3 = st.columns(3)
    departamento = c1.text_input("Departamento", value=dep0, help=tip("Gestor.Departamento"))
    division     = c2.text_input("División", value=div0, help=tip("Gestor.División"))
    persona      = c3.text_input("Persona encargada", value=per0, help=tip("Gestor.Persona_encargada"))
    save_g = st.form_submit_button("Guardar Gestor")
    if save_g:
        if not (departamento and division and persona):
            st.error("Todos los campos del Gestor son obligatorios.")
        else:
            conn.execute("INSERT INTO gestor(id,departamento,division,persona,updated_at) VALUES(1,?,?,?,?) "
                         "ON CONFLICT(id) DO UPDATE SET departamento=excluded.departamento, division=excluded.division, persona=excluded.persona, updated_at=excluded.updated_at",
                         (division, persona, datetime.now().isoformat()))
            conn.commit()
            st.success("Gestor guardado.")

st.divider()

# ---------- Form
st.subheader("2) Registro de Indicador/Serie")
tipo = st.radio("Tipo", ["Serie","Indicador simple","Indicador compuesto","Modelado","Otro"], horizontal=True, help=tip("Indicador.Tipo_de_indicador"))
nombre = st.text_input("Nombre", help=tip("Indicador.Nombre_del_indicador"))
categoria = st.text_input("Categoría", help=tip("Indicador.Categoría"))
definicion = st.text_area("Definición", help=tip("Indicador.Definición"))
periodicidad = st.selectbox("Periodicidad", ["Mensual","Trimestral","Anual","Diaria","Semanal","Otro"], help=tip("Indicador.Periodicidad"))
unidad = st.text_input("Unidad de medida", help=tip("Indicador.Unidad_de_medida"))
formula = st.text_area("Fórmula", help=tip("Indicador.Fórmula"))
fecha_inicio = st.text_input("Fecha_Inicio_Disponibilidad", help=tip("Indicador.Fecha_Inicio_Disponibilidad"))

c1,c2,c3 = st.columns(3)
codigo_fuente = c1.text_input("Código fuente (ruta/repo)", help=tip("Indicador.Código_fuente"))
query_sql     = c2.text_input("Query SQL (enlace/ruta)", help=tip("Indicador.Query_SQL"))
fuente_oracle = c3.text_input("Fuente Oracle (tabla/vista)", help=tip("Indicador.Fuente_Oracle"))

# multiselects
desag_opts = ["Entidad financiera","Tipo de cartera","Sector económico","Moneda","Región","Otro"]
desag = st.multiselect("Niveles de desagregación", desag_opts, help=tip("Indicador.Niveles_de_desagregación"))
vis_opts = ["SIMBAD","Dash","Power BI","Informe PDF","Portal web","Presentación ejecutiva","Otro"]
visual = st.multiselect("Visualización", vis_opts, help=tip("Indicador.Visualización"))

# references
st.markdown("### Referencias")
r1c1, r1c2 = st.columns(2)
ref_m_link = r1c1.text_input("Referencia Metodológica (link)")
ref_m_file = r1c2.file_uploader("Adjuntar ref. metodológica (PDF/DOC)", type=["pdf","doc","docx"])
r2c1, r2c2 = st.columns(2)
ref_r_link = r2c1.text_input("Referencia Regulatoria (link)")
ref_r_file = r2c2.file_uploader("Adjuntar ref. regulatoria (PDF/DOC)", type=["pdf","doc","docx"])

# submit
if st.button("Guardar registro"):
    # Gestor required
    cur = conn.execute("SELECT departamento, division, persona FROM gestor WHERE id=1")
    row = cur.fetchone()
    if not row or not all(row):
        st.error("Primero complete y guarde el bloque Gestor (todos sus campos son obligatorios).")
    elif not (nombre and tipo and categoria and definicion and periodicidad and unidad and formula and fecha_inicio):
        st.error("Campos obligatorios faltantes: Nombre, Tipo, Categoría, Definición, Periodicidad, Unidad, Fórmula, Fecha de inicio de disponibilidad.")
    elif not (codigo_fuente or query_sql or fuente_oracle):
        st.error("Debes completar al menos uno de: Código fuente, Query SQL o Fuente Oracle.")
    else:
        # generate code and save files
        code = next_code(tipo, categoria)
        mpath = save_upload_to(code, ref_m_file)
        rpath = save_upload_to(code, ref_r_file)
        # append to Excel
        row_dict = {
            "AutoCode": code,
            "Tipo": tipo,
            "Categoría": categoria,
            "Nombre": nombre,
            "Definición": definicion,
            "Periodicidad": periodicidad,
            "Unidad": unidad,
            "Fórmula": formula,
            "Fecha_Inicio_Disponibilidad": fecha_inicio,
            "Código_fuente": codigo_fuente,
            "Query_SQL": query_sql,
            "Fuente_Oracle": fuente_oracle,
            "Desagregación": "; ".join(desag) if desag else "",
            "Visualización": "; ".join(visual) if visual else "",
            "Ref_Metodológica_link": ref_m_link,
            "Ref_Metodológica_file": mpath,
            "Ref_Regulatoria_link": ref_r_link,
            "Ref_Regulatoria_file": rpath,
            "Departamento": row[0],
            "División": row[1],
            "Persona": row[2],
            "Creado": datetime.now().isoformat(timespec="seconds"),
            "Actualizado": datetime.now().isoformat(timespec="seconds"),
        }
        try:
            append_excel(row_dict)
            st.success(f"Registro guardado con código **{code}**. Excel actualizado en data/records.xlsx. Archivos en uploads/{code}/")
        except Exception as e:
            st.error(f"No se pudo guardar en Excel: {e}")
