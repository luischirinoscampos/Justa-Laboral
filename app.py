import streamlit as st
from google import genai
from google.genai import types
from datetime import datetime
import pandas as pd
import os

# 1. CONFIGURACIÓN DE LA PÁGINA (Debe ser lo primero)
st.set_page_config(page_title="Justa - Tutora Virtual", page_icon="⚖️", layout="centered")

# Recuperación de la API Key de Gemini
api_key = st.secrets.get("gemini_api_key", None)

# RUTA DEL ARCHIVO LOCAL DE BITÁCORA
ARCHIVO_BITACORA = "consultas_local.csv"

def registrar_consulta_local(texto_pregunta):
    """Guarda la consulta de inmediato en un archivo CSV local"""
    try:
        ahora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        nuevo_registro = pd.DataFrame([{"Cuándo": ahora, "Qué preguntaron": texto_pregunta}])
        
        if os.path.exists(ARCHIVO_BITACORA):
            nuevo_registro.to_csv(ARCHIVO_BITACORA, mode='a', header=False, index=False, encoding='utf-8')
        else:
            nuevo_registro.to_csv(ARCHIVO_BITACORA, mode='w', header=True, index=False, encoding='utf-8')
    except Exception:
        pass

# 2. INYECCIÓN DE ESTILOS CSS (Fondo blanco institucional y limpieza visual)
st.markdown("""
    <style>
    .stApp, [data-testid="stAppViewContainer"], .stChatMessage {
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
    }
    [data-testid="stHeader"] { background-color: transparent !important; }
    div[data-testid="stToolbar"] { visibility: hidden; display: none; }
    #MainMenu, footer, [data-testid="stDecoration"] { visibility: hidden; display: none; }
    
    .main-title { font-family: 'Inter', sans-serif; color: #0A2540 !important; font-weight: 700; margin-bottom: 5px; }
    .sub-caption { font-family: 'Inter', sans-serif; color: #4A5568 !important; font-size: 0.95rem; margin-bottom: 25px; border-bottom: 1px solid #E2E8F0; padding-bottom: 15px; }
    p, span, li, label, .stMarkdown, h1, h2, h3 { color: #1A202C !important; }
    
    /* Input del chat flotante abajo en la raíz */
    [data-testid="stChatInput"] {
        background-color: #FFFFFF !important;
    }
    [data-testid="stChatInput"] > div {
        background-color: #F8FAFC !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 8px !important;
    }
    [data-testid="stChatInput"] textarea {
        color: #0A2540 !important;
        font-family: 'Inter', sans-serif !important;
    }
    
    [data-testid="stChatMessageAvatarCell"] > div {
        background-color: transparent !important;
    }
    </style>
""", unsafe_allow_html=True)

# Inicialización obligatoria del historial antes de renderizar pestañas
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "avatar": "⚖️",
            "content": (
                "### ¡Bienvenido(a)!\n\n"
                "Hola. Soy **Justa**, tutora académica virtual del EDA de **Derecho del Trabajo**, "
                "espacio académico gestionado por Luis Ignacio Chirinos Campos.\n\n"
                "Cuento con la preparación para brindarte orientación, guía y acompañamiento en todo lo relacionado "
                "con el contenido temático de nuestra unidad curricular. Mis respuestas se fundamentan de forma estricta "
                "en la doctrina jurídica, la normativa laboral vigente y los materiales académicos autorizados.\n\n"
                "**¿Cómo te puedo apoyar en tu formación?**\n"
                "* Solventar dudas sobre los temas de las unidades de estudio.\n"
                "* Estudiar y repasar conceptos y contenidos temáticos esenciales.\n"
                "* Guiar tu aprendizaje de manera pedagógica y clara.\n\n"
                "Te invito a utilizar mi apoyo con responsabilidad e integridad académica. "
                "¿Qué tema o consulta académica deseas abordar hoy?"
            )
        }
    ]

# 3. CAPTURA DEL INPUT EN LA RAÍZ (Esto obliga a Streamlit a fijarlo abajo del todo)
prompt = st.chat_input("Escribe tu consulta jurídica aquí...")

# 4. ESTRUCTURA DE PESTAÑAS
tab_chat, tab_docente = st.tabs(["💬 Aula Virtual", "🔐 Control Docente"])

