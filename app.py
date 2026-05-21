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
                "⚠️ **Importante**: No puedo ayudarte a resolver exámenes o evaluaciones.\n\n"
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
# 4. CARGA DEL CONOCIMIENTO
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
# 6. ESTILOS CSS (fondo blanco total)
# ==========================================
st.markdown("""
    <style>
    /* Fondo blanco absoluto */
    html, body, .stApp, .stAppViewContainer, .main, .block-container,
    [data-testid="stAppViewContainer"], .stChatMessage,
    [data-testid="stChatMessage"], [data-testid="stChatMessageContent"] {
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
    }
    
    /* Texto azul oscuro */
    p, span, li, label, .stMarkdown, h1, h2, h3, h4, div {
        color: #0A2540 !important;
    }
    
    /* Encabezado */
    .custom-header {
        text-align: center;
        margin-bottom: 25px;
        padding-bottom: 10px;
        border-bottom: 2px solid #0A2540;
    }
    .line-1 {
        font-size: 2.5rem;
        font-weight: 700;
        color: #0A2540 !important;
    }
    .line-2 {
        font-size: 1.2rem;
        font-weight: 600;
        color: #1A3A5C !important;
    }
    .line-3 {
        font-size: 0.95rem;
        color: #4A5568 !important;
    }
    .line-4 {
        font-size: 0.85rem;
        color: #4A5568 !important;
        margin-top: 5px;
    }
    
    /* Input del chat */
    [data-testid="stChatInput"] > div {
        background-color: #F8FAFC !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 12px !important;
    }
    
    /* Botón de reinicio */
    .stButton > button {
        background-color: #0A2540 !important;
        color: white !important;
        border-radius: 8px !important;
    }
    
    /* Ocultar elementos */
    #MainMenu, footer, header, [data-testid="stToolbar"] {
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
- Cita las fuentes del contexto.
"""

# ==========================================
# 11. INTERFAZ DE CHAT (sin pestañas visibles)
# ==========================================
# Botón de reinicio
col1, col2 = st.columns([6, 1])
with col2:
    if st.button("🔄", help="Reiniciar conversación"):
        reiniciar_conversacion()
        st.rerun()

# Mostrar mensajes
for message in st.session_state.messages:
    with st.chat_message(message["role"], avatar=message.get("avatar")):
        st.markdown(message["content"])

# Input del chat
prompt = st.chat_input("Escribe tu consulta jurídica aquí...")

if prompt:
    tiempo_actual = time.time()
    if tiempo_actual - st.session_state.ultimo_envio < 15:
        st.warning(f"⏳ Espera {int(15 - (tiempo_actual - st.session_state.ultimo_envio))} segundos.")
    else:
        st.session_state.ultimo_envio = tiempo_actual
        
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "avatar": "👤", "content": prompt})
        
        with st.chat_message("assistant", avatar="✨"):
            # Bloqueo de evaluaciones
            if es_intento_evaluacion(prompt):
                respuesta = "📚 **Lo siento, no puedo ayudarte con evaluaciones.** Estoy para apoyar tu aprendizaje genuino. ¿Tienes alguna duda sobre el contenido?"
                st.markdown(respuesta)
                st.session_state.messages.append({"role": "assistant", "avatar": "✨", "content": respuesta})
                registrar_consulta_dual(prompt, "[BLOQUEADO]")
                st.stop()
            
            # Verificar caché
            cache = obtener_cache(prompt)
            if cache:
                st.markdown(cache)
                st.session_state.messages.append({"role": "assistant", "avatar": "✨", "content": cache})
                registrar_consulta_dual(prompt, "[CACHÉ]")
                st.rerun()
            
            # Llamar a Gemini
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
# 12. ACCESO OCULTO PARA EL PROFESOR (URL secreta)
# ==========================================
# Para ver la bitácora, añade "?admin=true" al final de la URL
# Ejemplo: https://tu-app.streamlit.app/?admin=true

import urllib.parse
query_params = st.query_params

if query_params.get("admin") == ["true"]:
    st.markdown("---")
    st.subheader("📋 Panel del Profesor")
    clave = st.text_input("Credencial:", type="password")
    
    if clave == "UCLA2026":
        st.success("Acceso concedido")
        if os.path.exists(ARCHIVO_BITACORA):
            df = pd.read_csv(ARCHIVO_BITACORA, encoding='utf-8')
            if not df.empty:
                st.dataframe(df.iloc[::-1], use_container_width=True)
                st.download_button("📥 Descargar CSV", df.to_csv(index=False).encode('utf-8'), "bitacora.csv")
            else:
                st.info("Sin registros")
        else:
            st.info("Sin registros")
    elif clave:
        st.error("Credencial incorrecta")
