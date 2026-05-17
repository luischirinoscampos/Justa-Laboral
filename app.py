import streamlit as st
from google import genai
from google.genai import types
from datetime import datetime
import pandas as pd
import os

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Justa - Tutora Virtual", page_icon="⚖️", layout="centered")

# Archivo local en el servidor para almacenar de forma persistente las consultas
LOG_FILE = ".interacciones_justa.csv"

def registrar_consulta(texto_pregunta):
    """Guarda de forma persistente el registro de la pregunta en el servidor"""
    ahora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    nuevo_registro = pd.DataFrame([{"Cuándo": ahora, "Qué preguntaron": texto_pregunta}])
    
    if not os.path.exists(LOG_FILE):
        nuevo_registro.to_csv(LOG_FILE, index=False, encoding='utf-8')
    else:
        nuevo_registro.to_csv(LOG_FILE, mode='a', header=False, index=False, encoding='utf-8')

# 2. INYECCIÓN DE ESTILOS CSS AVANZADOS (Alineación simétrica y fondo limpio)
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

    /* ESTABILIZACIÓN Y SIMETRÍA DEL CUADRO DE CONSULTA */
    [data-testid="stChatInput"] {
        background-color: #FFFFFF !important;
        padding: 10px 0px !important;
    }

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

    [data-testid="stChatInput"] textarea:focus {
        background-color: transparent !important;
        color: #0A2540 !important;
    }

    [data-testid="stChatInput"] button {
        color: #0A2540 !important;
        background-color: transparent !important;
        border: none !important;
        margin: 0 !important;
        padding: 0px 4px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
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

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Hola. Soy Justa, tu tutora académica virtual de la unidad curricular Derecho del Trabajo, "
                "gestionada por Luis Ignacio Chirinos Campos. Te doy la bienvenida a este espacio de aprendizaje. "
                "Cuento con la preparación para brindarte orientación y acompañamiento en todo lo relacionado con el "
                "contenido académico de nuestra unidad curricular, basándome estrictamente en los documentos "
                "y materiales de estudio autorizados. Te invito a utilizar esta herramienta con responsabilidad e "
                "integridad en tu proceso de formación. Aquí puedes estudiar, repasar y aclarar cualquier duda o "
                "inquietud que tengas sobre los temas objeto de estudio."
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
if prompt := st.chat_input("Escribe tu consulta académica aquí..."):
    # REGISTRO SILENCIOSO DE LA CONSULTA (Guarda Cuándo y Qué)
    registrar_consulta(prompt)
    
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

# ==========================================
# 7. PANEL DE CONTROL DOCENTE (SECRETO)
# ==========================================
st.sidebar.title("🔐 Control Docente")
clave = st.sidebar.text_input("Introduzca credencial:", type="password")

# Reemplaza "UCLA2026" por la clave de tu preferencia personal
if clave == "UCLA2026":
    st.sidebar.success("Acceso Docente Verificado")
    st.sidebar.subheader("Bitácora de Consultas del EDA")
    
    if os.path.exists(LOG_FILE):
        df_log = pd.read_csv(LOG_FILE, encoding='utf-8')
        
        # Mostrar las interacciones en una tabla ordenada dentro de la barra lateral
        st.sidebar.dataframe(df_log, use_container_width=True)
        
        # Botón para descargar el reporte a formato CSV compatible con Excel
        csv_data = df_log.to_csv(index=False).encode('utf-8')
        st.sidebar.download_button(
            label="📥 Descargar Reporte (CSV)",
            data=csv_data,
            file_name=f"interacciones_justa_{datetime.now().strftime('%d_%m_%Y')}.csv",
            mime="text/csv"
        )
    else:
        st.sidebar.info("Aún no se registran interacciones en el aula.")
