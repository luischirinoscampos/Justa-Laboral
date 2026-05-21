import streamlit as st
from google import genai
from google.genai import types
from datetime import datetime
import pandas as pd
import os
import time
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Aura - Tutora Virtual", page_icon="✨", layout="centered")

# Recuperación de la clave de la API desde los secretos de Streamlit
api_key = st.secrets.get("gemini_api_key", None)

# CONFIGURACIÓN DE ALMACENAMIENTO DUAL
ARCHIVO_BITACORA = "consultas_local.csv"
ARCHIVO_CONOCIMIENTO = "vector_store.json"
NOMBRE_HOJA_SHEETS = "Bitacora_Aura"  # Debe coincidir exactamente con el nombre de su Google Sheets

def conectar_google_sheets():
    """Establece conexión sólida limpiando la llave privada de los secretos en memoria"""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # Corrección de saltos de línea en la llave privada si viene mal escapada de Streamlit Cloud
        private_key = st.secrets["gspread"]["private_key"]
        if "\\n" in private_key:
            private_key = private_key.replace("\\n", "\n")
            
        credenciales_dict = {
            "type": st.secrets["gspread"]["type"],
            "project_id": st.secrets["gspread"]["project_id"],
            "private_key_id": st.secrets["gspread"]["private_key_id"],
            "private_key": private_key,
            "client_email": st.secrets["gspread"]["client_email"],
            "client_id": st.secrets["gspread"]["client_id"],
            "auth_uri": st.secrets["gspread"]["auth_uri"],
            "token_uri": st.secrets["gspread"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["gspread"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["gspread"]["client_x509_cert_url"]
        }
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(credenciales_dict, scope)
        gc = gspread.authorize(creds)
        sh = gc.open(NOMBRE_HOJA_SHEETS)
        return sh.sheet1  # Accede directamente a la primera pestaña
    except Exception as e:
        st.session_state["error_gsheets_conexion"] = str(e)
        return None

def registrar_consulta_dual(texto_pregunta, respuesta_o_error):
    """Registra de forma dual forzando la conversión limpia a texto plano"""
    ahora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    
    # Limpieza estricta de cadenas para evitar errores de formato en las celdas de Sheets
    p_limpia = str(texto_pregunta).replace("\n", " ").replace("\r", " ").strip()
    r_limpia = str(respuesta_o_error).replace("\n", " ").replace("\r", " ").strip()
    
    # --- OPERACIÓN 1: CSV LOCAL ---
    try:
        nuevo_registro = pd.DataFrame([{
            "Cuándo": ahora, 
            "Qué preguntaron": f'"{p_limpia}"', 
            "Respuesta de Aura": f'"{r_limpia}"'
        }])
        if os.path.exists(ARCHIVO_BITACORA):
            nuevo_registro.to_csv(ARCHIVO_BITACORA, mode='a', header=False, index=False, encoding='utf-8')
        else:
            nuevo_registro.to_csv(ARCHIVO_BITACORA, mode='w', header=True, index=False, encoding='utf-8')
    except Exception:
        pass

    # --- OPERACIÓN 2: GOOGLE SHEETS ---
    try:
        hoja = conectar_google_sheets()
        if hoja is not None:
            hoja.append_row([str(ahora), str(p_limpia), str(r_limpia)])
            st.session_state["error_gsheets_escritura"] = None
        else:
            if "error_gsheets_conexion" not in st.session_state:
                st.session_state["error_gsheets_escritura"] = "No se pudo establecer conexión (Hoja ausente o credenciales inválidas)."
    except Exception as e:
        st.session_state["error_gsheets_escritura"] = str(e)

@st.cache_data
def cargar_contexto_catedra():
    """Lee el repositorio estructurado local para inyectarlo en la base de conocimientos de Aura"""
    if os.path.exists(ARCHIVO_CONOCIMIENTO):
        try:
            with open(ARCHIVO_CONOCIMIENTO, "r", encoding="utf-8") as f:
                datos = json.load(f)
                contexto_unificado = ""
                for item in datos:
                    contexto_unificado += f"\nDocumento: {item['nombre_archivo']}\nContenido: {item['texto_contenido']}\n---"
                return contexto_unificado
        except Exception:
            return ""
    return ""

CONTEXTO_LEGAL_CATEDRA = cargar_contexto_catedra()

# 2. INYECCIÓN DE ESTILOS CSS (Interfaz de la Cátedra)
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
        overflow-x: hidden !important;
    }
    .block-container {
        padding: 1rem !important;
        max-width: 100% !important;
    }
    .stApp, .stChatMessage { background-color: #FFFFFF !important; }
    div[data-testid="stToolbar"], #MainMenu, footer, [data-testid="stDecoration"] { visibility: hidden; display: none; }
    
    .custom-header {
        text-align: center;
        width: 100%;
        margin-top: 5px;
        margin-bottom: 15px;
        font-family: 'Inter', sans-serif;
    }
    .line-1 { color: #0A2540 !important; font-size: 2.4rem; font-weight: 700; margin-bottom: 2px; }
    .line-2 { color: #1A202C !important; font-size: 1.4rem; font-weight: 600; margin-bottom: 6px; }
    .line-3 { color: #4A5568 !important; font-size: 1.05rem; font-weight: 400; margin-bottom: 4px; }
    .line-4 { color: #4A5568 !important; font-size: 1.05rem; font-weight: 400; margin-bottom: 12px; }
    .line-divider { border-bottom: 1px solid #E2E8F0; width: 100%; }
    p, span, li, label, .stMarkdown, h1, h2, h3 { color: #1A202C !important; }
    [data-testid="stChatInput"] { background-color: #FFFFFF !important; }
    [data-testid="stChatInput"] > div { background-color: #F8FAFC !important; border: 1px solid #CBD5E1 !important; border-radius: 8px !important; }
    [data-testid="stChatInput"] textarea { color: #0A2540 !important; font-family: 'Inter', sans-serif !important; }
    </style>
""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "avatar": "✨",
            "content": (
                "### ¡Bienvenido(a)!\n\n"
                "Hola. Soy **Aura**, tutora académica en línea del EDA de **Derecho del Trabajo**, "
                "un espacio académico gestionado por la cátedra.\n\n"
                "Cuento con la preparación para brindarles orientación, guía y acompañamiento en todo lo relacionado "
                "con el contenido temático de nuestra unidad curricular. Las respuestas emitidas se fundamentan de forma estricta "
                "en la doctrina jurídica, la normativa laboral vigente y los materiales académicos autorizados.\n\n"
                "**¿De qué manera puedo apoyarles en su formación?**\n"
                "* Solventar dudas sobre los temas de las unidades de estudio.\n"
                "* Estudiar y repasar conceptos y contenidos temáticos esenciales.\n"
                "* Guiar el aprendizaje de manera pedagógica y clara.\n\n"
                "Les invito a utilizar este apoyo con responsabilidad e integridad académica. "
                "¿Qué tema o consulta académica deseas abordar hoy?"
            )
        }
    ]

if "ultimo_envio" not in st.session_state:
    st.session_state.ultimo_envio = 0.0

st.markdown("""
    <div class="custom-header">
        <div class="line-1">Aura</div>
        <div class="line-2">Tutora Académica en Línea</div>
        <div class="line-3">Unidad Curricular: Derecho del Trabajo</div>
        <div class="line-4">Desarrollador: Ecosistema Digital de Aprendizaje</div>
        <div class="line-divider"></div>
    </div>
""", unsafe_allow_html=True)

tab_eda, tab_profesor = st.tabs(["💬 EDA", "🔐 Profesor"])

# ==========================================
# PESTAÑA 1: EDA (INTERFAZ DE CONSULTAS)
# ==========================================
with tab_eda:
    system_instruction = f"""
Eres Aura, una tutora académica en línea experta en Derecho del Trabajo para la
