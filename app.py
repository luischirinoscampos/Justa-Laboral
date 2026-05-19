import streamlit as st
from google import genai
from google.genai import types
from datetime import datetime
import pandas as pd
import os
import time

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Aura - Tutora Virtual", page_icon="✨", layout="centered")

# Recuperación de la API Key de Gemini desde los secretos
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

# 2. INYECCIÓN DE ESTILOS CSS REFORZADOS PARA INCRUSTACIÓN EN MOODLE (IFRAME)
st.markdown("""
    <style>
    /* Forzar comportamiento estricto dentro de marcos (Evita ventanas emergentes) */
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
    }
    
    /* Optimización de espacios para visualización embebida en Moodle */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    
    .stApp, .stChatMessage {
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
    }
    [data-testid="stHeader"] { background-color: transparent !important; }
    div[data-testid="stToolbar"] { visibility: hidden; display: none; }
    #MainMenu, footer, [data-testid="stDecoration"] { visibility: hidden; display: none; }
    
    /* Bloque de diseño de las 4 líneas centradas solicitado */
    .custom-header {
        text-align: center;
        width: 100%;
        margin-top: 5px;
        margin-bottom: 15px;
        font-family: 'Inter', sans-serif;
    }
    .line-1 {
        color: #0A2540 !important;
        font-size: 2.4rem;
        font-weight: 700;
        margin-bottom: 2px;
    }
    .line-2 {
        color: #1A202C !important;
        font-size: 1.4rem;
        font-weight: 600;
        margin-bottom: 6px;
    }
    .line-3 {
        color: #4A5568 !important;
        font-size: 1.05rem;
        font-weight: 400;
        margin-bottom: 4px;
    }
    .line-4 {
        color: #4A5568 !important;
        font-size: 1.05rem;
        font-weight: 400;
        margin-bottom: 12px;
    }
    .line-divider {
        border-bottom: 1px solid #E2E8F0;
        width: 100%;
    }
    p, span, li, label, .stMarkdown, h1, h2, h3 { color: #1A202C !important; }
    
    /* Input del chat flotante adaptivo */
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
    
    <script>
        document.addEventListener("DOMContentLoaded", function() {
            // Re-direcciona de forma estricta los clicks hacia el propio frame
            const bases = document.getElementsByTagName('base');
            if (bases.length > 0) {
                bases[0].target = "_self";
            } else {
                const baseNode = document.createElement('base');
                baseNode.target = "_self";
                document.head.appendChild(baseNode);
            }
        });
    </script>
""", unsafe_allow_html=True)

# Inicialización obligatoria del historial antes de las pestañas
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
                "¿Qué tema o consulta académica deseas abordar hoy?"
            )
        }
    ]

# Inicialización del control de tiempo
if "ultimo_envio" not in st.session_state:
    st.session_state.ultimo_envio = 0.0

# =========================================================================
# ENCABEZADO SOLICITADO (4 LÍNEAS CENTRADAS, SIN COMILLAS, SIN ICONOS)
# =========================================================================
st.markdown("""
    <div class="custom-header">
        <div class="line-1">Aura</div>
        <div class="line-2">Tutora Académica en Línea</div>
        <div class="line-3">Unidad Curricular: Derecho del Trabajo</div>
        <div class="line-4">Desarrollador: Luis Ignacio Chirinos Campos</div>
        <div class="line-divider"></div>
    </div>
""", unsafe_allow_html=True)

# 3. ESTRUCTURA DE PESTAÑAS NATIVAS
tab_eda, tab_profesor = st.tabs(["💬 EDA", "🔐 Profesor"])

# ==========================================
# PESTAÑA 1: EDA (CHAT)
# ==========================================
with tab_eda:
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

    # Renderizar el historial de conversación
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar=message.get("avatar")):
            st.markdown(message["content"])

    # Entrada de texto del estudiante
    prompt = st.chat_input("Escribe tu consulta jurídica aquí...", key="chat_input_eda")

    if prompt:
        tiempo_actual = time.time()
        tiempo_transcurrido = tiempo_actual - st.session_state.ultimo_envio
        
        if tiempo_transcurrido < 15.0:
            tiempo_espera = int(15.0 - tiempo_transcurrido)
            st.warning(f"⏳ Para garantizar el acceso de todos los miembros del grupo, por favor espera {tiempo_espera} segundos antes de enviar otra consulta.")
        else:
            st.session_state.ultimo_envio = tiempo_actual
            registrar_consulta_local(prompt)
            
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)
            st.session_state.messages.append({"role": "user", "avatar": "👤", "content": prompt})

            with st.chat_message("assistant", avatar="✨"):
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
                        st.session_state.messages.append({"role": "assistant", "avatar": "✨", "content": response.text})
                        
                        st.rerun()
                        
                    except Exception as e:
                        error_str = str(e)
                        clean_error = "Se ha agotado la cuota temporal de consultas de la API. El servicio se restablecerá pronto." if "RESOURCE_EXHAUSTED" in error_str else f"Ocurrió un inconveniente: {error_str}"
                        st.error(clean_error)

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
                df_log = pd.read_csv(ARCHIVO_BITACORA, encoding='utf-8')
                if not df_log.empty:
                    st.dataframe(df_log.iloc[::-1], use_container_width=True)
                    
                    csv_data = df_log.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Descargar Reporte Completo (CSV)",
                        data=csv_data,
                        file_name=f"interacciones_aura_{datetime.now().strftime('%d_%m_%Y')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("El archivo de bitácora está vacío.")
            except Exception as e:
                st.error(f"Error al leer la bitácora local: {e}")
        else:
            st.info("Aún no se registran interacciones en este servidor.")
