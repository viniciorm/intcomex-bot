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

## 📋 Flujo de Operación

1.  **Fase de Acceso**: Selenium Headless para login automatizado y descarga de CSVs.
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
├── woo_batch_manager.py  # Utility para Batch API (Nuevo)
├── generate_stats.py     # Generador de KPIs (Nuevo)
├── sync_bot.py           # Sincronización base
├── image_bot.py          # Descarga de imágenes (Paralelo)
├── image_uploader.py     # Upload de imágenes (Paralelo)
├── inventory_cleaner.py  # Gestión de stock (Batch)
├── ia_webhook_trigger.py # Trigger IA (Paralelo)
└── requirements.txt      # Dependencias
```

## 🔒 Seguridad y Robustez
- **Batch Resilience**: Manejo inteligente de fallos en lotes (Sync Limbo Repair).
- **Concurrency Control**: Hilos configurables para no saturar el servidor host.

## 📄 Licencia
Este proyecto es privado y confidencial para Tu Partner TI.

