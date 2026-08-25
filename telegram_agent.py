import os
import time
import subprocess
import schedule
import pytz
import telebot
import threading
import json
import socket
import requests
from datetime import datetime, timedelta

# Importar credenciales (usar un archivo dummy si no existe para evitar errores)
try:
    from credentials import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
except ImportError:
    print("Error: No se encontró TELEGRAM_BOT_TOKEN en credentials.py")
    exit(1)

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Variables globales para manejar el estado
waiting_for_2fa = False
pending_2fa_code = None
current_orchestrator_process = None

def get_allowed_chat_id():
    """Obtiene el Chat ID numérico para comparar"""
    try:
        return int(TELEGRAM_CHAT_ID) if TELEGRAM_CHAT_ID else None
    except ValueError:
        return None

allowed_chat_id = get_allowed_chat_id()

def setup_bot_menu():
    """Registra los comandos en el menú desplegable nativo de la app de Telegram"""
    try:
        commands = [
            telebot.types.BotCommand("stop", "🛑 Detener el proceso inmediatamente"),
            telebot.types.BotCommand("resume", "⏯️ Reanudar ejecución pendiente"),
            telebot.types.BotCommand("run_now", "🚀 Iniciar ejecución completa"),
            telebot.types.BotCommand("status", "📊 Ver estado del bot y servidor"),
            telebot.types.BotCommand("help", "ℹ️ Ver ayuda y comandos")
        ]
        bot.set_my_commands(commands)
        print("✅ Menú de comandos registrado exitosamente en Telegram.")
    except Exception as e:
        print(f"⚠️ No se pudo registrar el menú de comandos en Telegram: {e}")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    chat_id = message.chat.id
    if not allowed_chat_id:
        bot.reply_to(message, f"👋 Hola! Tu TELEGRAM_CHAT_ID es: {chat_id}\n\nPor favor, copia este número y agrégalo a tu archivo credentials.py en la variable TELEGRAM_CHAT_ID, luego reinicia este agente.")
        print(f"\n[ATENCIÓN] Un usuario inició el bot. Su CHAT ID es: {chat_id}")
    elif chat_id != allowed_chat_id:
        bot.reply_to(message, "⛔ No estás autorizado para usar este bot.")
    else:
        bot.reply_to(message, "🤖 ViniBot Agent activo y escuchando.\n\nComandos disponibles en el menú:\n🛑 /stop - Detiene inmediatamente la ejecución en curso\n⏯️ /resume - Reanuda la ejecución desde el último punto\n🚀 /run_now - Ejecuta el orquestador inmediatamente\n📊 /status - Verifica el estado del bot y del servidor\nℹ️ /help - Muestra este mensaje")

@bot.message_handler(commands=['status'])
def send_status(message):
    if allowed_chat_id and message.chat.id == allowed_chat_id:
        tz = pytz.timezone('America/Santiago')
        now = datetime.now(tz)
        
        # Detectar IP pública para saber si es VPS o Local
        try:
            public_ip = requests.get('https://api.ipify.org', timeout=3).text.strip()
        except Exception:
            public_ip = "No disponible"
            
        hostname = socket.gethostname()
        
        msg = f"✅ *Agente ViniBot en línea.*\n"
        msg += f"🖥️ *Servidor:* `{hostname}`\n"
        msg += f"🌐 *IP Pública:* `{public_ip}`\n"
        msg += f"🕒 *Hora actual (Stgo):* {now.strftime('%H:%M:%S')}\n\n"
        msg += "*Programación de cron:*\n"
        
        jobs = schedule.get_jobs()
        if not jobs and not rescheduled_retry_info:
            msg += "No hay tareas programadas."
        else:
            for job in jobs:
                msg += f"- Siguiente ejecución programada: {job.next_run.strftime('%Y-%m-%d %H:%M:%S')}\n"
            if rescheduled_retry_info:
                msg += f"⏳ *Reprogramación por desbloqueo SMS:* {rescheduled_retry_info['display_time']} hrs (Aprox: {rescheduled_retry_info['target_time']})\n"
        
        # Verificar estado de la última ejecución
        try:
            with open("data_activa/actividades.json", "r", encoding="utf-8") as f:
                logs = json.load(f)
            
            if logs:
                # Buscar el último inicio y el último fin
                ultimo_inicio = next((l for l in logs if "Orquestador iniciado" in l['message']), None)
                ultimo_fin = next((l for l in logs if "Orquestador finalizado" in l['message']), None)
                ultimo_error = next((l for l in logs if "Fallo Crítico Detenido" in l['message']), None)
                
                if ultimo_inicio:
                    msg += f"\n📊 *Última ejecución:*\n"
                    msg += f"- Inicio: {ultimo_inicio['timestamp'][:19].replace('T', ' ')}\n"
                    
                    # Si hay un inicio más reciente que el fin o el error, está incompleto
                    ts_inicio = ultimo_inicio['timestamp']
                    ts_fin = ultimo_fin['timestamp'] if ultimo_fin else "0000"
                    ts_err = ultimo_error['timestamp'] if ultimo_error else "0000"
                    
                    if ts_inicio > ts_fin and ts_inicio > ts_err:
                        msg += "⚠️ *ESTADO: INCOMPLETO*\n"
                        msg += "💡 Sugerencia: Usa `/resume` para continuar."
                    elif ts_err > ts_fin:
                        msg += f"❌ *ESTADO: ERROR*\n- Detalle: {ultimo_error['message']}\n"
                    else:
                        msg += "✅ *ESTADO: COMPLETADO*\n"
        except Exception as e:
            msg += f"\n(No se pudo leer el estado: {e})"

        bot.reply_to(message, msg, parse_mode="Markdown")

