import streamlit as st
import time
from google import genai
from google.genai import types

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Justa - Tutora Virtual", page_icon="⚖️", layout="centered")

# 2. INYECCIÓN DE ESTILOS CSS AVANZADOS (Alineación, fondo limpio y alertas simétricas)
st.markdown("""
    <style>
    /* Forzar fondo blanco absoluto en toda la infraestructura */
    .stApp, 
    [data-testid="stAppViewContainer"], 
    [data-testid="stHeader"], 
    [data-testid="stSidebar"],
    [data-testid="stBottomBlockContainer"],
    [data-testid="stBottom"],
    div[class^="st-emotion-cache"],
    .stChatMessage {
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
    }
    
    /* Estilización tipográfica institucional (Azul Oscuro) */
    .main-title {
        font-family: 'Inter', -apple-system, sans-serif;
        color: #0A2540 !important;
        font-weight: 700;
        margin-bottom: 5px;
    }
    
    .sub-caption {
        font-family: 'Inter', -apple-system, sans-serif;
        color: #4A5568 !important;
        font-size: 0.95rem;
        margin-bottom: 25px;
        border-bottom: 1px solid #E2E8F0;
        padding-bottom: 15px;
    }

    /* Color de texto general para alta legibilidad */
    p, span, li, label, .stMarkdown, h1, h2, h3 {
        color: #1A202C !important;
    }

    /* ESTABILIZACIÓN DE RECUADROS DE ALERTA Y ERROR */
    [data-testid="stNotification"],
    div[data-inner-alert-container="true"],
    .stAlert {
        width: 100% !important;
        box-sizing: border-box !important;
        margin: 10px 0px !important;
        padding: 4px !important;
    }
    
    div[role="alert"] {
        width: 100% !important;
        border-radius: 8px !important;
        box-sizing: border-box !important;
        border: 1px solid #FCA5A5 !important;
        background-color: #FEF2F2 !important;
        padding: 12px 16px !important;
    }

    /* ESTABILIZACIÓN Y SIMETRÍA DEL CUADRO DE CONSULTA */
    [data-testid="stChatInput"] {
        background-color: #FFFFFF !important;
        padding: 10px 0px !important;
    }

    /* Marco perimetral interno de la caja de texto */
    [data-testid="stChatInput"] > div {
        background-color: #F8FAFC !important;
        background: #F8FAFC !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 8px !important;
        padding: 4px 8px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
    }

    /* Ajuste estricto del área de escritura */
    [data-testid="stChatInput"] textarea {
        background-color: transparent !important;
        background: transparent !important;
        color: #0A2540 !important;
        font-family: 'Inter', sans-serif !important;
        border: none !important;
        box-shadow: none !important;
        margin: 0 !important;
        padding: 8px 4px !important;
        resize: none !important;
    }

    /* Alineación y estilo simétrico del botón de envío (Flecha) */
    [data-testid="stChatInput"] button {
        color: #0A2540 !important;
        background-color: transparent !important;
        border: none !important;
        margin: 0 !important;
        padding: 0px 4px !important;
        display: flex !important;
        align-items: center !important;
    }

    /* Eliminar componentes de desarrollo en la interfaz */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stDecoration"] {display: none;}
    </style>
""", unsafe_allow_html=True)

# 3. ENCABEZADO DE LA INTERFAZ INSTITUCIONAL
st.markdown('<h1 class="main-title">⚖️ Justa: Tutora Académica Virtual</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-caption">Asignatura: Derecho del Trabajo | Profesor Luis Ignacio Chirinos Campos</p>', unsafe_allow_html=True)

# 4. INICIALIZACIÓN DE LA API Y MANEJO DE SESIÓN
if "gemini_api_key" in st.secrets:
    api_key = st.secrets["gemini_api_key"]
else:
    api_key = None

if "last_request_time" not in st.session_state:
    st.session_state.last_request_time = 0.0

welcome_text = (
    "Hola. Soy Justa, tutora académica virtual de la asignatura Derecho del Trabajo, "
    "gestionada por Luis Ignacio Chirinos Campos. Te doy la bienvenida a este espacio de aprendizaje. "
    "Cuento con la preparación para brindarte orientación y acompañamiento en todo lo relacionado con el "
    "contenido académico de nuestra unidad curricular, basándome estrictamente en los documentos "
    "y materiales de estudio autorizados. Te invito a utilizar esta herramienta con responsibility e "
    "integridad en tu proceso de formación. Aquí puedes estudiar, repasar y aclarar cualquier duda o "
    "inquietud que tengas sobre los temas de la materia."
)

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": welcome_text}]

system_instruction = (
    "Eres 'Justa', una tutora académica experta en Derecho del Trabajo para la Universidad Centroccidental "
    "Lisandro Alvarado (UCLA). Tu rol es guiar a las y los estudiantes de forma pedagógica, rigurosa y clara, "
    "utilizando un lenguaje neutral e institucional. Responde con base en la doctrina jurídica y la normativa laboral vigente."
)

# 5. DESPLIEGUE DEL HISTORIAL DE CONVERSACIÓN
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 6. ENTRADA DE USUARIO Y VALIDACIÓN DE TIEMPO
if prompt := st.chat_input("Escribe tu consulta jurídica aquí..."):
    current_time = time.time()
    time_passed = current_time - st.session_state.last_request_time
    COOLDOWN_PERIOD = 5.0 
    
    if time_passed < COOLDOWN_PERIOD:
        time_to_wait = int(COOLDOWN_PERIOD - time_passed) + 1
        st.warning(f"Por favor, procesa tus consultas con calma. Espera {time_to_wait} segundos antes de enviar otra pregunta.")
    else:
        st.session_state.last_request_time = current_time
        
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            if not api_key:
                error_msg = "Error: No se encontró la configuración de la API Key ('gemini_api_key') en los Secrets de Streamlit."
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
            else:
                try:
                    # Inicializar el cliente nativo
                    client = genai.Client(api_key=api_key)
                    
                    # Formatear el historial de forma nativa para el motor de chats de Google
                    native_history = []
                    # Omitir el primer mensaje de bienvenida para no gastar tokens
                    active_msgs = [m for m in st.session_state.messages[:-1] if m["content"] != welcome_text]
                    
                    # Conservar únicamente las últimas 2 interacciones (4 mensajes) para un consumo mínimo
                    for msg in active_msgs[-4:]:
                        role_mapped = "model" if msg["role"] == "assistant" else "user"
                        native_history.append(
                            types.Content(role=role_mapped, parts=[types.Part.from_text(text=msg["content"])])
                        )
                    
                    # Configuración del modelo
                    config = types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.3,
                    )
                    
                    # Crear el canal de chat nativo con el historial limpio
                    chat = client.chats.create(
                        model='gemini-2.5-flash',
                        config=config,
                        history=native_history
                    )
                    
                    # Enviar el mensaje actual
                    response = chat.send_message(prompt)
                    
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                    
                except Exception as e:
                    error_str = str(e)
                    if "RESOURCE_EXHAUSTED" in error_str:
                        clean_error = "Se ha alcanzado el límite temporal de la cuota gratuita. Por favor, aguarda 60 segundos y vuelve a enviar tu consulta."
                        st.error(clean_error)
                    else:
                        clean_error = f"Ocurrió un inconveniente al procesar la solicitud: {error_str}"
                        st.error(clean_error)
                    st.session_state.messages.append({"role": "assistant", "content": clean_error})
