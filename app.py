import streamlit as st
from google import genai
from google.genai import types
from datetime import datetime
import pandas as pd
import os
import time

# 1. CONFIGURACIÓN DE LA PÁGINA (Debe ser lo primero)
st.set_page_config(page_title="Aura - Tutora Virtual", page_icon="✨", layout="centered")

# Recuperación de la API Key de Gemini desde los secretos del servidor
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

# 2. INYECCIÓN DE ESTILOS CSS (Fondo blanco institucional, centrado absoluto y limpieza visual)
st.markdown("""
    <style>
    .stApp, [data-testid="stAppViewContainer"], .stChatMessage {
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
    }
    [data-testid="stHeader"] { background-color: transparent !important; }
    div[data-testid="stToolbar"] { visibility: hidden; display: none; }
    #MainMenu, footer, [data-testid="stDecoration"] { visibility: hidden; display: none; }
    
    /* Contenedor centralizado para los títulos según la segunda captura */
    .centered-header-block {
        text-align: center;
        width: 100%;
        padding-top: 10px;
    }
    .main-title { 
        font-family: 'Inter', sans-serif; 
        color: #0A2540 !important; 
        font-weight: 700; 
        margin-bottom: 8px;
        text-align: center;
        font-size: 2.2rem;
    }
    .sub-caption { 
        font-family: 'Inter', sans-serif; 
        color: #4A5568 !important; 
        font-size: 1rem; 
        margin-bottom: 25px; 
        border-bottom: 1px solid #E2E8F0; 
        padding-bottom: 20px;
        text-align: center;
    }
    p, span, li, label, .stMarkdown, h1, h2, h3 { color: #1A202C !important; }
    
    /* Estructura del input del chat flotante */
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
            "avatar": "✨",
            "content": (
                "### ¡Bienvenido(a)!\n\n"
                "Hola. Les saluda **Aura**, tutora académica en línea del EDA de **Derecho del Trabajo**, "
                "un espacio académico gestionado por el Prof: Luis Ignacio Chirinos Campos.\n\n"
                "Cuento con la preparación para brindarles orientación, guía y acompañamiento en todo lo relacionado "
                "con el contenido temático de nuestra unidad curricular. Las respuestas emitidas se fundamentan de forma estricta "
                "en la doctrina jurídica, la normativa laboral vigente y los materiales académicos autorizados.\n\n"
                "**¿De qué manera puedo apoyarles en su formación?**\n"
                "* Solventar dudas sobre los temas de las unidades de estudio.\n"
                "* Estudiar y repasar conceptos y contenidos temáticos esenciales.\n"
                "* Guiar el aprendizaje de manera pedagógica y clara.\n\n"
                "Les invito a utilizar este apoyo con responsabilidad e integridad académica. "
                "¿Qué tema o consulta académica desean abordar hoy?"
            )
        }
    ]

# Inicialización del control de tiempo para mitigar saturación de cuota
if "ultimo_envio" not in st.session_state:
    st.session_state.ultimo_envio = 0.0

# 3. ESTRUCTURA DE PESTAÑAS NATIVAS (Alineadas visualmente a la izquierda en Streamlit)
tab_eda, tab_profesor = st.tabs(["💬 EDA", "🔐 Profesor"])

# ==========================================
# PESTAÑA 1: EDA (CHAT EN LÍNEA)
# ==========================================
with tab_eda:
    # Bloque de encabezado perfectamente centrado y libre de iconos
    st.markdown("""
        <div class="centered-header-block">
            <h1 class="main-title">Aura: Tutora Académica en Línea</h1>
            <p class="sub-caption">Unidad Curricular: Derecho del Trabajo | Prof: Luis Ignacio Chirinos Campos</p>
        </div>
    """, unsafe_allow_html=True)

    system_instruction = (
        "Eres 'Aura', una tutora académica en línea experta en Derecho del Trabajo para el DCEE de la "
        "Universidad Centroccidental Lisandro Alvarado (UCLA).\n\n"
        "CONTEXTO DE TU DESARROLLO E IDENTIDAD:\n"
        "- Fuiste desarrollada, programada y configurada exclusivamente por el profesor y abogado "
        "Luis Ignacio Chirinos Campos, quien es tu creador y el docente ordinario de esta asignatura.\n"
        "- Si alguien te pregunta por tu origen, creador, desarrollador o profesor de la materia, "
        "debes reconocer con orgullo, respeto y claridad institucional que eres una creación tecnológica "
        "del profesor Luis Ignacio Chirinos Campos para el beneficio académico del estudiantado, y perteneces al ecosistema digital de aprendizaje de la unidad curricular.\n\n"
        "PAUTAS DE COMPORTAMIENTO Y PEDAGOGÍA:\n"
        "- Tu propósito es guiar a quienes estudian de forma pedagógica, rigurosa aunque amable, clara, cálida y cercana.\n"
        "- Utiliza siempre un lenguaje neutral, inclusivo y formal, adecuado para el ámbito de la educación universitaria virtual o a distancia.\n"
        "- Responde basándote estrictamente en la doctrina jurídica laboral, la normativa legal venezolana "
        "vigente y los lineamientos académicos proporcionados por la cátedra.\n"
        "- Evita respuestas genéricas de asistente virtual de internet. Eres una herramienta académica del Ecosistema Digital de Aprendizaje (EDA) de Derecho del Trabajo del Decanato de Ciencias Económicas y Empresariales de la UCLA."
    )

    # Renderizar el contenedor del historial dentro de la pestaña activa
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar=message.get("avatar")):
            st.markdown(message["content"])

    # Captura del prompt (Ubicado correctamente al final del bloque para asegurar interactividad)
    prompt = st.chat_input("Escribe tu consulta jurídica aquí...", key="chat_input_eda")

    if prompt:
        tiempo_actual = time.time()
        tiempo_transcurrido = tiempo_actual - st.session_state.ultimo_envio
        
        # Restricción obligatoria de tráfico para los 100 estudiantes
        if tiempo_transcurrido < 15.0:
            tiempo_espera = int(15.0 - tiempo_transcurrido)
            st.warning(f"⏳ Para garantizar el acceso de todos los miembros del grupo, por favor espera {tiempo_espera} segundos antes de enviar otra consulta.")
        else:
            st.session_state.ultimo_envio = tiempo_actual
            registrar_consulta_local(prompt)
            
            # Mostrar inmediatamente la consulta de quien estudia
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)
            st.session_state.messages.append({"role": "user", "avatar": "👤", "content": prompt})

            # Generación de la respuesta asistida por el modelo estable de Gemini
            with st.chat_message("assistant", avatar="✨"):
                if not api_key:
                    st.error("Error: No se encontró la configuración de la API Key ('gemini_api_key').")
                else:
                    try:
                        client = genai.Client(api_key=api_key)
                        
                        history_contents = []
                        for msg in st.session_state.messages[:-1]:
                            role