@bot.message_handler(commands=['run_now'])
def run_now_command(message):
    if allowed_chat_id and message.chat.id == allowed_chat_id:
        bot.reply_to(message, "🚀 Iniciando ViniBot (Ejecución manual)... Te notificaré cuando empiece.")
        # Lanzar en un hilo separado para no bloquear el bot de telegram
        threading.Thread(target=ejecutar_orquestador, args=(message.chat.id, "all")).start()

@bot.message_handler(commands=['resume'])
def resume_command(message):
    if allowed_chat_id and message.chat.id == allowed_chat_id:
        bot.reply_to(message, "⏯️ Reanudando ViniBot (Modo RESUME)... Te notificaré cuando empiece.")
        # Lanzar en un hilo separado para no bloquear el bot de telegram
        threading.Thread(target=ejecutar_orquestador, args=(message.chat.id, "resume")).start()

@bot.message_handler(commands=['stop'])
def stop_command(message):
    global current_orchestrator_process
    if allowed_chat_id and message.chat.id == allowed_chat_id:
        if current_orchestrator_process and current_orchestrator_process.poll() is None:
            bot.reply_to(message, "🛑 Deteniendo el orquestador y cerrando procesos...")
            try:
                pid = current_orchestrator_process.pid
                # Terminar árbol de procesos
                try:
                    import psutil
                    parent = psutil.Process(pid)
                    for child in parent.children(recursive=True):
                        try:
                            child.kill()
                        except: pass
                    parent.kill()
                except Exception:
                    # Fallback si no está psutil
                    if os.name == 'nt':
                        subprocess.call(['taskkill', '/F', '/T', '/PID', str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        subprocess.call(['pkill', '-P', str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    try:
                        current_orchestrator_process.kill()
                    except:
                        current_orchestrator_process.terminate()
                
                # Limpiar archivos de bloqueo y 2FA pendientes
                for temp_f in [LOCK_FILE, "data_activa/pending_2fa.txt"]:
                    if os.path.exists(temp_f):
                        try: os.remove(temp_f)
                        except: pass
                        
                bot.reply_to(message, "✅ Proceso detenido exitosamente. Los bloqueos han sido liberados. Usa /resume o /run_now para volver a iniciar cuando quieras.")
            except Exception as e:
                bot.reply_to(message, f"⚠️ Hubo un error al intentar detener el proceso: {e}")
        else:
            # Limpiar archivo lock residual si quedó colgado
            if os.path.exists(LOCK_FILE):
                try: os.remove(LOCK_FILE)
                except: pass
            bot.reply_to(message, "⚠️ No hay ninguna ejecución del orquestador activa en este momento. Sistema limpio.")

_last_processed_message_id = None

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    global _last_processed_message_id
    if allowed_chat_id and message.chat.id == allowed_chat_id:
        # Evitar responder dos veces al mismo mensaje en caso de reintentos de red de Telegram
        if _last_processed_message_id == message.message_id:
            return
        _last_processed_message_id = message.message_id
        
        texto = message.text.strip()
        # Si comprobamos que es un código numérico (2FA) o si el usuario escribe explícitamente algo
        if texto.isdigit():
            # Guardar el código en un archivo para que sync_bot.py lo lea
            with open("data_activa/pending_2fa.txt", "w") as f:
                f.write(texto)
            bot.reply_to(message, f"👍 Código {texto} recibido localmente. El navegador lo insertará si lo está solicitando.")
        else:
            bot.reply_to(message, "No te entendí. Si necesitas ingresar el código SMS, simplemente envíame el número.\nUsa el menú de comandos o /help para ver las opciones disponibles.")

rescheduled_retry_info = None

def programar_reintento_por_bloqueo(retry_dt):
    global rescheduled_retry_info
    tz_stgo = pytz.timezone('America/Santiago')
    now = datetime.now(tz_stgo)
    delay_seconds = max(5, int((retry_dt - now).total_seconds()))
    rescheduled_retry_info = {
        "target_time": retry_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "display_time": retry_dt.strftime("%H:%M")
    }
    
    def retry_job():
        global rescheduled_retry_info
        print(f"[{datetime.now()}] ⏰ Ejecutando tarea reprogramada por desbloqueo de SMS...")
        rescheduled_retry_info = None
        if os.path.exists("data_activa/rate_limit_lock.json"):
            try: os.remove("data_activa/rate_limit_lock.json")
            except: pass
        ejecutar_orquestador(allowed_chat_id, mode="resume")
        
    timer = threading.Timer(delay_seconds, retry_job)
    timer.daemon = True
    timer.start()
    print(f"✅ Reintento programado con éxito para las {retry_dt.strftime('%H:%M')} hrs (en {delay_seconds} segs).")

def check_pending_rate_limit_reschedule():
    RATE_LIMIT_FILE = "data_activa/rate_limit_lock.json"
    if os.path.exists(RATE_LIMIT_FILE):
        try:
            with open(RATE_LIMIT_FILE, "r", encoding="utf-8") as f:
                rl_data = json.load(f)
            detected_at = datetime.fromisoformat(rl_data["detected_at"])
            minutes_delay = rl_data.get("reschedule_minutes", 135)
            retry_dt = detected_at + timedelta(minutes=minutes_delay)
            now = datetime.now()
            if retry_dt > now:
                tz_stgo = pytz.timezone('America/Santiago')
                retry_dt_localized = tz_stgo.localize(retry_dt) if retry_dt.tzinfo is None else retry_dt
                programar_reintento_por_bloqueo(retry_dt_localized)
            else:
                os.remove(RATE_LIMIT_FILE)
        except Exception as e:
            print(f"Nota: No se pudo restaurar reintento previo: {e}")

LOCK_FILE = "data_activa/orchestrator.lock"
_orchestrator_running = threading.Lock()

def ejecutar_orquestador(chat_id=None, mode="all"):
    """Ejecuta el main_orchestrator.py como subproceso con lock para evitar ejecuciones paralelas."""
    global current_orchestrator_process
    if chat_id is None:
        chat_id = allowed_chat_id

    # Evitar ejecuciones simultáneas (ej: PC se suspende y despierta con jobs atrasados)
    if not _orchestrator_running.acquire(blocking=False):
        msg = "⚠️ ViniBot ya está corriendo. Ejecución ignorada para evitar duplicados."
        print(f"[{datetime.now()}] {msg}")
        if chat_id:
            bot.send_message(chat_id, msg)
        return

    try:
        if chat_id:
            bot.send_message(chat_id, "⚙️ Comenzando ejecución programada del ViniBot (Orchestrator)...")

        # Ejecutamos sin capturar el stdout en PIPEs para evitar DEADLOCKS por buffer lleno (64kb)
        current_orchestrator_process = subprocess.Popen(['python', 'main_orchestrator.py', mode])
        
        # Escribir el PID real del proceso orquestador al lock file para diagnóstico
        with open(LOCK_FILE, "w") as f:
            f.write(str(current_orchestrator_process.pid))

        current_orchestrator_process.wait()

        # Verificar si se detectó bloqueo temporal de SMS ("número inaccesible") para reprogramar automáticamente
        RATE_LIMIT_FILE = "data_activa/rate_limit_lock.json"
        if os.path.exists(RATE_LIMIT_FILE):
            try:
                with open(RATE_LIMIT_FILE, "r", encoding="utf-8") as f:
                    rl_data = json.load(f)
                
                minutes_delay = rl_data.get("reschedule_minutes", 135)
                tz_stgo = pytz.timezone('America/Santiago')
                retry_dt = datetime.now(tz_stgo) + timedelta(minutes=minutes_delay)
                retry_time_str = retry_dt.strftime("%H:%M")
                
                programar_reintento_por_bloqueo(retry_dt)
                
                msg_alerta = (
                    "🚫 *ALERTA INTCOMEX (Bloqueo Temporal de SMS)*\n\n"
                    "La plataforma de Intcomex indica que _'El número proporcionado es inaccesible'_ (bloqueo de seguridad por exceso de solicitudes de SMS).\n\n"
                    f"⏰ *Reprogramación Automática:* He pospuesto la ejecución para las *{retry_time_str} hrs* (en 2 horas y 15 minutos), cuando el portal haya liberado el bloqueo de seguridad.\n\n"
                    "💡 Te avisaré por aquí en cuanto comience para que puedas ingresar el código SMS tranquilamente."
                )
                if chat_id:
                    bot.send_message(chat_id, msg_alerta, parse_mode="Markdown")
            except Exception as e_rl:
                print(f"Error procesando reprogramación por rate limit: {e_rl}")
        elif chat_id:
            if current_orchestrator_process.returncode != 0 and current_orchestrator_process.returncode != 1:
                # Retornos como -15 son típicos de SIGTERM (.terminate())
                bot.send_message(chat_id, f"⚠️ Ejecución del ViniBot interrumpida. (Código de salida: {current_orchestrator_process.returncode})")
            else:
                bot.send_message(chat_id, f"🏁 Ejecución del ViniBot terminada. (Código de salida: {current_orchestrator_process.returncode})")
    except Exception as e:
        if chat_id:
            bot.send_message(chat_id, f"❌ Error crítico al ejecutar ViniBot: {e}")
    finally:
        current_orchestrator_process = None
        # Liberar lock siempre, incluso si hubo error
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
        _orchestrator_running.release()

def run_schedule():
    """Loop infinito para el crontab (schedule)"""
    while True:
        schedule.run_pending()
        time.sleep(30) # Chequear cada 30 segundos

def job_wrapper(expected_hour):
    """Wrapper para la tarea de schedule que lanza el thread.
    Detecta si el job se disparó tarde (por suspensión del PC) y lo ignora.
    """
    tz = pytz.timezone('America/Santiago')
    now = datetime.now(tz)
    
    # Calcular la hora esperada para hoy
    horas, minutos = map(int, expected_hour.split(':'))
    expected_time = now.replace(hour=horas, minute=minutos, second=0, microsecond=0)
    
    # Si la diferencia es mayor a 30 minutos (1800 segundos), se considera un job atrasado (ej. por suspensión)
    # Usamos abs() por si se dispara unos milisegundos/segundos antes o después
    diff_seconds = abs((now - expected_time).total_seconds())
    
    if diff_seconds > 1800:
        msg = f"⏭️ Job de las {expected_hour} omitido: disparado muy tarde ({now.strftime('%H:%M')}). Se ejecutará en la próxima hora programada."
        print(f"[{now}] {msg}")
        if allowed_chat_id:
            bot.send_message(allowed_chat_id, msg)
        return
        
    print(f"[{now}] Lanzando tarea programada de las {expected_hour}...")
    threading.Thread(target=ejecutar_orquestador).start()

if __name__ == '__main__':
    print("🤖 Iniciando Agente de Telegram ViniBot...")
    
    # Configurar el menú nativo de comandos en Telegram
    setup_bot_menu()
    
    # Restaurar reprogramaciones pendientes por bloqueo de SMS si las hubiera
    check_pending_rate_limit_reschedule()
    
    # Programar las ejecuciones asegurando la zona horaria de Chile sin importar dónde esté el PC físicamente
    schedule.every().day.at("08:00", "America/Santiago").do(job_wrapper, "08:00")
    schedule.every().day.at("15:00", "America/Santiago").do(job_wrapper, "15:00")
    
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
    error_count = 0
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=60)
            error_count = 0  # Si logra conectar y mantenerse, reseteamos el contador
        except Exception as e:
            error_count += 1
            print(f"[{datetime.now()}] ⚠️ Desconexión temporal o Timeout de Telegram: {e}. (Intento {error_count}/5)")
            if error_count >= 5:
                print(f"[{datetime.now()}] 🔴 Múltiples fallos de red detectados. Forzando caída para que Docker reinicie el contenedor...")
                os._exit(1)
            time.sleep(5)
