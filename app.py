import streamlit as st
from google import genai
from google.genai import types
from datetime import datetime
import pandas as pd
import os
import time
import json
import hashlib
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ==========================================
# 1. CONFIGURACIÓN INICIAL
# ==========================================
st.set_page_config(page_title="Aura - Tutora Virtual", page_icon="✨", layout="centered")

api_key = st.secrets.get("gemini_api_key", None)

ARCHIVO_BITACORA = "consultas_local.csv"
ARCHIVO_CONOCIMIENTO = "vector_store.json"
NOMBRE_HOJA_SHEETS = "Bitacora_Aura"

# ==========================================
# 2. FUNCIÓN PARA REINICIAR CONVERSACIÓN
# ==========================================
def reiniciar_conversacion():
    """Limpia el historial y restaura el mensaje de bienvenida"""
    st.session_state.messages = [
        {
            "role": "assistant",
            "avatar": "✨",
            "content": (
                "✨ ¡Hola! Soy **Aura**, tu tutora académica en Derecho del Trabajo.\n\n"
                "Pertenezco al **Ecosistema Digital de Aprendizaje (EDA)** de esta unidad curricular, "
                "creada y desarrollada por el **Prof. Luis Ignacio Chirinos Campos**.\n\n"
                "Estoy aquí para acompañarte en tu **aprendizaje** con claridad, calidez y rigor jurídico.\n\n"
                "📌 **¿Qué puedo hacer por ti?**\n"
                "- Resolver dudas sobre los contenidos de la unidad\n"
                "- Explicar conceptos jurídicos complejos de forma sencilla\n"
                "- Ayudarte a preparar tus estudios\n"
                "- Orientarte en casos prácticos\n\n"
                "⚠️ **Importante**: No puedo ayudarte a resolver exámenes o evaluaciones. "
                "Mi propósito es apoyar tu **aprendizaje genuino**, no proporcionar atajos académicos.\n\n"
                "Cuéntame, ¿qué tema o consulta académica te trae hoy? 💬"
            )
        }
    ]
    st.session_state.ultimo_envio = 0.0

# ==========================================
# 3. CACHÉ DE RESPUESTAS
# ==========================================
CACHE_RESPUESTAS = {}
CACHE_MAX = 200

def obtener_cache(pregunta: str) -> str:
    clave = hashlib.md5(pregunta.lower().encode()).hexdigest()
    return CACHE_RESPUESTAS.get(clave)

def guardar_cache(pregunta: str, respuesta: str):
    clave = hashlib.md5(pregunta.lower().encode()).hexdigest()
    if len(CACHE_RESPUESTAS) >= CACHE_MAX:
        for k in list(CACHE_RESPUESTAS.keys())[:20]:
            del CACHE_RESPUESTAS[k]
    CACHE_RESPUESTAS[clave] = respuesta

# ==========================================
# 4. CARGA INTELIGENTE DEL CONOCIMIENTO
# ==========================================
@st.cache_data
def cargar_contexto_catedra():
    if os.path.exists(ARCHIVO_CONOCIMIENTO):
        try:
            with open(ARCHIVO_CONOCIMIENTO, "r", encoding="utf-8") as f:
                contenido = f.read()
                if len(contenido) > 2500:
                    return contenido[:2500] + "\n...[Contenido adicional disponible]"
                return contenido
        except Exception:
            return ""
    return ""

CONTEXTO_BASE = cargar_contexto_catedra()

# ==========================================
# 5. FUNCIONES DE REGISTRO
# ==========================================
def conectar_google_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
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
        return sh.sheet1
    except Exception:
        return None

@st.cache_resource
def get_sheets_client():
    return conectar_google_sheets()

def registrar_consulta_dual(texto_pregunta, respuesta_o_error):
    ahora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    p_limpia = str(texto_pregunta).replace("\n", " ").replace("\r", " ").strip()
    r_limpia = str(respuesta_o_error).replace("\n", " ").replace("\r", " ").strip()
    
    try:
        nuevo_registro = pd.DataFrame([{"Cuándo": ahora, "Qué preguntaron": p_limpia, "Respuesta de Aura": r_limpia}])
        if os.path.exists(ARCHIVO_BITACORA):
            nuevo_registro.to_csv(ARCHIVO_BITACORA, mode='a', header=False, index=False, encoding='utf-8')
        else:
            nuevo_registro.to_csv(ARCHIVO_BITACORA, mode='w', header=True, index=False, encoding='utf-8')
    except Exception:
        pass
    
    try:
        hoja = get_sheets_client()
        if hoja:
            hoja.append_row([ahora, p_limpia, r_limpia])
    except Exception:
        pass

