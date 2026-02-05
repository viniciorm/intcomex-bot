import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from credentials import (
    SMTP_SERVER,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASS,
    SMTP_RECEIVER,
    SMTP_CC
)

def test_enviar_reporte():
    """
    Script de prueba para verificar la funcionalidad de envío de reportes.
    """
    print("📧 Iniciando prueba de envío de correo...")
    
    try:
        fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        fecha_asunto = datetime.now().strftime("%d/%m/%Y")
        
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = SMTP_RECEIVER
        msg['Cc'] = SMTP_CC
        msg['Subject'] = f"🧪 PRUEBA: Reporte Automático [{fecha_asunto}]"
        
        # Destinatarios
        destinatarios = [SMTP_RECEIVER]
        if SMTP_CC:
            destinatarios.append(SMTP_CC)
            
        cuerpo = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Prueba de Conexión SMTP Exitosa</h2>
            <hr>
            <p>Este es un correo de prueba enviado por el script del bot para verificar la configuración:</p>
            <ul>
                <li><b>Hora de envío:</b> {fecha_actual}</li>
                <li><b>Servidor:</b> {SMTP_SERVER}</li>
                <li><b>Remitente:</b> {SMTP_USER}</li>
                <li><b>Destinatario Principal:</b> {SMTP_RECEIVER}</li>
                <li><b>CC:</b> {SMTP_CC}</li>
            </ul>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(cuerpo, 'html'))
        
        print(f"🔌 Conectando a {SMTP_SERVER}:{SMTP_PORT}...")
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASS)
            print("🔑 Login exitoso.")
            server.sendmail(SMTP_USER, destinatarios, msg.as_string())
            
        print(f"✅ ¡Prueba completada! Correo enviado a {SMTP_RECEIVER} y {SMTP_CC}")
        
    except Exception as e:
        print(f"❌ Error en la prueba de correo: {e}")

if __name__ == "__main__":
    test_enviar_reporte()
