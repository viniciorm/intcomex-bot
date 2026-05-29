import json
import os

STATE_FILE = "data_activa/estado_productos.json"

def main():
    if not os.path.exists(STATE_FILE):
        print(f"Error: No se encontró el archivo {STATE_FILE}")
        return

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        estado = json.load(f)

    for sku, data in estado.items():
        # Marcamos todo como subido para que el VPS no intente poner placeholders
        data["tiene_imagen"] = True
        data["subido_a_woo"] = True
        data["pendiente_sync_woo"] = False

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(estado, f, indent=4, ensure_ascii=False)
        
    print("\n✅ ¡Éxito! Base de datos de estado del VPS asegurada.")
    print("El VPS ahora sabe que no debe poner placeholders ni intentar descargar de nuevo.")

if __name__ == "__main__":
    main()
