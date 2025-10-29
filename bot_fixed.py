import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)
# ==============================================================================
# ⚠️ 1. CONFIGURACIÓN REQUERIDA (NO TOCAR, VALORES YA PEGADOS)
# ==============================================================================

# El token de tu bot obtenido del Portal de Desarrolladores de Discord.
TOKEN_BOT = os.getenv("DISCORD_TOKEN")

# ID DEL SERVIDOR: Haz clic derecho en el nombre de tu servidor -> Copiar ID.
ID_SERVIDOR = int(os.getenv("SERVER_ID"))

# ID DEL CANAL DE TEXTO: Canal de respaldo donde se enviará la encuesta
# si el usuario tiene los Mensajes Directos (DM) desactivados.
ID_CANAL_TEXTO_VERIFICACION = int(os.getenv("VERIF_CHANNEL_ID"))

# ==============================================================================
# 2. CONFIGURACIÓN INTERNA Y UTILIDADES
# ==============================================================================

# Un Set para rastrear a los usuarios que han completado la encuesta temporalmente.
USUARIOS_VERIFICADOS_VOZ = set()

# Diccionario para rastrear el progreso de la encuesta de cada usuario.
# {user_id: índice_de_pregunta_actual}
PROGRESO_ENCUESTA = {}

# La lista de emojis a usar (solo usamos 1 y 2 en las preguntas)
OPCIONES_EMOJIS = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']

# --- BANCO DE PREGUNTAS OBLIGATORIAS (10 PREGUNTAS) ---
BANCO_PREGUNTAS = [
    {
        "pregunta": "¿El moma es un genio de la programación?",
        "opciones": ["Sí", "No"],
        "respuesta_correcta": "1️⃣"
    },
    {
        "pregunta": "¿Qué es peor: el droga de support o que el feto se vaya a acompañar al moma?",
        "opciones": ["El droga", "El feto"],
        "respuesta_correcta": "2️⃣"
    },
    {
        "pregunta": "¿Debería haber un canal solo para el moma se cague?",
        "opciones": ["Sí, absolutamente", "No"],
        "respuesta_correcta": "1️⃣"
    },
    {
        "pregunta": "¿El lag del feto es causando por su PC o por el internet?",
        "opciones": ["PC", "Internet"],
        "respuesta_correcta": "2️⃣"
    },
    {
        "pregunta": "¿Los ctm de las pizza colombiana le tiraron pollos a la pizza?",
        "opciones": ["Si y la moquiaron", "No"],
        "respuesta_correcta": "1️⃣"
    },
    {
        "pregunta": "¿Que es peor pirarle la pela a los plataformeros klos o jugar con el moma?",
        "opciones": ["Ser un plataformero klo", "Jugar con el moma"],
        "respuesta_correcta": "1️⃣"
    },
    {
        "pregunta": "¿Que prefires darle la luca al vagabundo ctm o ir al lider y comprarte una bebida y que te de la pera tomartela en la pizza colombiana?",
        "opciones": ["Darle la luca", "Que te de la pera"],
        "respuesta_correcta": "2️⃣"
    },
    {
        "pregunta": "¿Que es peor ser main yasuo o chuparle la teta a la watusi?",
        "opciones": ["Ser main yasuo", "Ser main yasuo"],
        "respuesta_correcta": "2️⃣"
    },
    {
        "pregunta": "¿Es este bot realmente molesto?",
        "opciones": ["No", "No"],
        "respuesta_correcta": "1️⃣"
    },
    {
        "pregunta": "Pregunta Final: ¿Que es peor ser de la Islacity o del MonteYork?",
        "opciones": ["Islacity", "MonteYork"],
        "respuesta_correcta": "1️⃣"
    },
]

# Definir las Intenciones (Intents) necesarias
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

# Crear el objeto Bot
bot = commands.Bot(command_prefix='!', intents=intents)

# Funciones de utilidad
def marcar_como_verificado(user_id):
    USUARIOS_VERIFICADOS_VOZ.add(user_id)

def desmarcar_como_verificado(user_id):
    USUARIOS_VERIFICADOS_VOZ.discard(user_id)

def esta_verificado(user_id):
    return user_id in USUARIOS_VERIFICADOS_VOZ


# ==============================================================================
# 3. LÓGICA DE LA ENCUESTA SECUENCIAL (NUEVO NÚCLEO)
# ==============================================================================

