import streamlit as st
import time
import datetime
from google import genai
from google.genai import types
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. CONFIGURACIÓN DE LA PÁGINA INDEPENDIENTE
st.set_page_config(page_title="Justa - Tutora Virtual", page_icon="⚖️", layout="centered")

# 2. ESTILOS CSS AVANZADOS (Fondo limpio, sin marcos de alerta innecesarios)
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

# 3. CONEXIÓN A BASE DE DATOS Y API KEY
api_key = st.secrets.get("gemini_api_key", None)
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    conn = None

# 4. CAPTURA DEL ESTUDIANTE Y SECCIÓN DESDE LA LTI DE MOODLE
query_params = st.query_params
moodle_user = query_params.get("estudiante", None)
moodle_section = query_params.get("seccion", None)

if "nombre_estudiante" not in st.session_state:
    st.session_state.nombre_estudiante = moodle_user if moodle_user else None

if "seccion_estudiante" not in st.session_state:
    if moodle_section:
        # Homologar la entrada de Moodle a mayúsculas por si viene como n01 o m03
        sec_upper = str(moodle_section).strip().upper()
        # Normalizar formatos cortos como N1 o M3 a sus nombres oficiales de tabla
        if sec_upper == "N1":
            sec_upper = "N01"
        elif sec_upper == "M3":
            sec_upper = "M03"
        st.session_state.seccion_estudiante = sec_upper
    else:
        st.session_state.seccion_estudiante = None

# Mecanismo de contingencia fuera de Moodle
if st.session_state.nombre_estudiante is None or st.session_state.seccion_estudiante is None:
    st.info("Bienvenido al espacio de tutoría virtual de Derecho del Trabajo.")
    
    with st.form("registro_contingencia"):
        identificacion = st.text_input("Por favor, introduce tu nombre y apellido:")
        # Opciones restringidas estrictamente a N01 y M03
        opciones_seccion = ["Selecciona tu sección...", "N01", "M03"]
        sec_seleccionada = st.selectbox("Selecciona tu sección académica:", opciones_seccion)
        boton_entrar = st.form_submit_button("Comenzar Tutoría")
        
        if boton_entrar:
            if identificacion.strip() == "":
                st.error("Debes ingresar tu nombre.")
            elif sec_seleccionada == "Selecciona tu sección...":
                st.error("Debes seleccionar una sección válida.")
            else:
                st.session_state.nombre_estudiante = identificacion.strip().replace(" ", "_")
                st.session_state.seccion_estudiante = sec_seleccionada
                st.rerun()
    st.stop()

# 5. INICIALIZACIÓN DE VARIABLES DE SESIÓN
if "messages" not in st.session_state:
    welcome_text = (
        "Hola. Soy Justa, tutora académica virtual de la asignatura Derecho del Trabajo, "
        "gestionada por Luis Ignacio Chirinos Campos. Te doy la bienvenida a este espacio de aprendizaje. "
        "Cuento con la preparación para brindarte orientación y acompañamiento en todo lo relacionado con el "
        "contenido académico de nuestra unidad curricular, basándome estrictamente en los documentos "
        "y materiales de estudio autorizados. Te invito a utilizar esta herramienta con responsabilidad e "
        "integridad en tu proceso de formación. Aquí puedes estudiar, repasar y aclarar cualquier duda o "
        "inquietun que tengas sobre los temas de la materia."
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

# 7. PROCESAMIENTO DE CONSULTAS
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
                respuesta_texto = ""
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
                    
                except Exception as e:
                    if "RESOURCE_EXHAUSTED" in str(e):
                        respuesta_texto = "La plataforma académica está procesando un alto volumen de consultas. Por favor, espera 30 segundos y presiona enviar nuevamente."
                    else:
                        respuesta_texto = "Lo siento, ha ocurrido un inconveniente al procesar tu consulta en el modelo de lenguaje."
                    st.error(respuesta_texto)
                    st.session_state.messages.append({"role": "assistant", "content": respuesta_texto})

                # AUDITORÍA EN GOOGLE SHEETS EN SEGUNDO PLANO
                if conn is not None and respuesta_texto != "":
                    try:
                        ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        # 1. Leer el estado actual de la hoja para anexar los renglones
                        data_existente = conn.read(worksheet="Sheet1", ttl=0)
                        df_existente = pd.DataFrame(data_existente)
                        
                        # 2. Estructurar la fila con los nombres de columna idénticos a tu hoja
                        nueva_fila = pd.DataFrame([{
                            "Fecha/Hora": ahora,
                            "Estudiante": st.session_state.nombre_estudiante,
                            "sección": st.session_state.seccion_estudiante,
                            "Pregunta": prompt,
                            "Respuesta_IA": respuesta_texto
                        }])
                        
                        # 3. Combinar datos previos con el nuevo registro
                        df_actualizado = pd.concat([df_existente, nueva_fila], ignore_index=True)
                        
                        # 4. Actualizar la hoja de cálculo de Google
                        conn.update(worksheet="Sheet1", data=df_actualizado)
                    except Exception:
                        pass