# ==========================================
# 6. ESTILOS CSS (FORZADO: fondo blanco absoluto)
# ==========================================
st.markdown("""
    <style>
    /* === FORZAR FONDO BLANCO EN TODO === */
    html, body, .stApp, .stAppViewContainer, .main, .block-container,
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewBlockContainer"],
    [data-testid="stVerticalBlock"],
    [data-testid="stHorizontalBlock"],
    .element-container,
    .stMarkdown,
    .stChatMessage,
    [data-testid="stChatMessage"],
    [data-testid="stChatMessageContent"],
    [data-testid="stChatInput"],
    [data-testid="stChatInputTextArea"],
    div[data-testid="stChatMessage"] {
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
    }
    
    /* === FORZAR TEXTO AZUL OSCURO === */
    p, span, li, label, .stMarkdown, h1, h2, h3, h4, h5, h6,
    .stChatMessage, div, .stTextInput > div > div > input,
    [data-testid="stChatMessage"] p,
    [data-testid="stChatMessage"] span {
        color: #0A2540 !important;
    }
    
    /* === ENCABEZADO === */
    .custom-header {
        text-align: center;
        margin-bottom: 20px;
        padding-bottom: 5px;
        border-bottom: 1px solid #E2E8F0;
        width: 100%;
        background-color: #FFFFFF !important;
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
        margin-bottom: 4px;
    }
    .line-3 {
        color: #4A5568 !important;
        font-size: 1rem;
        font-weight: 400;
        margin-bottom: 4px;
    }
    .line-4 {
        color: #4A5568 !important;
        font-size: 0.9rem;
        font-weight: 400;
        margin-bottom: 8px;
    }
    .line-divider {
        border-bottom: 1px solid #E2E8F0;
        width: 100%;
    }
    
    /* === INPUT DEL CHAT === */
    [data-testid="stChatInput"] > div {
        background-color: #F8FAFC !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 12px !important;
    }
    [data-testid="stChatInput"] textarea {
        color: #0A2540 !important;
        background-color: #F8FAFC !important;
    }
    
    /* === BOTONES === */
    .stButton > button {
        background-color: #0A2540 !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
    }
    .stButton > button:hover {
        background-color: #1A3A5C !important;
    }
    
    /* === PESTAÑAS === */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #F8FAFC;
        padding: 8px;
        border-radius: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 16px;
        background-color: transparent;
        color: #0A2540 !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0A2540 !important;
        color: white !important;
    }
    
    /* === OCULTAR ELEMENTOS DE STREAMLIT === */
    #MainMenu, footer, header, [data-testid="stToolbar"], [data-testid="stDecoration"] {
        visibility: hidden !important;
        display: none !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 7. ENCABEZADO VISUAL
# ==========================================
st.markdown("""
    <div class="custom-header">
        <div class="line-1">✨ Aura</div>
        <div class="line-2">Tutora Académica en Línea</div>
        <div class="line-3">Unidad Curricular: Derecho del Trabajo</div>
        <div class="line-4">Desarrollador: Prof. Luis Ignacio Chirinos Campos</div>
        <div class="line-divider"></div>
    </div>
""", unsafe_allow_html=True)

# ==========================================
# 8. INICIALIZACIÓN
# ==========================================
if "messages" not in st.session_state:
    reiniciar_conversacion()

if "ultimo_envio" not in st.session_state:
    st.session_state.ultimo_envio = 0.0

# ==========================================
# 9. DETECCIÓN DE EVALUACIONES
# ==========================================
PALABRAS_EVALUACION = [
    "examen", "evaluación", "prueba", "cuestionario", "respuesta del examen",
    "dame la respuesta", "cuál es la opción", "qué pongo", "respuesta correcta"
]

def es_intento_evaluacion(pregunta: str) -> bool:
    return any(palabra in pregunta.lower() for palabra in PALABRAS_EVALUACION)

# ==========================================
# 10. SYSTEM INSTRUCTION
# ==========================================
def get_system_instruction():
    return f"""
Eres AURA, tutora de Derecho del Trabajo del EDA creado por el Prof. Luis Ignacio Chirinos Campos.

CONTEXTO DE CÁTEDRA:
{CONTEXTO_BASE}

REGLAS:
- Responde con claridad, calidez y rigor jurídico.
- Máximo 3 párrafos. Usa **negritas** para conceptos clave.
- NO ayudas a resolver exámenes o evaluaciones.
- Si la pregunta es un intento de obtener respuestas de examen, recházala educadamente.
- Cita las fuentes del contexto cuando las uses.
"""

# ==========================================
# 11. PESTAÑAS
# ==========================================
tab_eda, tab_profesor = st.tabs(["💬 EDA", "🔐 Profesor"])

# ==========================================
# 12. PESTAÑA EDA
# ==========================================
with tab_eda:
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("🔄", help="Reiniciar"):
            reiniciar_conversacion()
            st.rerun()
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar=message.get("avatar")):
            st.markdown(message["content"])
    
    prompt = st.chat_input("Escribe tu consulta...")
    
    if prompt:
        if time.time() - st.session_state.ultimo_envio < 15:
            st.warning("⏳ Espera 15 segundos.")
        else:
            st.session_state.ultimo_envio = time.time()
            
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)
            st.session_state.messages.append({"role": "user", "avatar": "👤", "content": prompt})
            
            with st.chat_message("assistant", avatar="✨"):
                if es_intento_evaluacion(prompt):
                    respuesta = "📚 **Lo siento, no puedo ayudarte con evaluaciones.** Estoy para apoyar tu aprendizaje."
                    st.markdown(respuesta)
                    st.session_state.messages.append({"role": "assistant", "avatar": "✨", "content": respuesta})
                    registrar_consulta_dual(prompt, "[BLOQUEADO]")
                    st.stop()
                
                cache = obtener_cache(prompt)
                if cache:
                    st.markdown(cache)
                    st.session_state.messages.append({"role": "assistant", "avatar": "✨", "content": cache})
                    registrar_consulta_dual(prompt, "[CACHÉ]")
                    st.rerun()
                
                if not api_key:
                    st.error("Error: API Key no configurada.")
                else:
                    try:
                        client = genai.Client(api_key=api_key)
                        history = []
                        for msg in st.session_state.messages[-4:]:
                            role = "model" if msg["role"] == "assistant" else "user"
                            history.append(types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])]))
                        
                        config = types.GenerateContentConfig(
                            system_instruction=get_system_instruction(),
                            temperature=0.2,
                            max_output_tokens=1024
                        )
                        
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=history,
                            config=config
                        )
                        
                        respuesta_texto = response.text
                        st.markdown(respuesta_texto)
                        st.session_state.messages.append({"role": "assistant", "avatar": "✨", "content": respuesta_texto})
                        guardar_cache(prompt, respuesta_texto)
                        registrar_consulta_dual(prompt, respuesta_texto)
                        
                    except Exception as e:
                        error_msg = "📚 Aura está recibiendo muchas consultas. Espera un momento." if "RESOURCE_EXHAUSTED" in str(e) else f"⚠️ Error: {str(e)[:150]}"
                        st.error(error_msg)
                        registrar_consulta_dual(prompt, error_msg)

# ==========================================
# 13. PESTAÑA PROFESOR
# ==========================================
with tab_profesor:
    st.subheader("Bitácora de Consultas")
    clave = st.text_input("Credencial docente:", type="password")
    
    if clave == "UCLA2026":
        st.success("Acceso Verificado")
        if os.path.exists(ARCHIVO_BITACORA):
            df = pd.read_csv(ARCHIVO_BITACORA, encoding='utf-8')
            if not df.empty:
                st.dataframe(df.iloc[::-1])
                st.download_button("Descargar CSV", df.to_csv(index=False).encode('utf-8'), "bitacora.csv")
            else:
                st.info("Sin registros.")
        else:
            st.info("Sin registros.")
    elif clave:
        st.error("Credencial incorrecta")
