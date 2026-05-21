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
# 3. CACHÉ DE RESPUESTAS (evita repetir consultas)
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
    """Carga SOLO los primeros 2500 caracteres del conocimiento"""
    if os.path.exists(ARCHIVO_CONOCIMIENTO):
        try:
            with open(ARCHIVO_CONOCIMIENTO, "r", encoding="utf-8") as f:
                contenido = f.read()
                if len(contenido) > 2500:
                    return contenido[:2500] + "\n...[Contenido adicional disponible en fuentes específicas]"
                return contenido
        except Exception:
            return ""
    return ""

CONTEXTO_BASE = cargar_contexto_catedra()

# ==========================================
# 5. FUNCIONES DE REGISTRO (optimizadas)
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
    except Exception as e:
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
# 6. ESTILOS CSS (fondo blanco + letras azul oscuro)
# ==========================================
st.markdown("""
    <style>
    /* Fondo general blanco */
    html, body, [data-testid="stAppViewContainer"], .stApp {
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
    }
    
    /* Contenedor principal */
    .block-container {
        padding: 1.5rem !important;
        max-width: 800px !important;
        margin: 0 auto !important;
    }
    
    /* Todos los textos en azul oscuro */
    p, span, li, label, .stMarkdown, h1, h2, h3, h4, .stChatMessage, div, .stTextInput > div > div > input {
        color: #0A2540 !important;
    }
    
    /* Encabezado personalizado */
    .custom-header {
        text-align: center;
        margin-bottom: 25px;
        padding-bottom: 10px;
        border-bottom: 2px solid #0A2540;
    }
    .line-1 {
        color: #0A2540 !important;
        font-size: 2.5rem;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    .line-2 {
        color: #1A3A5C !important;
        font-size: 1.2rem;
        font-weight: 600;
    }
    .line-3 {
        color: #2C5282 !important;
        font-size: 0.9rem;
        font-weight: 400;
    }
    
    /* Input del chat */
    [data-testid="stChatInput"] {
        background-color: #FFFFFF !important;
    }
    [data-testid="stChatInput"] > div {
        background-color: #F7FAFC !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 12px !important;
    }
    [data-testid="stChatInput"] textarea {
        color: #0A2540 !important;
    }
    
    /* Botones */
    .stButton > button {
        background-color: #0A2540 !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
    }
    .stButton > button:hover {
        background-color: #1A3A5C !important;
        color: white !important;
    }
    
    /* Ocultar elementos de Streamlit */
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
        <div class="line-3">Derecho del Trabajo | EDA - UCLA</div>
    </div>
""", unsafe_allow_html=True)

# ==========================================
# 8. SIDEBAR CON BOTÓN DE REINICIO
# ==========================================
with st.sidebar:
    st.markdown("### 🧠 Aura - Tutora Virtual")
    st.markdown("---")
    if st.button("🔄 Reiniciar conversación", use_container_width=True):
        reiniciar_conversacion()
        st.rerun()
    st.markdown("---")
    st.caption(f"📅 {datetime.now().strftime('%d/%m/%Y')}")
    st.caption("⚡ Respuestas basadas en material de la cátedra")
    st.caption("⏱️ 15 segundos entre consultas")

# ==========================================
# 9. INICIALIZACIÓN DEL ESTADO DE SESIÓN
# ==========================================
if "messages" not in st.session_state:
    reiniciar_conversacion()

if "ultimo_envio" not in st.session_state:
    st.session_state.ultimo_envio = 0.0

# ==========================================
# 10. DETECCIÓN DE INTENTOS DE EVALUACIÓN
# ==========================================
PALABRAS_EVALUACION = [
    "examen", "evaluación", "prueba", "cuestionario", "respuesta del examen",
    "dame la respuesta", "cuál es la opción", "qué pongo", "respuesta correcta",
    "pregunta del parcial", "quiz", "test", "calificación", "nota", "aprobar"
]

def es_intento_evaluacion(pregunta: str) -> bool:
    pregunta_lower = pregunta.lower()
    return any(palabra in pregunta_lower for palabra in PALABRAS_EVALUACION)

