import os
import time
import subprocess
import schedule
import pytz
import telebot
import threading
from datetime import datetime

# Importar credenciales (usar un archivo dummy si no existe para evitar errores)
try:
    from credentials import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
except ImportError:
    print("Error: No se encontró TELEGRAM_BOT_TOKEN en credentials.py")
    exit(1)

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Variables globales para manejar el estado del 2FA
waiting_for_2fa = False
pending_2fa_code = None

def get_allowed_chat_id():
    """Obtiene el Chat ID numérico para comparar"""
    try:
        return int(TELEGRAM_CHAT_ID) if TELEGRAM_CHAT_ID else None
    except ValueError:
        return None

allowed_chat_id = get_allowed_chat_id()

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    chat_id = message.chat.id
    if not allowed_chat_id:
        bot.reply_to(message, f"👋 Hola! Tu TELEGRAM_CHAT_ID es: {chat_id}\n\nPor favor, copia este número y agrégalo a tu archivo credentials.py en la variable TELEGRAM_CHAT_ID, luego reinicia este agente.")
        print(f"\n[ATENCIÓN] Un usuario inició el bot. Su CHAT ID es: {chat_id}")
    elif chat_id != allowed_chat_id:
        bot.reply_to(message, "⛔ No estás autorizado para usar este bot.")
    else:
        bot.reply_to(message, "🤖 ViniBot Agent activo y escuchando.\nComandos disponibles:\n/run_now - Ejecuta el orquestador inmediatamente\n/status - Verifica si el bot está programado y activo")

@bot.message_handler(commands=['status'])
def send_status(message):
    if allowed_chat_id and message.chat.id == allowed_chat_id:
        tz = pytz.timezone('America/Santiago')
        now = datetime.now(tz)
        msg = f"✅ Agente ViniBot en línea.\n🕒 Hora actual (Stgo): {now.strftime('%H:%M:%S')}\n\nProgramación de cron:\n"
        jobs = schedule.get_jobs()
        if not jobs:
            msg += "No hay tareas programadas."
        else:
            for job in jobs:
                msg += f"- Siguiente ejecución: {job.next_run.strftime('%Y-%m-%d %H:%M:%S')}\n"
        bot.reply_to(message, msg)

@bot.message_handler(commands=['run_now'])
def run_now_command(message):
    if allowed_chat_id and message.chat.id == allowed_chat_id:
        bot.reply_to(message, "🚀 Iniciando ViniBot (Ejecución manual)... Te notificaré cuando empiece.")
        # Lanzar en un hilo separado para no bloquear el bot de telegram
        threading.Thread(target=ejecutar_orquestador, args=(message.chat.id,)).start()

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    if allowed_chat_id and message.chat.id == allowed_chat_id:
        texto = message.text.strip()
        # Si comprobamos que es un código numérico (2FA) o si el usuario escribe explícitamente algo
        if texto.isdigit():
            # Guardar el código en un archivo para que sync_bot.py lo lea
            with open("data_activa/pending_2fa.txt", "w") as f:
                f.write(texto)
            bot.reply_to(message, f"👍 Código {texto} recibido localmente. El navegador lo insertará si lo está solicitando.")
        else:
            bot.reply_to(message, "No te entendí. Si necesitas ingresar el código SMS, simplemente envíame el número.\nUsa /help para ver los comandos.")

def ejecutar_orquestador(chat_id=None):
    """Ejecuta el main_orchestrator.py como subproceso"""
    if chat_id is None:
        chat_id = allowed_chat_id
    
    if chat_id:
        bot.send_message(chat_id, "⚙️ Comenzando ejecución programada del ViniBot (Orchestrator)...")
        
    try:
        # Ejecutamos sin capturar el stdout en PIPEs para evitar DEADLOCKS por buffer lleno (64kb)
        # Esto permite que los logs se impriman felizmente en la consola del usuario.
        process = subprocess.Popen(['python', 'main_orchestrator.py', 'all'])
        # Esperar a que termine
        process.wait()
        
        if chat_id:
            bot.send_message(chat_id, f"🏁 Ejecución del ViniBot terminada. (Código de salida: {process.returncode})")
    except Exception as e:
        if chat_id:
            bot.send_message(chat_id, f"❌ Error crítico al ejecutar ViniBot: {e}")

def run_schedule():
    """Loop infinito para el crontab (schedule)"""
    while True:
        schedule.run_pending()
        time.sleep(30) # Chequear cada 30 segundos

def job_wrapper():
    """Wrapper para la tarea de schedule que lanza el thread"""
    print(f"[{datetime.now()}] Lanzando tarea programada...")
    threading.Thread(target=ejecutar_orquestador).start()

if __name__ == '__main__':
    print("🤖 Iniciando Agente de Telegram ViniBot...")
    
    # Programar las ejecuciones asegurando la zona horaria de Chile sin importar dónde esté el PC físicamente
    schedule.every().day.at("08:00", "America/Santiago").do(job_wrapper)
    schedule.every().day.at("15:00", "America/Santiago").do(job_wrapper)
    
    print("🕒 Tareas programadas:")
    for j in schedule.get_jobs():
        print("  -", j)
    
    # Iniciar el hilo del cron
    cron_thread = threading.Thread(target=run_schedule, daemon=True)
    cron_thread.start()
    
    # Iniciar el polling del bot (bloqueante) resistente a caídas de red
    if not allowed_chat_id:
        print("\n=======================================================")
        print("⚠️ AÚN NO HAS CONFIGURADO EL TELEGRAM_CHAT_ID EN credentials.py")
        print("Por favor, abre Telegram, búscame y envíame un mensaje '/start'.")
        print("Aparecerá aquí tu ID. Cópialo, actualiza el credentials.py y reinicia.")
        print("=======================================================\n")
    else:
        bot.send_message(allowed_chat_id, "🟢 Agente de Telegram iniciado exitosamente en la máquina host. Corriendo programaciones a las 08:00 y 15:00.")
        
    print("Iniciando conexión con los servidores de Telegram...")
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=60)
        except Exception as e:
            print(f"[{datetime.now()}] ⚠️ Desconexión temporal o Timeout de Telegram: {e}. Reconectando en 5 segundos...")
            time.sleep(5)