# ==========================================
# PESTAÑA 1: AULA VIRTUAL (CHAT)
# ==========================================
with tab_chat:
    st.markdown('<h1 class="main-title">⚖️ Justa: Tutora Académica Virtual</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-caption">Asignatura: Derecho del Trabajo | Docencia: Luis Ignacio Chirinos Campos</p>', unsafe_allow_html=True)

    system_instruction = (
        "Eres 'Justa', una tutora académica experta en Derecho del Trabajo para el DCEE de la "
        "Universidad Centroccidental Lisandro Alvarado (UCLA).\n\n"
        "CONTEXTO DE TU DESARROLLO E IDENTIDAD:\n"
        "- Fuiste desarrollada, programada y configurada exclusivamente por el profesor y abogado "
        "Luis Ignacio Chirinos Campos, quien es tu creador y el docente ordinario de esta asignatura.\n"
        "- Si alguien te pregunta por tu origen, creador, desarrollador o profesor de la materia, "
        "debes reconocer con orgullo, respeto y claridad institucional que eres una creación tecnológica "
        "del profesor Luis Ignacio Chirinos Campos para el beneficio académico del estudiantado, y perteneces al ecosistma digital de aprendizaje de la unidad curricular.\n\n"
        "PAUTAS DE COMPORTAMIENTO Y PEDAGOGÍA:\n"
        "- Tu propósito es guiar a quienes estudian de forma pedagógica, rigurosa aunque amable, clara, cálida y cercana.\n"
        "- Utiliza siempre un lenguaje neutral, inclusivo y formal, adecuado para el ámbito universitario.\n"
        "- Responde basándote estrictamente en la doctrina jurídica laboral, la normativa legal venezolana "
        "vigente y los lineamientos académicos proporcionados por la cátedra.\n"
        "- Evita respuestas genéricas de asistente virtual de internet. Eres una herramienta académica del Ecosistema Digital de Aprendizaje de Derecho del Trabajo del Decanato de Ciencias Económicas y Empresariales de la UCLA."
    )

    # Renderizar todos los mensajes procesados hasta ahora
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar=message.get("avatar")):
            st.markdown(message["content"])

    # Si hay una nueva entrada desde el fondo de la pantalla, se procesa aquí adentro
    if prompt:
        registrar_consulta_local(prompt)
        
        # Mostrar el mensaje del estudiante
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "avatar": "👤", "content": prompt})

        # Generar respuesta de Justa
        with st.chat_message("assistant", avatar="⚖️"):
            if not api_key:
                st.error("Error: No se encontró la configuración de la API Key ('gemini_api_key').")
            else:
                try:
                    client = genai.Client(api_key=api_key)
                    
                    history_contents = []
                    for msg in st.session_state.messages[:-1]:
                        role_mapped = "model" if msg["role"] == "assistant" else "user"
                        history_contents.append(
                            types.Content(role=role_mapped, parts=[types.Part.from_text(text=msg["content"])])
                        )
                    
                    config = types.GenerateContentConfig(
                        system_instruction=system_instruction, 
                        temperature=0.3
                    )
                    
                    response = client.models.generate_content(
                        model='gemini-2.5-flash', 
                        contents=prompt, 
                        config=config
                    )
                    
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "avatar": "⚖️", "content": response.text})
                    
                    # Forzar recarga limpia para pintar el nuevo mensaje en el orden correcto
                    st.rerun()
                    
                except Exception as e:
                    error_str = str(e)
                    clean_error = "Se ha agotado la cuota temporal de consultas de la API. El servicio se restablecerá pronto." if "RESOURCE_EXHAUSTED" in error_str else f"Ocurrió un inconveniente: {error_str}"
                    st.error(clean_error)

# ==========================================
# PESTAÑA 2: CONTROL DOCENTE
# ==========================================
with tab_docente:
    st.markdown('<h2 class="main-title">🔐 Panel de Gestión Académica</h2>', unsafe_allow_html=True)
    clave = st.text_input("Introduzca credencial docente:", type="password", key="docente_password")

    if clave == "UCLA2026":
        st.success("Acceso Docente Verificado")
        st.subheader("Bitácora de Consultas Locales")
        
        if os.path.exists(ARCHIVO_BITACORA):
            try:
                df_log = pd.read_csv(ARCHIVO_BITACORA, encoding='utf-8')
                if not df_log.empty:
                    st.dataframe(df_log.iloc[::-1], use_container_width=True)
                    
                    csv_data = df_log.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Descargar Reporte Completo (CSV)",
                        data=csv_data,
                        file_name=f"interacciones_justa_{datetime.now().strftime('%d_%m_%Y')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("El archivo de bitácora está vacío.")
            except Exception as e:
                st.error(f"Error al leer la bitácora local: {e}")
        else:
            st.info("Aún no se registran interacciones en este servidor.")
