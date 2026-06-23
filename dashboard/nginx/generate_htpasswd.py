import subprocess
import getpass
import sys
import os

HTPASSWD_PATH = os.path.join(os.path.dirname(__file__), ".htpasswd")

def main():
    print("--- Generador de Credenciales para el Dashboard ---")
    username = input("Introduce el nombre de usuario (por defecto: admin): ").strip() or "admin"
    password = getpass.getpass("Introduce la contraseña: ")
    if not password:
        print("✗ La contraseña no puede estar vacía.")
        sys.exit(1)
        
    print("Generando hash de contraseña...")
    
    # Intentar usar openssl en el sistema
    try:
        res = subprocess.run(
            ["openssl", "passwd", "-apr1", password],
            capture_output=True,
            text=True,
            check=True
        )
        password_hash = res.stdout.strip()
    except Exception:
        # Fallback si openssl no está disponible
        print("⚠ openssl no está disponible, usando fallback SHA-1 (menos seguro, cambiar en producción)...")
        import hashlib
        import base64
        sha = hashlib.sha1(password.encode('utf-8')).digest()
        password_hash = "{SHA}" + base64.b64encode(sha).decode('utf-8')

    with open(HTPASSWD_PATH, "w", encoding="utf-8") as f:
        f.write(f"{username}:{password_hash}\n")
        
    print(f"✅ Archivo creado con éxito en: {HTPASSWD_PATH}")
    print(f"   Usuario: {username}")

if __name__ == "__main__":
    main()
