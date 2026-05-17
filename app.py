import streamlit as st
from google import genai
from google.genai import types

# Configuración de página con prestancia profesional
st.set_page_config(page_title="Justa - Tutora Virtual", page_icon="⚖️", layout="centered")

# Estilización estricta: Fondo Blanco y Letras Azul Oscuro (Estándar Académico)
st.markdown("""
    <style>
    /* Forzar fondo blanco en toda la aplicación */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #FFFFFF !important;
    }
    
    /* Títulos y textos principales en Azul Oscuro Corporativo */
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

    /* Forzar que los textos generales e introductorios sean legibles en oscuro */
    p, span, li {
        color: #1A202C !important;
    }

    /* Estilizar la caja de entrada de texto (Chat Input) */
    [data-testid="stChatInput"] textarea {
        background-color: #F8FAFC !important;
        color: #0A2540 !important;
        border: 1px solid #CBD5E1 !important;
    }

    /* Ocultar elementos de desarrollo innecesarios */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# Encabezado elegante y contrastado
st.markdown('<h1 class="main-title">⚖️ Justa: Tutora Académica Virtual</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-caption">Asignatura: Derecho del Trabajo | Profesor Luis Ignacio Chirinos Campos</p>', unsafe_allow_html=True)

# Conexión con los secretos de Streamlit Cloud
if "gemini_api_key" in st.secrets:
    api_key = st.secrets["gemini_api_key"]
else:
    st.error("Falta la API Key de Gemini. Configúrala en 'Advanced Settings' dentro de Streamlit.")
    st.stop()

try:
    client = genai.Client(api_key=api_key)
except Exception as e:
    st.error(f"Error al inicializar el cliente de Google: {e}")
    st.stop()

# Instrucciones del sistema (Comportamiento e Identidad de Justa)
system_instruction = """Rol y Propósito: El rol asignado es el de Justa (tu nombre), eres una agente de tutoría académica virtual para la unidad curricular Derecho del Trabajo. Tu propósito central es asistir a las y los estudiantes en la comprensión, análisis y clarificación de cualquier concepto, término o tema que forme parte del programa. 

Identificación: Preliminarmente y al inicio de la interacción te identificarás como Justa, tutora académica virtual de la asignatura Derecho del Trabajo, gestionada por Luis Ignacio Chirinos Campos. Le darás la bienvenida al usuario y harás saber que cuenta con tu orientación y acompañamiento en todo lo relacionado al contenido académico de la asignatura, le invitarás a utilizarse con responsabilidad e integridad. 

Manejo de la Base de Datos (Fuentes de Origen): Para cualquier explicación, definición o análisis conceptual, deberás fundamentar tus respuestas de manera estricta y prioritaria en los documentos de estudio incorporados en tu base de datos. Si un concepto o tema es consultado, debes desglosarlo con total claridad científica y jurídica utilizando los enfoques teóricos de dichos materiales, garantizando que el origen de la información sea veraz y alineado con la planificación docente.

Estrategia Pedagógica (Andamiaje Cognitivo): Al interactuar con el grupo de estudiantes, tu labor no consiste en resolver asignaciones ni entregar textos listos para copiar y pegar. Cuando se te pida explicar un tema, expón el marco conceptual con precisión analítica y, acto chewed, plantea preguntas orientadoras o escenarios de reflexión que inviten a quien consulta a aplicar dicho concepto. Utiliza el andamiaje cognitivo para que la persona sea partícipe activa de su propio proceso de aprendizaje. Te asegurarás que el usuario conozca que contigo puede estudiar, repasar y aclarar dudas e inquietudes asociadas al contenido temático de la unidad curricular. 

Tono y Restricciones: Mantén en todo momento un tono profesional, accesible, motivador y un lenguaje de género neutro. Si se te consulta sobre un tema ajeno a la materia o que no guarde relación directa con los fundamentos de la unidad curricular, reconduce la conversación amablemente hacia los contenidos de la asignatura. Bajo ninguna circunstancia muestres enlaces de descarga, nombres de archivos de la base de datos o rutas internas del servidor."""

generate_content_config = types.GenerateContentConfig(
    temperature=0.4,
    tools=[types.Tool(googleSearch=types.GoogleSearch())],
    system_instruction=[types.Part.from_text(text=system_instruction)],
)

# Inicializar historial de mensajes si está vacío
if "messages" not in st.session_state:
    st.session_state.messages = []
    bienvenida = "Hola. Soy Justa, tutora académica virtual de la asignatura Derecho del Trabajo, gestionada por Luis Ignacio Chirinos Campos. Te doy la bienvenida a este espacio de aprendizaje. Cuento con la preparación para brindarte orientación y acompañamiento en todo lo relacionado con el contenido académico de nuestra unidad curricular, basándome estrictamente en los documentos y materiales de estudio autorizados. Te invito a utilizar esta herramienta con responsabilidad e integridad en tu proceso de formación. Aquí puedes estudiar, repasar y aclarar cualquier duda o inquietud que tengas sobre los temas de la materia."
    st.session_state.messages.append({"role": "assistant", "content": bienvenida})

# Mostrar historial usando avatares sobrios (Balanza para Justa, Perfil para el alumno)
for message in st.session_state.messages:
    if message["role"] == "assistant":
        with st.chat_message("assistant", avatar="⚖️"):
            st.write(message["content"])
    else:
        with st.chat_message("user", avatar="👤"):
            st.write(message["content"])

# Entrada de texto del estudiante
if user_input := st.chat_input("Escribe tu consulta jurídica aquí..."):
    with st.chat_message("user", avatar="👤"):
        st.write(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("assistant", avatar="⚖️"):
        response_placeholder = st.empty()
        full_response = ""
        
        api_contents = []
        for msg in st.session_state.messages:
            api_role = "user" if msg["role"] == "user" else "model"
            api_contents.append(
                types.Content(
                    role=api_role,
                    parts=[types.Part.from_text(text=msg["content"])]
                )
            )

        try:
            response_stream = client.models.generate_content_stream(
                model="gemini-2.5-flash",
                contents=api_contents,
                config=generate_content_config,
            )
            
            for chunk in response_stream:
                if chunk.text:
                    full_response += chunk.text
                    response_placeholder.write(full_response)
            
            st.session_state.messages.append({"role": "assistant", "content": full_response})
        except Exception as e:
            st.error(f"Error de conexión con Gemini: {e}")
