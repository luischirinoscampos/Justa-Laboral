import streamlit as st
import time
import datetime
from google import genai
from google.genai import types
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. CONFIGURACIÓN DE LA PÁGINA INDEPENDIENTE
st.set_page_config(page_title="Justa - Tutora Virtual", page_icon="⚖️", layout="centered")

# 2. ESTILOS CSS AVANZADOS (Fondo limpio y alertas simétricas)
st.markdown("""
    <style>
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], 
    [data-testid="stSidebar"], [data-testid="stBottomBlockContainer"], 
    [data-testid="stBottom"], div[class^="st-emotion-cache"], .stChatMessage {
        background-color: #FFFFFF !important;
    }
    .main-title {
        font-family: 'Inter', sans-serif;
        color: #0A2540 !important;
        font-weight: 700;
        margin-bottom: 5px;
    }
    .sub-caption {
        font-family: 'Inter', sans-serif;
        color: #4A5568 !important;
        font-size: 0.95rem;
        margin-bottom: 25px;
        border-bottom: 1px solid #E2E8F0;
        padding-bottom: 15px;
    }
    p, span, li, label, .stMarkdown, h1, h2, h3 {
        color: #1A202C !important;
    }
    div[role="alert"] {
        width: 100% !important;
        border-radius: 8px !important;
        border: 1px solid #FCA5A5 !important;
        background-color: #FEF2F2 !important;
        padding: 12px 16px !important;
    }
    [data-testid="stChatInput"] {
        background-color: #FFFFFF !important;
        padding: 10px 0px !important;
    }
    [data-testid="stChatInput"] > div {
        background-color: #F8FAFC !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 8px !important;
    }
    [data-testid="stChatInput"] textarea {
        color: #0A2540 !important;
    }
    #MainMenu, footer, header, [data-testid="stDecoration"] { visibility: hidden; display: none; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">⚖️ Justa: Tutora Académica Virtual</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-caption">Asignatura: Derecho del Trabajo | Profesor Luis Ignacio Chirinos Campos</p>', unsafe_allow_html=True)

# 3. CONEXIÓN A BASE DE DATOS (GOOGLE SHEETS) Y API KEY
api_key = st.secrets.get("gemini_api_key", None)
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    conn = None

# 4. CAPTURA DEL ESTUDIANTE ENVIADO DESDE LA LTI DE MOODLE
query_params = st.query_params
moodle_user = query_params.get("estudiante", None)

if "nombre_estudiante" not in st.session_state:
    if moodle_user:
        st.session_state.nombre_estudiante = moodle_user
    else:
        st.session_state.nombre_estudiante = None

# Mecanismo de contingencia si se ingresa fuera de Moodle
if st.session_state.nombre_estudiante is None:
    st.info("Bienvenido al espacio de tutoría virtual.")
    identificacion = st.text_input("Por favor, introduce tu nombre y apellido para comenzar:")
    if identificacion:
        st.session_state.nombre_estudiante = identificacion.strip().replace(" ", "_")
        st.rerun()
    st.stop()

# 5. INICIALIZACIÓN DE VARIABLES EXCLUSIVAS DE SESIÓN
if "messages" not in st.session_state:
    welcome_text = (
        "Hola. Soy Justa, tutora académica virtual de la asignatura Derecho del Trabajo, "
        "gestionada por Luis Ignacio Chirinos Campos. Te doy la bienvenida a este espacio de aprendizaje. "
        "Cuento con la preparación para brindarte orientación y acompañamiento en todo lo relacionado con el "
        "contenido académico de nuestra unidad curricular, basándome estrictamente en los documentos "
        "y materiales de estudio autorizados. Te invito a utilizar esta herramienta con responsabilidad e "
        "integridad en tu proceso de formación. Aquí puedes estudiar, repasar y aclarar cualquier duda o "
        "inquietud que tengas sobre los temas de la materia."
    )
    st.session_state.messages = [{"role": "assistant", "content": welcome_text}]

if "last_request_time" not in st.session_state:
    st.session_state.last_request_time = 0.0

if "api_client" not in st.session_state and api_key:
    st.session_state.api_client = genai.Client(api_key=api_key)

system_instruction = (
    "Eres 'Justa', una tutora académica experta en Derecho del Trabajo para la Universidad Centroccidental "
    "Lisandro Alvarado (UCLA). Tu rol es guiar a las y los estudiantes de forma pedagógica, rigurosa y clara, "
    "utilizando un lenguaje neutral e institucional. Responde con base en la doctrina jurídica y la normativa laboral vigente."
)

# 6. MOSTRAR HISTORIAL LOCAL DEL ESTUDIANTE
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 7. PROCESAMIENTO Y AUDITORÍA DE CONSULTAS
if prompt := st.chat_input("Escribe tu consulta jurídica aquí..."):
    current_time = time.time()
    time_passed = current_time - st.session_state.last_request_time
    COOLDOWN_PERIOD = 3.0 
    
    if time_passed < COOLDOWN_PERIOD:
        st.warning("Por favor, procesa tus consultas con calma. Espera unos segundos antes de enviar otra pregunta.")
    else:
        st.session_state.last_request_time = current_time
        
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            if "api_client" not in st.session_state:
                st.error("Error de configuración: La clave de acceso de la API no está disponible en el servidor.")
            else:
                try:
                    native_history = []
                    filtrado = [m for m in st.session_state.messages[:-1] if "Derecho del Trabajo" not in m["content"]]
                    
                    for msg in filtrado[-2:]:
                        role_mapped = "model" if msg["role"] == "assistant" else "user"
                        native_history.append(
                            types.Content(role=role_mapped, parts=[types.Part.from_text(text=msg["content"])])
                        )
                    
                    config = types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.2,
                    )
                    
                    chat = st.session_state.api_client.chats.create(
                        model='gemini-2.5-flash-lite',
                        config=config,
                        history=native_history
                    )
                    
                    response = chat.send_message(prompt)
                    respuesta_texto = response.text
                    
                    st.markdown(respuesta_texto)
                    st.session_state.messages.append({"role": "assistant", "content": respuesta_texto})
                    
                    # REGISTRO DE MÉTRICA EN GOOGLE SHEETS (Sintaxis simplificada de inserción)
                    if conn is not None:
                        ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        nuevo_registro = pd.DataFrame([{
                            "Fecha/Hora": ahora,
                            "Estudiante": st.session_state.nombre_estudiante,
                            "Pregunta": prompt,
                            "Respuesta_IA": respuesta_texto
                        }])
                        
                        try:
                            # Intenta leer los datos existentes, si falla o está vacía inicializa el DataFrame
                            datos_actuales = conn.read()
                            datos_actualizados = pd.concat([datos_actuales, nuevo_registro], ignore_index=True)
                        except Exception:
                            datos_actualizados = nuevo_registro
                        
                        # Actualización explícita utilizando el método nativo de la conexión de Streamlit
                        conn.update(data=datos_actualizados)
                        
                except Exception as e:
                    error_str = str(e)
                    if "RESOURCE_EXHAUSTED" in error_str:
                        clean_error = "La plataforma académica está procesando un alto volumen de consultas. Por favor, espera 30 segundos y presiona enviar nuevamente."
                        st.error(clean_error)
                    else:
                        clean_error = "Nota: No se pudo procesar la solicitud en este momento de forma correcta."
                        st.error(clean_error)
                    st.session_state.messages.append({"role": "assistant", "content": clean_error})