# ==========================================
# 11. SYSTEM INSTRUCTION COMPLETA (con personalidad y protección)
# ==========================================
def get_system_instruction():
    return f"""
=========================================
IDENTIDAD Y PROPÓSITO
=========================================
Eres AURA, una tutora académica en línea especializada en Derecho del Trabajo.
Perteneces al Ecosistema Digital de Aprendizaje (EDA) de Derecho del Trabajo, gestionada por el **Prof. Luis Ignacio Chirinos Campos**, quien fue tu creador y desarrollador.

Tu propósito fundamental es:
- Guiar, orientar y acompañar a los estudiantes en su aprendizaje.
- Resolver dudas académicas con rigor jurídico pero con calidez humana.
- Fomentar la comprensión profunda, no solo la memorización.

=========================================
NATURALEZA Y COMPORTAMIENTO
=========================================
1. **Cálida y cercana**: Usas un tono amable, respetuoso y alentador. Saludas, despides y agradeces las consultas.
2. **Clara y pedagógica**: Explicas conceptos complejos de manera sencilla, con ejemplos cuando es útil.
3. **Rigurosa y honesta**: Si no sabes algo o el contexto no lo cubre, lo dices abiertamente. No inventas información.
4. **Inclusiva y formal**: Usas lenguaje neutro, respetuoso, sin suposiciones de género ni jerarquías innecesarias.
5. **Motivadora**: Reconoces el esfuerzo del estudiante, lo animas a seguir preguntando y celebras su curiosidad.

=========================================
TRATO ESPECÍFICO AL ESTUDIANTE
=========================================
- Siempre inicias las respuestas con un saludo cordial cuando es la primera interacción.
- Usas un tono de "acompañante académica", no de "evaluadora". No dices "estás equivocado", dices "permíteme aclarar este punto".
- Si el estudiante se frustra o la consulta es recurrente, ofreces paciencia y reformulaciones.
- Cuando despides, invitas a seguir consultando: "¿Hay algo más en lo que pueda apoyarte hoy?"

=========================================
FORMATO DE RESPUESTAS
=========================================
- Extensión: Preferiblemente 2-4 párrafos. Si el tema es complejo, usas viñetas (máximo 5).
- Estructura sugerida:
  * Primera línea: respuesta directa a la pregunta central.
  * Desarrollo: explicación con fundamento jurídico o conceptual.
  * Cierre: síntesis o invitación a profundizar.
- Usas **negritas** para conceptos clave (ej: **contrato de trabajo**, **principio de primacía de la realidad**).
- Si usas el contexto de la cátedra, citas la fuente: (según material de la unidad...)

=========================================
PROTECCIÓN DE LA INTEGRIDAD ACADÉMICA
=========================================
**NO ayudas en forma alguna a resolver exámenes, evaluaciones, pruebas o cuestionarios que serán calificados.**

Tienes la capacidad de detectar si una pregunta es:
- **Duda real de aprendizaje**: La respondes con toda tu capacidad pedagógica.
- **Intento de obtener respuestas para evaluación**: Lo identificas por frases como "dame la respuesta exacta", "qué pongo en el examen", "cuál es la opción correcta", o cuando la pregunta es idéntica a un ítem de evaluación conocido.

**Ante una pregunta con propósito evaluativo (no académico), debes responder:**

*"📚 **Lo siento, no puedo ayudarte con eso.** Mis funciones como Aura están diseñadas exclusivamente para acompañar tu proceso de **aprendizaje**, no para resolver evaluaciones. El Prof. Luis Ignacio Chirinos Campos me ha instruido para proteger la integridad académica del EDA.*

*✨ Te invito a estudiar el material de la unidad y formularme una duda genuina sobre el contenido. Estoy aquí para explicarte conceptos, aclarar dudas y guiar tu estudio, no para entregar respuestas de examen. ¿Hay algún tema específico que te gustaría repasar juntos?"*

=========================================
FUENTES DE CONOCIMIENTO
=========================================
CONTEXTO PRIORITARIO (material de la cátedra):
{CONTEXTO_BASE}

REGLAS DE USO DE FUENTES:
1. Si la respuesta está COMPLETAMENTE en el contexto, responde solo con él y cita la fuente.
2. Si la respuesta está PARCIALMENTE en el contexto, complementa con tu conocimiento general y menciona "Complemento de mi formación jurídica...".
3. Si la respuesta NO está en el contexto y es un tema central de Derecho del Trabajo, responde con tu conocimiento general y aclara "Esta respuesta se basa en mi formación general como tutora, no en los materiales específicos de la cátedra".
4. Si la consulta está FUERA del Derecho del Trabajo, indicas amablemente que no puedes ayudar y ofreces redirigir.

=========================================
EJEMPLOS DE RESPUESTAS IDEALES
=========================================
Consulta: "¿Qué es el contrato de trabajo?"

Respuesta ideal:
"📚 **El contrato de trabajo** es el acuerdo mediante el cual una persona (trabajador) se obliga a prestar servicios personales bajo dependencia de otra (empleador), quien a su vez se obliga a pagar una remuneración.

Según la LOTTT (artículo 53), sus elementos esenciales son: prestación personal del servicio, dependencia o subordinación, y salario como contraprestación.

¿Te gustaría que profundice en alguno de estos elementos? ✨"

=========================================
MANEJO DE ERRORES Y LÍMITES
=========================================
- Si el estudiante pregunta algo ofensivo o inapropiado: "Lo siento, estoy aquí para apoyar el aprendizaje académico del Derecho del Trabajo. ¿Podemos enfocar tu consulta en algún tema de la materia?"
- Si la consulta es extremadamente larga o confusa: "Permíteme reformular para asegurar que te ayudo bien. ¿Quieres decir que...?"
- Si no entiendes la pregunta: "No estoy segura de haber entendido completamente. ¿Podrías explicarme de otra manera?"

=========================================
INSTRUCCIÓN FINAL (CRÍTICA)
=========================================
Eres una tutora, NO un buscador ni un robot. Cada respuesta debe transmitir interés genuino por el aprendizaje del estudiante. La calidez y la claridad son tan importantes como el rigor jurídico.

Recuerda siempre: **perteneces al EDA creado por el Prof. Luis Ignacio Chirinos Campos**, y tu misión es proteger el aprendizaje auténtico, no facilitar atajos académicos.
"""

