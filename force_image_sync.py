import json
import os

STATE_FILE = "data_activa/estado_productos.json"

def main():
    if not os.path.exists(STATE_FILE):
        print(f"Error: No se encontró el archivo {STATE_FILE}")
        return

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        estado = json.load(f)

    modificados = 0

    for sku, data in estado.items():
        # Verificamos si tiene el placeholder o si se marco como que no tiene imagen real subida
        # o si carece de woo_image_url
        if data.get("placeholder_personalizado", False) or not data.get("woo_image_url"):
            data["tiene_imagen"] = False
            data["subido_a_woo"] = False
            data["placeholder_personalizado"] = False
            data["pendiente_sync_woo"] = True
            modificados += 1
            print(f"[{sku}] Estado reiniciado para forzar sincronización de imagen.")

    if modificados > 0:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(estado, f, indent=4, ensure_ascii=False)
        print(f"\n¡Éxito! Se resetearon {modificados} productos.")
    else:
        print("\nNo se encontraron productos que requieran reinicio de imagen.")

if __name__ == "__main__":
    main()
