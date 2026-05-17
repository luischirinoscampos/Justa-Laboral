import streamlit as st
from google import genai
from google.genai import types

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Justa - Tutora Virtual", page_icon="⚖️", layout="centered")

# 2. INYECCIÓN DE ESTILOS CSS (Fondo blanco, texto azul oscuro y caja integrada)
st.markdown("""
    <style>
    /* Forzar fondo blanco absoluto en toda la interfaz */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
    }
    
    /* Títulos y subtítulos en Azul Oscuro Institucional */
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

    /* Forzar texto general en gris oscuro/negro para máxima legibilidad */
    p, span, li, label, .stMarkdown {
        color: #1A202C !important;
    }

    /* Neutralizar el contenedor inferior (Elimina por completo la barra negra) */
    [data-testid="stChatInput"] {
        background-color: #FFFFFF !important;
        border-top: 1px solid #E2E8F0 !important;
        padding: 15px 0px !important;
    }

    /* Estilizar el cuadro de texto interno (Fondo gris claro, texto azul oscuro) */
    [data-testid="stChatInput"] textarea {
        background-color: #F8FAFC !important;
        color: #0A2540 !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 8px !important;
    }

    /* Ajustar el botón de enviar (flecha) al tono azul corporativo */
    [data-testid="stChatInput"] button {
        color: #0A2540 !important;
        background-color: transparent !important;
    }

    /* Ocultar componentes nativos de desarrollo de Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stDecoration"] {display: none;}
    </style>
""", unsafe_allow_html=True)

# 3. ENCABEZADO DE LA INTERFAZ
st.markdown('<h1 class="main-title">⚖️ Justa: Tutora Académica Virtual</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-caption">Asignatura: Derecho del Trabajo | Profesor Luis Ignacio Chirinos Campos</p>', unsafe_allow_html=True)

# 4. INICIALIZACIÓN DEL CLIENTE API Y CONTEXTO
if "gemini_api_key" in st.secrets:
    api_key = st.secrets["gemini_api_key"]
else:
    api_key = None

# Mensaje de bienvenida inicial de Justa
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

# Opciones de configuración del modelo (Andamio cognitivo)
system_instruction = (
    "Eres 'Justa', una tutora académica experta en Derecho del Trabajo para la Universidad Centroccidental "
    "Lisandro Alvarado (UCLA). Tu rol es guiar a las y los estudiantes de forma pedagógica, rigurosa y clara, "
    "utilizando un lenguaje neutral e institucional. Responde con base en la doctrina jurídica y la normativa laboral vigente."
)

# 5. RENDERIZADO DEL HISTORIAL DE CHAT
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 6. PROCESAMIENTO DE CONSULTAS
if prompt := st.chat_input("Escribe tu consulta jurídica aquí..."):
    # Mostrar la pregunta del usuario en la pantalla
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Generar la respuesta llamando a la API de Gemini
    with st.chat_message("assistant"):
        if not api_key:
            error_msg = "Error: No se encontró la configuración de la API Key ('gemini_api_key') en los Secrets de Streamlit."
            st.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
        else:
            try:
                # Inicializar el cliente oficial con la estructura de la API de Google
                client = genai.Client(api_key=api_key)
                
                # Construir el historial para mantener la continuidad de la conversación
                history_contents = []
                for msg in st.session_state.messages[:-1]:
                    role_mapped = "model" if msg["role"] == "assistant" else "user"
                    history_contents.append(
                        types.Content(role=role_mapped, parts=[types.Part.from_text(text=msg["content"])])
                    )
                
                # Configurar los parámetros de comportamiento
                config = types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.3,
                )
                
                # Llamada al modelo
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=config
                )
                
                # Renderizar la respuesta obtenida
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
