import os
import json
import time
import sys
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

# Importar bots
from image_bot import run_image_bot
from image_uploader import run_image_uploader
from inventory_cleaner import run_inventory_cleaner
from sync_bot import run_sync_bot, init_woocommerce_api, LoginException
from ia_webhook_trigger import run_ia_webhook_trigger
from generate_stats import generate_daily_snapshot
from system_health import run_health_check
from activity_logger import log_activity

# Importar credenciales
try:
    from credentials import (
        SMTP_SERVER,
        SMTP_PORT,
        SMTP_USER,
        SMTP_PASS,
        SMTP_RECEIVER,
        SMTP_CC
    )
except ImportError:
    print("ERROR: No se encontró el archivo 'credentials.py'")
    exit(1)

# Configuración de Rutas
DATA_PATH = "./data_activa/"
STATE_FILE = os.path.join(DATA_PATH, "estado_productos.json")
MAPA_IMAGENES_PATH = os.path.join(DATA_PATH, "mapa_imagenes.json")

# Asegurar que la carpeta de datos existe
os.makedirs(DATA_PATH, exist_ok=True)

def enviar_alerta_emergencia(error):
    """Envía un correo de alerta inmediata ante fallos críticos de login."""
    print("🚨 Enviando Alerta de Emergencia...")
    try:
        fecha = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = "bot_intcomex@tupartnerti.cl, marcosreyes@tupartnerti.cl"
        msg['Subject'] = "🚨 ERROR CRÍTICO: Fallo de Login en Intcomex - Proceso Detenido"
        
        cuerpo = f"""
        <html>
        <body>
            <h2 style='color: #e74c3c;'>🚨 ALERTA DE SISTEMA: FALLO DE ACCESO</h2>
            <p>Se ha detectado un error crítico durante el inicio de sesión en el portal de Intcomex.</p>
            <p><b>Error:</b> {error}</p>
            <p><b>Fecha/Hora:</b> {fecha}</p>
            <hr>
            <p style='color: #c0392b; font-weight: bold;'>EL PROCESO SE HA DETENIDO PARA EVITAR INCONSISTENCIAS.</p>
            <p>Por favor, revisa el screenshot de error en el servidor y valida las credenciales o selectores del bot.</p>
        </body>
        </html>
        """
        msg.attach(MIMEText(cuerpo, 'html'))
        
        destinatarios = ["bot_intcomex@tupartnerti.cl", "marcosreyes@tupartnerti.cl"]
        
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
                server.login(SMTP_USER, SMTP_PASS)
                server.sendmail(SMTP_USER, destinatarios, msg.as_string())
        else:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.sendmail(SMTP_USER, destinatarios, msg.as_string())
        print("✅ Alerta de emergencia enviada.")
    except Exception as e:
        print(f"❌ Falló envío de alerta: {e}")

    # Enviar también por Telegram
    try:
        from credentials import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": f"🚨 ALERTA DE SISTEMA: FALLO DE ACCESO\n\nSe ha detectado un error crítico durante el inicio de sesión en el portal de Intcomex.\n\nError: {error}\n\nEL PROCESO SE HA DETENIDO."
            }, timeout=5)
            print("✅ Alerta de emergencia enviada por Telegram.")
    except Exception as e:
        print(f"❌ Falló envío de alerta por Telegram: {e}")

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def enviar_reporte_consolidado(resumen, error_critico=None):
    """Envía el reporte final consolidado por email."""
    print("\n📧 Enviando reporte consolidado...")
    try:
        fecha_asunto = datetime.now().strftime("%d/%m/%Y")
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = SMTP_RECEIVER
        msg['Cc'] = SMTP_CC
        
        subject = f"✅ Reporte Intcomex Orchestrator [{fecha_asunto}]"
        if error_critico:
            subject = f"🚨 ERROR: Reporte Intcomex [{fecha_asunto}]"
        msg['Subject'] = subject

        destinatarios = [SMTP_RECEIVER]
        if SMTP_CC:
            destinatarios.append(SMTP_CC)

        cuerpo_html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: sans-serif; color: #333; }}
                h2 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 5px; }}
                .stat-box {{ background: #f8f9fa; padding: 10px; border-radius: 5px; margin: 10px 0; }}
                .error {{ color: #e74c3c; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h2>Resumen de Ejecución - {fecha_asunto}</h2>
        """
        
        if error_critico:
            cuerpo_html += f"<p class='error'>⚠️ Error Crítico Detectado: {error_critico}</p>"

        # Fase A: Sync
        sync = resumen.get("sync", {})
        cuerpo_html += f"""
            <div class='stat-box'>
                <h3>Fase A: Sincronización (Precios/Stock)</h3>
                <ul>
                    <li>Estado: {'✅ Completado' if sync.get('status') == 'OK' else '❌ Falló/Pendiente'}</li>
                    <li>Productos Procesados: {sync.get('stats', {}).get('productos_procesados', 0)}</li>
                    <li>Nuevos SKUs Creados: {sync.get('stats', {}).get('productos_creados', 0)}</li>
                    <li>Actualizados: {sync.get('stats', {}).get('productos_actualizados', 0)}</li>
                </ul>
            </div>
        """

        # Fase B: Imágenes
        imgs = resumen.get("imagenes", {})
        cuerpo_html += f"""
            <div class='stat-box'>
                <h3>Fase B: Gestión de Imágenes (Deep Scan)</h3>
                <ul>
                    <li>Descargadas con éxito: {imgs.get('descargadas', 0)}</li>
                </ul>
            </div>
        """

        # Fase C: Uploader
        up = resumen.get("uploader", {})
        cuerpo_html += f"""
            <div class='stat-box'>
                <h3>Fase C: Vinculación WooCommerce</h3>
                <ul>
                    <li>Imágenes vinculadas: {up.get('vinculadas', 0)}</li>
                </ul>
            </div>
        """

        # Fase D: Cleaner
        cl = resumen.get("cleaner", {})
        cuerpo_html += f"""
            <div class='stat-box'>
                <h3>Fase D: Gestión de Inventario (Cleaner)</h3>
                <ul>
                    <li>Re-activados (Borrador -> Publicado): {cl.get('reactivados', 0)}</li>
                    <li>Ocultos por Stock Bajo (<= 2): {cl.get('stock_bajo', 0)}</li>
                    <li>Ocultos por Fuera de Catálogo: {cl.get('fuera_catalogo', 0)}</li>
                </ul>
            </div>
        """

        # Fase E: IA
        ia_stats = resumen.get("ia", {})
        cuerpo_html += f"""
            <div class='stat-box'>
                <h3>Fase E: Enriquecimiento IA (n8n)</h3>
                <ul>
                    <li>Productos Procesados Correctamente: {ia_stats.get('enviados', 0)}</li>
                </ul>
            </div>
        """

        cuerpo_html += f"""
            <p style='font-size: 0.8em; color: #7f8c8d; margin-top: 30px;'>
                Orquestador Intcomex v2.1.0 - tupartnerti.cl
            </p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(cuerpo_html, 'html'))
        
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
                server.login(SMTP_USER, SMTP_PASS)
                server.sendmail(SMTP_USER, destinatarios, msg.as_string())
        else:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.sendmail(SMTP_USER, destinatarios, msg.as_string())
        print("✅ Reporte enviado con éxito.")
    except Exception as e:
        print(f"❌ Falló envío de reporte: {e}")

def enviar_reporte_telegram(resumen, error_critico=None):
    """Envía un resumen de la ejecución a través de Telegram."""
    print("📱 Enviando reporte por Telegram...")
    try:
        from credentials import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            print("Telegram no configurado en credentials.py")
            return
            
        fecha_asunto = datetime.now().strftime("%d/%m/%Y")
        texto = f"📅 *Resumen de Ejecución - {fecha_asunto}*\n\n"
        
        if error_critico:
            texto += f"🚨 *ERROR CRÍTICO DETECTADO:* {error_critico}\n\n"
            
        sync = resumen.get("sync", {})
        texto += "🔄 *FASE A: Sincronización*\n"
        texto += f"Estado: {'✅ Completado' if sync.get('status') == 'OK' else '❌ Falló/Pendiente'}\n"
        texto += f"Procesados: {sync.get('stats', {}).get('productos_procesados', 0)}\n"
        texto += f"Nuevos SKUs: {sync.get('stats', {}).get('productos_creados', 0)}\n"
        texto += f"Actualizados: {sync.get('stats', {}).get('productos_actualizados', 0)}\n\n"
        
        imgs = resumen.get("imagenes", {})
        texto += "🖼️ *FASE B: Imágenes*\n"
        texto += f"Descargadas: {imgs.get('descargadas', 0)}\n\n"
        
        up = resumen.get("uploader", {})
        texto += "☁️ *FASE C: Vinculación WooCommerce*\n"
        texto += f"Vinculadas: {up.get('vinculadas', 0)}\n\n"
        
        cl = resumen.get("cleaner", {})
        texto += "🧹 *FASE D: Limpieza de Inventario*\n"
        texto += f"Re-activados: {cl.get('reactivados', 0)}\n"
        texto += f"Ocultos stock bajo: {cl.get('stock_bajo', 0)}\n"
        texto += f"Ocultos fuera cat: {cl.get('fuera_catalogo', 0)}\n\n"
        
        ia = resumen.get("ia", {})
        texto += "🧠 *FASE E: IA (n8n)*\n"
        texto += f"Enriquecidos: {ia.get('enviados', 0)}\n"

        resp = requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": texto,
            "parse_mode": "Markdown"
        }, timeout=10)
        
        if resp.status_code == 200:
            print("✅ Reporte Telegram enviado.")
        else:
            print(f"❌ Error API Telegram: {resp.status_code} - {resp.text}")
    except ImportError:
        print("Telegram no configurado en credentials.py")
    except Exception as e:
        print(f"❌ Falló envío de reporte por Telegram: {e}")

def main():
    # Detectar modo de ejecución por argumentos
    # python main_orchestrator.py [all|sync|images|upload|clean|ia|local|resume]
    mode = "all"
    if len(sys.argv) > 1:
        # Normalizar modo (quitar guiones si el usuario puso -all o --all)
        mode = sys.argv[1].lower().lstrip("-")

    print("="*60)
    
    log_activity(f"Orquestador iniciado (Modo: {mode.upper()})", "Sistema", "fa-play")

    resumen = {
        "sync": {"status": "SKIPPED", "stats": {}},
        "imagenes": {"descargadas": 0},
        "uploader": {"vinculadas": 0},
        "cleaner": {"reactivados": 0, "stock_bajo": 0, "fuera_catalogo": 0},
        "ia": {"enviados": 0}
    }
    
    error_global = None
    start_time = time.time()
    nuevos_count = 0

    try:
        # FASE A: Sincronización (Solo si mode es 'all', 'sync' o 'local')
        if mode in ['all', 'sync', 'local']:
            try:
                skip_dl = (mode == 'local')
                msg_local = " (MODO LOCAL: Sin descargas)" if skip_dl else ""
                print(f"\n[FASE A] Iniciando Sincronización de Precios/Stock{msg_local}...")
                log_activity("Iniciando Fase A: Sincronización", "Sincronización", "fa-sync fa-spin")
                # Sync Bot requiere login si no es local
                stats, nuevos = run_sync_bot(skip_download=skip_dl)
                resumen["sync"]["status"] = "OK"
                resumen["sync"]["stats"] = stats
                resumen["sync"]["nuevos_skus"] = nuevos
                nuevos_count = len(nuevos) if nuevos else 0
                log_activity(f"Fase A Completada. Nuevos SKUs: {nuevos_count}", "Sincronización", "fa-check-circle")
            except LoginException as le:
                error_msg = f"Fallo de Login: {le}"
                resumen["sync"]["status"] = "CRITICAL_ERROR"
                enviar_alerta_emergencia(error_msg)
                raise Exception(error_msg) # Detener ejecución y enviar reporte final

        # FASE B: Deep Scan de Imágenes
        # Basado en estado: buscamos qué productos en el JSON no tienen imagen
        if mode in ['all', 'images']:
            state = load_state()
            skus_sin_imagen = [sku for sku, data in state.items() if not data.get("tiene_imagen") and data.get("stock", 0) > 0]
            
            if skus_sin_imagen:
                print(f"\n[FASE B] Iniciando Deep Scan para {len(skus_sin_imagen)} SKUs...")
                log_activity(f"Iniciando Fase B: Deep Scan de {len(skus_sin_imagen)} imgs", "Imágenes", "fa-search")
                descargas = run_image_bot(skus_to_process=skus_sin_imagen)
                resumen["imagenes"]["descargadas"] = descargas
                log_activity(f"Fase B Completada. Descargadas: {descargas}", "Imágenes", "fa-image")
            else:
                print("\n[FASE B] No hay SKUs pendientes de imagen. Saltando.")

        # FASE C: Vinculación WooCommerce y Datos
        if mode in ['all', 'upload', 'resume']:
            state = load_state()
            # Pendientes: O tienen imagen nueva, o tienen cambios de precio/stock no sincronizados
            pending_upload = [sku for sku, data in state.items() 
                             if (data.get("tiene_imagen") and not data.get("subido_a_woo")) 
                             or data.get("pendiente_sync_woo")]
            
            # En modo local, forzamos que si tiene imagen local y no esta en woo, vaya a upload
            # Esto ya está cubierto arriba, pero aseguramos
            
            if pending_upload:
                print(f"\n[FASE C] Iniciando Sincronización de {len(pending_upload)} productos...")
                log_activity(f"Iniciando Fase C: Subida a Woo (Batch) de {len(pending_upload)} imgs", "WooCommerce", "fa-cloud-upload-alt")
                procesados = run_image_uploader()
                resumen["uploader"]["vinculadas"] = procesados
                log_activity(f"Fase C Completada. Vinculadas: {procesados}", "WooCommerce", "fa-link")
            else:
                print("\n[FASE C] No hay datos ni imágenes pendientes de sincronizar. Saltando.")

        # FASE D: Limpieza de Inventario
        if mode in ['all', 'clean', 'resume']:
            print("\n[FASE D] Iniciando Limpieza de Inventario...")
            log_activity("Iniciando Fase D: Limpieza de Inventario", "Cleaner", "fa-broom")
            clean_stats = run_inventory_cleaner()
            resumen["cleaner"] = clean_stats
            log_activity(f"Fase D Completada. Ocultados: {clean_stats.get('stock_bajo',0) + clean_stats.get('fuera_catalogo',0)}", "Cleaner", "fa-recycle")

        # FASE E: Disparar Webhook de IA (n8n)
        if mode in ['all', 'ia', 'resume']:
            print("\n[FASE E] Iniciando Webhook de Inteligencia Artificial...")
            log_activity("Iniciando Fase E: IA Enrichment", "Inteligencia Artificial", "fa-robot")
            total_skus_ia = run_ia_webhook_trigger()
            resumen["ia"]["enviados"] = total_skus_ia
            log_activity(f"Fase E Completada. Enriquecidos: {total_skus_ia}", "Inteligencia Artificial", "fa-brain")

    except Exception as e:
        error_global = str(e)
        print(f"\n❌ ERROR CRÍTICO: {error_global}")
        log_activity(f"Fallo Crítico Detenido: {error_global}", "Sistema", "fa-exclamation-triangle")
    finally:
        # Generar estadísticas para el Dashboard automáticamente
        duration = time.time() - start_time
        print("\n📈 Actualizando Dashboard de KPIs...")
        log_activity("Actualizando Dashboard y métricas de ROI", "Sistema", "fa-chart-pie")
        run_health_check()
        generate_daily_snapshot(nuevos_count=nuevos_count, duration=duration)
        
        # Enviar reporte final siempre que haya ocurrido algo o haya un error
        if mode != "none":
            enviar_reporte_consolidado(resumen, error_critico=error_global)
            enviar_reporte_telegram(resumen, error_critico=error_global)
    
    print("\n" + "="*60)
    print("🤖 ORQUESTADOR FINALIZADO")
    print("="*60)

if __name__ == "__main__":
    main()
