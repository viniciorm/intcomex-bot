# 🤖 Bot de Sincronización Intcomex -> WooCommerce `v3.0.0 - VINI TURBO` 🚀

Bot de producción de alto rendimiento diseñado para sincronizar miles de productos desde Intcomex Chile a WooCommerce en tiempo récord mediante arquitectura paralela.

> [!IMPORTANT]
> **Arquitectura ViniBot Turbo**: Esta versión ha sido rediseñada para eliminar cuellos de botella secuenciales. El bot ahora utiliza **Multi-threading** y **Batch API Operations**, reduciendo el tiempo de ejecución de 5+ horas a menos de 45 minutos.

## 🚀 Lo nuevo en v3.0.0 (Vini Turbo)

1.  **Procesamiento Paralelo (Multithreading)**: 
    *   **IA & Webhooks**: Ejecución concurrente de hasta 5 peticiones simultáneas a n8n.
    *   **Imágenes**: Descarga y upload de medios a WordPress en paralelo, eliminando la espera de red secuencial.
2.  **WooCommerce Batch Operations**:
    *   Implementación de `WooBatchManager` para agrupar hasta 100 actualizaciones/creaciones en una sola petición.
    *   Reducción drástica del overhead de red y errores 503 por saturación.
3.  **Dashboard de Performance v2**:
    *   **KPI de Velocidad**: Medición de "Velocidad vs Humano" (ej: 6.3x más rápido).
    *   **ROI de Tiempo**: Seguimiento diario de Horas Hombre (HH) ahorradas.
4.  **Agente de Telegram Integrado**:
    *   **Control Remoto y Programación**: Ejecuta el bot (`/run_now`), verifica su estado (`/status`) y mantén crons programados, todo desde un chat.
    *   **Manejo Interactivo 2FA**: Intercepta solicitudes de código SMS de Intcomex, te avisa a Telegram y espera a que escribas el número para autocompletarlo.
    *   **Notificaciones Finales**: Recibe resumen de ejecución y alertas de error crítico directo en tu dispositivo móvil.

## 📋 Flujo de Operación

1.  **Fase de Acceso**: Selenium para login automatizado y descarga de CSVs. **(NUEVO: Soporte de pausa interactiva en consola para ingresar código de Autenticación 2FA SMS de Intcomex).**
2.  **Fase de Imágenes (Turbo)**: `image_bot.py` cosecha imágenes en paralelo.
3.  **Fase de Carga & Media (Turbo)**: `image_uploader.py` sube binarios a WP y vincula productos en lotes.
4.  **Fase de IA (Turbo)**: `ia_webhook_trigger.py` usa `ThreadPoolExecutor` para enriquecer descripciones mediante n8n/OpenAI sin esperas artificiales.
5.  **Fase de Limpieza**: `inventory_cleaner.py` gestiona stock y productos fuera de catálogo en lotes de 100.

## 🧠 Dashboard de Control (ROI & Velocity)

El sistema incluye un dashboard web interactivo para visualizar el rendimiento:
*   **Velocidad ViniBot**: Compara el tiempo del bot contra el tiempo estimado de un humano (Human Velocity).
*   **HH Ahorradas**: Acumulado histórico y diario de tiempo automatizado.
*   **Stock Health**: Visualización del estado de salud del inventario.

## 🚀 Configuración Inicial

### 1. Instalar Dependencias
```bash
pip install -r requirements.txt
```

### 2. Configurar Credenciales
1. Copia el archivo de ejemplo: `cp credentials.example.py credentials.py`
2. Completa los datos de WooCommerce y WordPress Application Passwords.

## 📖 Uso

### Ejecución Consolidada (Recomendado)
```bash
# Ejecutar todo el flujo optimizado
python main_orchestrator.py all
```

| Script | Función | Modo Turbo |
| :--- | :--- | :--- |
| `main_orchestrator.py` | Orquestador central | ✅ |
| `woo_batch_manager.py` | Gestor de lotes Woo (Core) | ✅ |
| `ia_webhook_trigger.py`| Enriquecimiento n8n paralelo | ✅ |
| `image_uploader.py` | Upload media + Batch Link | ✅ |
| `generate_stats.py` | Cálculo de KPIs y ROI | ✅ |

## 📁 Estructura del Proyecto
```
├── dashboard/            # Web Dashboard (HTML/JS/CSS)
├── data_activa/          # JSONs de estado y estadísticas históricas
├── main_orchestrator.py  # Orquestador central
├── telegram_agent.py     # Controlador de Telegram y Cron
├── woo_batch_manager.py  # Utility para Batch API (Nuevo)
├── generate_stats.py     # Generador de KPIs (Nuevo)
├── sync_bot.py           # Sincronización base
├── image_bot.py          # Descarga de imágenes (Paralelo)
├── image_uploader.py     # Upload de imágenes (Paralelo)
├── inventory_cleaner.py  # Gestión de stock (Batch)
├── ia_webhook_trigger.py # Trigger IA (Paralelo)
└── requirements.txt      # Dependencias
```

## 🚀 Guía de Instalación en VPS (Debian/Ubuntu)

Para desplegar el bot en un servidor remoto (DigitalOcean, AWS, etc.):

### 1. Preparación del Sistema
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl docker.io docker-compose
```

### 2. Instalación
```bash
git clone https://github.com/viniciorm/intcomex-bot.git
cd intcomex-bot

# Configurar credenciales
cp credentials.example.py credentials.py
nano credentials.py # Completa tus datos
```

### 3. Despliegue con Docker
```bash
docker compose up -d
```

### 4. Gestión del Agente (Controlador)
El agente de Telegram se encarga de las ejecuciones programadas y el manejo de 2FA. Se levanta automáticamente con Docker, pero puedes monitorearlo con:
```bash
docker logs -f vinibot-agent
```

### 5. Acceso Remoto
- **Dashboard**: `http://tu-ip-vps:8000/dashboard/index.html` (requiere `python3 -m http.server 8000 &` ejecutándose)

### 6. Configuración de n8n (Flujos e IA)
El enriquecimiento de productos requiere una conexión con **OpenAI**.
1. **Obtener API Key**: Regístrate en [OpenAI Platform](https://platform.openai.com/), crea una API Key y asegúrate de tener saldo (credits).
2. **Importar Flujos**: En n8n, ve a **Workflows** -> **Import from File** y sube `flujo_productos_ia_webhook.json`.
3. **Credenciales en n8n**: Dentro de n8n, ve a **Credentials** -> **Add Credential** -> **OpenAI** y pega tu API Key.
4. **Activar**: Abre el flujo y presiona el botón **Execute Workflow** o **Activate** para que empiece a escuchar al bot.

---

## 🔒 Seguridad y Robustez
- **Batch Resilience**: Manejo inteligente de fallos en lotes (Sync Limbo Repair).
- **Concurrency Control**: Hilos configurables para no saturar el servidor host.

## 📄 Licencia
Este proyecto es privado y confidencial para Tu Partner TI.

