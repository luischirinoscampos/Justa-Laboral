import streamlit as st
from google import genai
from google.genai import types

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Justa - Tutora Virtual", page_icon="⚖️", layout="centered")

# 2. INYECCIÓN DE ESTILOS CSS AVANZADOS (Fondo blanco absoluto y caja integrada)
st.markdown("""
    <style>
    /* Forzar fondo blanco en toda la infraestructura visible y oculta */
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

    /* Forzar color de texto para alta legibilidad */
    p, span, li, label, .stMarkdown, h1, h2, h3 {
        color: #1A202C !important;
    }

    /* SOLUCIÓN AL CUADRO DE ESCRITURA: Forzar fondo claro en el input y sus pseudoelementos */
    [data-testid="stChatInput"],
    [data-testid="stChatInput"] > div,
    [data-testid="stChatInput"] div[class^="st-emotion-cache"],
    [data-testid="stChatInput"] textarea {
        background-color: #F8FAFC !important;
        background: #F8FAFC !important;
        color: #0A2540 !important;
        border: 1px solid #CBD5E1 !important;
    }

    /* Asegurar que el área interna de texto elimine cualquier rastro oscuro al escribir o enfocar */
    [data-testid="stChatInput"] textarea:focus {
        background-color: #F8FAFC !important;
        color: #0A2540 !important;
        border-color: #0A2540 !important;
        box-shadow: none !important;
    }

    /* Ajustar el botón de envío (Flecha) */
    [data-testid="stChatInput"] button {
        color: #0A2540 !important;
        background-color: transparent !important;
    }

    /* Ocultar componentes de desarrollo */
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

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Hola. Soy Justa, tutora académica virtual de la asignatura Derecho del Trabajo, "
                "gestionada por Luis Ignacio Chirinos Campos. Te doy la bienvenida a este espacio de aprendizaje. "
                "Cuento con la preparación para brindarte orientación y acompañamiento en todo lo relacionado con el "
                "contenido académico de nuestra unidad curricular, basándome estrictamente en los documentos "
                "y materiales de estudio autorizados. Te invito a utilizar esta herramienta con responsabilidad e "
                "integridad en tu proceso de formación. Aquí puedes estudiar, repasar y aclarar cualquier duda o "
                "inquietud que tengas sobre los temas de la materia."
            )
        }
    ]

system_instruction = (
    "Eres 'Justa', una tutora académica experta en Derecho del Trabajo para la Universidad Centroccidental "
    "Lisandro Alvarado (UCLA). Tu rol es guiar a las y los estudiantes de forma pedagógica, rigurosa y clara, "
    "utilizando un lenguaje neutral e institucional. Responde con base en la doctrina jurídica y la normativa laboral vigente."
)

# 5. DESPLIEGUE DEL HISTORIAL DE CONVERSACIÓN
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 6. ENTRADA DE USUARIO Y PROCESAMIENTO
if prompt := st.chat_input("Escribe tu consulta jurídica aquí..."):
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
                client = genai.Client(api_key=api_key)
                
                history_contents = []
                for msg in st.session_state.messages[:-1]:
                    role_mapped = "model" if msg["role"] == "assistant" else "user"
                    history_contents.append(
                        types.Content(role=role_mapped, parts=[types.Part.from_text(text=msg["content"])])
                    )
                
                config = types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.3,
                )
                
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=config
                )
                
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                
            except Exception as e:
                error_str = str(e)
                if "RESOURCE_EXHAUSTED" in error_str:
                    clean_error = "Se ha agotado la cuota temporal de consultas de la API. El servicio se restablecerá automáticamente en unos momentos."
                    st.error(clean_error)
                else:
                    clean_error = f"Ocurrió un inconveniente al procesar la solicitud: {error_str}"
                    st.error(clean_error)
                st.session_state.messages.append({"role": "assistant", "content": clean_error})