async def iniciar_o_continuar_encuesta(member, canal_destino_voz):
    """
    Función recursiva para manejar las N preguntas de forma secuencial.
    """
    user_id = member.id
    # Obtenemos el progreso actual del usuario (0 si es la primera vez)
    indice_actual = PROGRESO_ENCUESTA.get(user_id, 0)
    
    # --- 1. Lógica de Finalización ---
    if indice_actual >= len(BANCO_PREGUNTAS):
        # ¡ENCUESTA COMPLETA! Dar acceso.
        marcar_como_verificado(user_id)
        # Intentar reingresar al usuario a la sala de voz
        try:
            await member.move_to(canal_destino_voz)
            await member.send("✅ **¡Acceso concedido!** Has superado las 10 preguntas obligatorias. ¡Puedes usar la voz!")
        except Exception as e:
            # Esto puede pasar si el canal de voz se cerró.
            print(f"Error al reingresar a {member.display_name}: {e}")
            await member.send("✅ **¡Acceso concedido!** Pero no pude reingresarte automáticamente (quizás el canal cerró). ¡Puedes unirte ahora!")
            
        # Limpiamos el progreso para que el bot no lo moleste con preguntas si falla algo.
        if user_id in PROGRESO_ENCUESTA:
            del PROGRESO_ENCUESTA[user_id]
        return

    # --- 2. Enviar la Pregunta Actual ---
    pregunta_data = BANCO_PREGUNTAS[indice_actual]
    
    descripcion_opciones = ""
    for i, opcion in enumerate(pregunta_data["opciones"]):
        # Usamos 1️⃣ y 2️⃣ para las dos opciones
        descripcion_opciones += f"{OPCIONES_EMOJIS[i]} {opcion}\n"

    embed = discord.Embed(
        title=f"🚨 PREGUNTA {indice_actual + 1} de {len(BANCO_PREGUNTAS)}: {pregunta_data['pregunta']}",
        description=descripcion_opciones,
        color=discord.Color.dark_orange()
    )
    embed.set_footer(text=f"Responde correctamente en 5 minutos para pasar a la siguiente. ({member.display_name})")

    try:
        mensaje_encuesta = await member.send(embed=embed)
        for i in range(len(pregunta_data["opciones"])):
            await mensaje_encuesta.add_reaction(OPCIONES_EMOJIS[i])
        
    except discord.Forbidden:
        # Manejo si los DMs están cerrados (usamos el canal de verificación)
        canal_respaldo = bot.get_channel(ID_CANAL_TEXTO_VERIFICACION)
        if canal_respaldo:
            await canal_respaldo.send(f"{member.mention}, ¡Tu DM está cerrado! No puedo enviarte las 10 preguntas. Debes activarlo para acceder a la voz.")
        return

    # --- 3. Esperar la Reacción (Respuesta) ---
    def check_respuesta(reaction, user):
        # Solo acepta opciones válidas por el usuario correcto.
        es_opcion_valida = str(reaction.emoji) in OPCIONES_EMOJIS[:len(pregunta_data["opciones"])]
        return user == member and reaction.message.id == mensaje_encuesta.id and es_opcion_valida

    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=300.0, check=check_respuesta)
        
        # --- 4. Evaluar la Respuesta ---
        if str(reaction.emoji) == pregunta_data["respuesta_correcta"]:
            # Respuesta Correcta: Pasa a la siguiente pregunta
            PROGRESO_ENCUESTA[user_id] += 1
            await iniciar_o_continuar_encuesta(member, canal_destino_voz) # Llamada recursiva
            
        else:
            # Respuesta Incorrecta: ¡Reinicia la encuesta! (La mayor molestia)
            PROGRESO_ENCUESTA[user_id] = 0
            await member.send("❌ **¡RESPUESTA INCORRECTA!** La encuesta de 10 preguntas se ha **REINICIADO** desde la Pregunta 1. Tendrás que unirte a la voz de nuevo para volver a empezar.")
            # Eliminamos el progreso para que solo se reinicie la próxima vez que intente unirse
            if user_id in PROGRESO_ENCUESTA:
                del PROGRESO_ENCUESTA[user_id]

    except asyncio.TimeoutError:
        # Si se acaba el tiempo, lo sacamos del progreso
        if user_id in PROGRESO_ENCUESTA:
            del PROGRESO_ENCUESTA[user_id]
        await member.send("⌛ **Tiempo agotado (5 minutos).** Se canceló el proceso. ¡Intenta unirte a la voz de nuevo para reiniciar las 10 preguntas!")
        

# ==============================================================================
# 4. EVENTOS DEL BOT (MODIFICADO)
# ==============================================================================

@bot.event
async def on_ready():
    print(f'🤖 ¡Bot conectado como {bot.user}!')
    await bot.change_presence(activity=discord.Game(name="¡Evitando que se unan a voz con 10 preguntas!"))
    print('--------------------------------')


@bot.event
async def on_voice_state_update(member, before, after):
    
    # 1. Lógica de DESVERIFICACIÓN (La Molestia: al salir de voz, se desverifica)
    if before.channel is not None and after.channel is None:
        if member.id in USUARIOS_VERIFICADOS_VOZ:
            desmarcar_como_verificado(member.id)
            print(f"[{member.display_name}] salió de voz. Desverificado. ¡Próxima vez, encuesta de nuevo!")
            return

    # 2. Lógica de VERIFICACIÓN OBLIGATORIA (El Bloqueo Molesto)
    if after.channel is not None and not esta_verificado(member.id):
        
        # --- A) Expulsar Inmediatamente del Canal de Voz ---
        try:
            await member.move_to(None) 
            print(f"❌ [Bloqueo] {member.display_name} fue expulsado de la voz. Iniciando 10 preguntas...")
        except Exception as e:
            print(f"Error al mover a {member.display_name}: {e}. ¿Tiene el bot permiso 'Mover Miembros'?")
            return

        # --- B) Iniciar o Continuar el Proceso de 10 Preguntas ---
        # Si ya tiene un progreso de encuesta (por ejemplo, falló una pregunta), 
        # reiniciamos a la pregunta 1. Si no lo tiene, iniciamos la pregunta 1.
        PROGRESO_ENCUESTA[member.id] = 0 # Siempre iniciamos desde la primera pregunta
        await iniciar_o_continuar_encuesta(member, after.channel)


# ==============================================================================
# 5. INICIO DEL BOT
# ==============================================================================

if __name__ == "__main__":
    try:
        bot.run(TOKEN_BOT) 
    except discord.HTTPException as e:
        print(f"🚨 ERROR: No se pudo conectar. Verifica que tu token sea correcto. Error: {e}")
    except Exception as e:
        print(f"🚨 ERROR INESPERADO: {e}")