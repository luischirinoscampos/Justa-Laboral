import streamlit as st
from google import genai
from google.genai import types
from datetime import datetime
import pandas as pd
import os
import time
import json
import gspread

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Aura - Tutora Virtual", page_icon="✨", layout="centered")

# Recuperación de credenciales desde los secretos de Streamlit
api_key = st.secrets.get("gemini_api_key", None)

# RUTAS DE ARCHIVOS LOCALES Y CONFIGURACIÓN DE SHEETS
ARCHIVO_BITACORA = "consultas_local.csv"
ARCHIVO_CONOCIMIENTO = "vector_store.json"
NOMBRE_HOJA_SHEETS = "Bitacora_Aura"  # Debe coincidir exactamente con el título de su Google Sheets

def conectar_google_sheets():
    """Establece conexión con Google Sheets utilizando las credenciales de los secretos"""
    try:
        credenciales = {
            "type": st.secrets["gspread"]["type"],
            "project_id": st.secrets["gspread"]["project_id"],
            "private_key_id": st.secrets["gspread"]["private_key_id"],
            "private_key": st.secrets["gspread"]["private_key"],
            "client_email": st.secrets["gspread"]["client_email"],
            "client_id": st.secrets["gspread"]["client_id"],
            "auth_uri": st.secrets["gspread"]["auth_uri"],
            "token_uri": st.secrets["gspread"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["gspread"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["gspread"]["client_x509_cert_url"],
            "universe_domain": st.secrets["gspread"].get("universe_domain", "googleapis.com")
        }
        gc = gspread.service_account_from_dict(credenciales)
        sh = gc.open(NOMBRE_HOJA_SHEETS)
        return sh.get_worksheet(0)  # Retorna la primera pestaña de la hoja
    except Exception:
        return None

def registrar_consulta_dual(texto_pregunta, respuesta_aura):
    """Guarda la consulta localmente en el CSV y asíncronamente en Google Sheets"""
    ahora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    p_limpia = str(texto_pregunta).replace("\n", " ").replace("\r", " ").replace('"', '""')
    r_limpia = str(respuesta_aura).replace("\n", " ").replace("\r", " ").replace('"', '""')
    
    # --- OPERACIÓN 1: ALMACENAMIENTO LOCAL (CSV) ---
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
        pass  # Garantiza que fallos en disco no congelen la interfaz

    # --- OPERACIÓN 2: ALMACENAMIENTO EN LA NUBE (GOOGLE SHEETS) ---
    try:
        hoja = conectar_google_sheets()
        if hoja is not None:
            # Añade una nueva fila al final de la hoja con los tres datos limpios
            hoja.append_row([ahora, p_limpia, r_limpia])
    except Exception:
        pass  # Si no hay internet o expira la cuota de Google, la app sigue funcionando normalmente

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

# 2. INYECCIÓN DE ESTILOS CSS
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
# PESTAÑA 1: EDA (CHAT)
# ==========================================
with tab_eda:
    system_instruction = f"""
Eres Aura, una tutora académica en línea experta en Derecho del Trabajo para el de la Universidad Centroccidental Lisandro Alvarado (UCLA).
Tu comunicación debe caracterizarse por una claridad respetuosa y una honestidad total.

PAUTAS DE COMPORTAMIENTO Y PEDAGOGÍA:
- Tu propósito es guiar a quienes estudiar de forma pedagógica, rigurosa aunque amable, clara, cálida y cercana.
- Utiliza siempre un lenguaje neutral, inclusivo y formal, adecuado para el ámbito de la educación universitaria virtual o a distancia.

FUENTE PRINCIPAL DE CONOCIMIENTO (REPOSITORIO DE LA CÁTEDRA):
=========================================
{CONTEXTO_LEGAL_CATEDRA}
=========================================
"""

    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar=message.get("avatar")):
            st.markdown(message["content"])

    prompt = st.chat_input("Escribe tu consulta jurídica aquí...", key="chat_input_eda")

    if prompt:
        tiempo_actual = time.time()
        tiempo_transcurrido = tiempo_actual - st.session_state.ultimo_envio
        
        if tiempo_transcurrido < 15.0:
            tiempo_espera = int(15.0 - tiempo_transcurrido)
            st.warning(f"⏳ Por favor espera {tiempo_espera} segundos antes de enviar otra consulta.")
        else:
            st.session_state.ultimo_envio = tiempo_actual
            
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)
            st.session_state.messages.append({"role": "user", "avatar": "👤", "content": prompt})

            with st.chat_message("assistant", avatar="✨"):
                if not api_key:
                    st.error("Error: No se encontró la configuración de la API Key.")
                    registrar_consulta_dual(prompt, "ERROR: Configuración de API Key ausente.")
                else:
                    try:
                        client = genai.Client(api_key=api_key)
                        history_contents = []
                        for msg in st.session_state.messages:
                            role_mapped = "model" if msg["role"] == "assistant" else "user"
                            history_contents.append(
                                types.Content(role=role_mapped, parts=[types.Part.from_text(text=msg["content"])])
                            )
                        
                        config = types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.3)
                        response = client.models.generate_content(model='gemini-2.5-flash', contents=history_contents, config=config)
                        
                        respuesta_texto = response.text
                        st.markdown(respuesta_texto)
                        st.session_state.messages.append({"role": "assistant", "avatar": "✨", "content": respuesta_texto})
                        
                        # Doble registro automático
                        registrar_consulta_dual(prompt, respuesta_texto)
                        st.rerun()
                        
                    except Exception as e:
                        error_str = str(e)
                        if "RESOURCE_EXHAUSTED" in error_str:
                            clean_error = "Se ha agotado la cuota temporal de consultas de la API."
                        else:
                            clean_error = f"Ocurrió un inconveniente: {error_str}"
                        
                        st.error(clean_error)
                        registrar_consulta_dual(prompt, f"ERROR: {error_str}")

# ==========================================
# PESTAÑA 2: PROFESOR
# ==========================================
with tab_profesor:
    st.subheader("Bitácora de Consultas Locales")
    clave = st.text_input("Introduzca credencial docente:", type="password", key="docente_password")

    if clave == "UCLA2026":
        st.success("Acceso Docente Verificado")
        
        if os.path.exists(ARCHIVO_BITACORA):
            try:
                df_log = pd.read_csv(ARCHIVO_BITACORA, encoding='utf-8', on_bad_lines='skip')
                columnas_requeridas = ["Cuándo", "Qué preguntaron", "Respuesta de Aura"]
                
                if df_log.empty or not all(col in df_log.columns for col in columnas_requeridas):
                    os.remove(ARCHIVO_BITACORA)
                    df_log = pd.DataFrame(columns=columnas_requeridas)
                
                if not df_log.empty:
                    st.dataframe(df_log.iloc[::-1], use_container_width=True)
                    csv_data = df_log.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Descargar Reporte Local (CSV)",
                        data=csv_data,
                        file_name=f"interacciones_aura_{datetime.now().strftime('%d_%m_%Y')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("Aún no se registran interacciones locales en este servidor.")
            except Exception as e:
                st.error(f"Error al leer la bitácora local: {e}")
        else:
            st.info("Aún no se registran interacciones locales.")