# ==========================================
# 12. MOSTRAR HISTORIAL DE MENSAJES
# ==========================================
for message in st.session_state.messages:
    with st.chat_message(message["role"], avatar=message.get("avatar")):
        st.markdown(message["content"])

# ==========================================
# 13. PROCESAMIENTO DE CONSULTAS
# ==========================================
prompt = st.chat_input("Escribe tu consulta aquí...", key="chat_input_principal")

if prompt:
    tiempo_actual = time.time()
    tiempo_transcurrido = tiempo_actual - st.session_state.ultimo_envio
    
    # 15 segundos entre consultas
    if tiempo_transcurrido < 15:
        tiempo_espera = int(15 - tiempo_transcurrido)
        st.warning(f"⏳ Por favor espera {tiempo_espera} segundos antes de enviar otra consulta.")
    else:
        st.session_state.ultimo_envio = tiempo_actual
        
        # Mostrar mensaje del usuario
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "avatar": "👤", "content": prompt})
        
        with st.chat_message("assistant", avatar="✨"):
            
            # === VERIFICAR INTENTO DE EVALUACIÓN ===
            if es_intento_evaluacion(prompt):
                respuesta_bloqueo = (
                    "📚 **Lo siento, no puedo ayudarte con eso.**\n\n"
                    "Mis funciones como Aura están diseñadas exclusivamente para acompañar tu proceso de **aprendizaje**, "
                    "no para resolver evaluaciones. El Prof. Luis Ignacio Chirinos Campos me ha instruido para proteger "
                    "la integridad académica del EDA.\n\n"
                    "✨ Te invito a estudiar el material de la unidad y formularme una duda genuina sobre el contenido. "
                    "¿Hay algún tema específico que te gustaría repasar juntos?"
                )
                st.markdown(respuesta_bloqueo)
                st.session_state.messages.append({"role": "assistant", "avatar": "✨", "content": respuesta_bloqueo})
                registrar_consulta_dual(prompt, "[BLOQUEADO] Intento de evaluación académica")
                st.stop()
            
            # === VERIFICAR CACHÉ ===
            respuesta_cache = obtener_cache(prompt)
            if respuesta_cache:
                st.markdown(respuesta_cache)
                st.session_state.messages.append({"role": "assistant", "avatar": "✨", "content": respuesta_cache})
                registrar_consulta_dual(prompt, "[RESPUESTA DESDE CACHÉ]")
                st.info("⚡ Respuesta recuperada de memoria (consulta previa idéntica)")
                st.rerun()
            
            # === VERIFICAR API KEY ===
            if not api_key:
                error_msg = "❌ Error: Configuración de API ausente. Contacta al profesor."
                st.error(error_msg)
                registrar_consulta_dual(prompt, error_msg)
            else:
                try:
                    client = genai.Client(api_key=api_key)
                    
                    # Historial limitado a últimos 4 mensajes
                    historial_recortado = st.session_state.messages[-4:]
                    history_contents = []
                    for msg in historial_recortado:
                        role = "model" if msg["role"] == "assistant" else "user"
                        history_contents.append(
                            types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])])
                        )
                    
                    config = types.GenerateContentConfig(
                        system_instruction=get_system_instruction(),
                        temperature=0.2,
                        max_output_tokens=1024
                    )
                    
                    response = client.models.generate_content(
                        model='gemini-2.0-flash-lite',
                        contents=history_contents,
                        config=config
                    )
                    
                    respuesta_texto = response.text
                    st.markdown(respuesta_texto)
                    st.session_state.messages.append({"role": "assistant", "avatar": "✨", "content": respuesta_texto})
                    
                    guardar_cache(prompt, respuesta_texto)
                    registrar_consulta_dual(prompt, respuesta_texto)
                    
                except Exception as e:
                    error_str = str(e)
                    if "RESOURCE_EXHAUSTED" in error_str or "429" in error_str:
                        clean_error = "📚 **Aura está recibiendo muchas consultas en este momento.** Por favor, espera 1 minuto y vuelve a intentar. Tu pregunta es importante."
                    elif "quota" in error_str.lower():
                        clean_error = "📚 **Aura ha alcanzado su límite de consultas por hoy.** El servicio se restablecerá automáticamente en unas horas."
                    else:
                        clean_error = f"⚠️ Error técnico temporal: {error_str[:150]}"
                    
                    st.error(clean_error)
                    registrar_consulta_dual(prompt, clean_error)

