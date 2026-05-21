import streamlit as st
from google import genai
from google.genai import types
from datetime import datetime
import pandas as pd
import os
import time
import json

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Aura - Tutora Virtual", page_icon="✨", layout="centered")

# Recuperación de la API Key de Gemini desde los secretos
api_key = st.secrets.get("gemini_api_key", None)

# RUTAS DE ARCHIVOS LOCALES
ARCHIVO_BITACORA = "consultas_local.csv"
ARCHIVO_CONOCIMIENTO = "vector_store.json"

def registrar_consulta_local(texto_pregunta, respuesta_aura):
    """Guarda la consulta en un archivo CSV local con estructura estricta de dos columnas"""
    try:
        ahora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        # Integración compacta de la pregunta y la respuesta en una sola cadena de texto
        detalle_integrado = f"PREGUNTA: {texto_pregunta} | RESPUESTA DE AURA: {respuesta_aura}"
        
        nuevo_registro = pd.DataFrame([{"Cuándo": ahora, "Detalle de la Consulta": detalle_integrado}])
        
        if os.path.exists(ARCHIVO_BITACORA):
            nuevo_registro.to_csv(ARCHIVO_BITACORA, mode='a', header=False, index=False, encoding='utf-8')
        else:
            nuevo_registro.to_csv(ARCHIVO_BITACORA, mode='w', header=True, index=False, encoding='utf-8')
    except Exception:
        pass

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

# Cargar la base de conocimiento en memoria de manera optimizada
CONTEXTO_LEGAL_CATEDRA = cargar_contexto_catedra()

# 2. INYECCIÓN DE ESTILOS CSS REFORZADOS
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
        overflow-x: hidden !important;
    }
    
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }
    
    .stApp, .stChatMessage {
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
    }
    [data-testid="stHeader"] { background-color: transparent !important; }
    div[data-testid="stToolbar"] { visibility: hidden; display: none; }
    #MainMenu, footer, [data-testid="stDecoration"] { visibility: hidden; display: none; }
    
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

# Inicialización obligatoria del historial antes de las pestañas
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "avatar": "✨",
            "content": (
                "### ¡Bienvenido(a)!\n\n"
                "Hola. Soy **Aura**, tutora académica en línea del EDA de **Derecho del Trabajo**, "
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
# ENCABEZADO
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
    system_instruction = f"""
Eres Aura, una tutora académica en línea experta en Derecho del Trabajo para el DCEE de la Universidad Centroccidental Lisandro Alvarado (UCLA).
Tu comunicación debe caracterizarse por una claridad respetuosa y una honestidad total.

CONTEXTO DE TU DESARROLLO E IDENTIDAD:
- Fuiste desarrollada, programada y configurada exclusivamente por el profesor y abogado Luis Ignacio Chirinos Campos, quien es tu creador y el docente ordinario de esta asignatura.
- Si alguien te pregunta por tu origen, creador, desarrollador o profesor de la materia, debes reconocer con orgullo, respeto y claridad institucional que eres una creación tecnológica del profesor Luis Ignacio Chirinos Campos para el beneficio académico del estudiantado, y perteneces al ecosistema digital de aprendizaje de la unidad curricular.

PAUTAS DE COMPORTAMIENTO Y PEDAGOGÍA:
- Tu propósito es guiar a quienes estudian de forma pedagógica, rigurosa aunque amable, clara, cálida y cercana.
- Utiliza siempre un lenguaje neutral, inclusivo y formal, adecuado para el ámbito de la educación universitaria virtual o a distancia.
- Evita respuestas genéricas de asistente virtual de internet. Eres una herramienta académica del Ecosistema Digital de Aprendizaje (EDA).

FUENTE PRINCIPAL DE CONOCIMIENTO (REPOSITORIO DE LA CÁTEDRA):
Utiliza de forma obligatoria y prioritaria el siguiente contenido extraído de las guías, ejercicios resueltos, Constitución y leyes cargadas por el docente para estructurar tus respuestas:
=========================================
{CONTEXTO_LEGAL_CATEDRA}
=========================================

DIRECTRICES DE RESPUESTA:
1. Responde basándote estrictamente en la doctrina jurídica laboral, la normativa legal venezolana vigente (CRBV, LOTTT) y el repositorio de la cátedra suministrado arriba. Citando las fuentes de forma precisa cuando corresponda.
2. Si la respuesta a la duda o planteamiento del estudiante no se encuentra en el repositorio proporcionado ni se relaciona directamente con los objetivos académicos de la asignatura, indícalo abiertamente con honestidad académica y reorienta la conversación hacia los temas de estudio laboral.
"""

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
                        for msg in st.session_state.messages:
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
                            contents=history_contents, 
                            config=config
                        )
                        
                        respuesta_texto = response.text
                        st.markdown(respuesta_texto)
                        st.session_state.messages.append({"role": "assistant", "avatar": "✨", "content": respuesta_texto})
                        
                        # El registro local ocurre aquí, capturando ambas partes en la estructura unificada de dos columnas
                        registrar_consulta_local(prompt, respuesta_texto)
                        
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
                    # Muestra las dos columnas del dataframe: 'Cuándo' y 'Detalle de la Consulta'
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
                st.error(f"Error al leer la bitácora local de forma estructurada: {e}")
                st.info("Nota técnica: Si el archivo previo quedó corrupto por la estructura antigua, bórrelo del servidor para que el nuevo sistema lo regenere correctamente desde cero.")
        else:
            st.info("Aún no se registran interacciones en este servidor.")