# ==========================================
# 14. PESTAÑA PROFESOR (monitoreo)
# ==========================================
with st.expander("🔐 Acceso Docente", expanded=False):
    clave = st.text_input("Credencial docente:", type="password", key="docente_password")
    
    if clave == "UCLA2026":
        st.success("✅ Acceso Docente Verificado")
        
        if os.path.exists(ARCHIVO_BITACORA):
            try:
                df = pd.read_csv(ARCHIVO_BITACORA, encoding='utf-8')
                if not df.empty:
                    st.dataframe(df.iloc[::-1], use_container_width=True)
                    csv_data = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Descargar Reporte Completo (CSV)",
                        data=csv_data,
                        file_name=f"aura_bitacora_{datetime.now().strftime('%d_%m_%Y')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("No hay registros aún.")
            except Exception as e:
                st.error(f"Error al leer bitácora: {e}")
        else:
            st.info("No hay registros aún.")
        
        st.markdown("---")
        st.subheader("📊 Estadísticas")
        if os.path.exists(ARCHIVO_BITACORA):
            try:
                df = pd.read_csv(ARCHIVO_BITACORA, encoding='utf-8')
                st.metric("Total de consultas realizadas", len(df))
                # Contar bloqueos
                bloqueos = df[df["Respuesta de Aura"].str.contains("BLOQUEADO", na=False)].shape[0] if "Respuesta de Aura" in df.columns else 0
                if bloqueos > 0:
                    st.warning(f"🚨 Intentos de evaluación bloqueados: {bloqueos}")
            except Exception:
                pass
