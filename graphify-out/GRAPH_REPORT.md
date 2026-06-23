# Graph Report - .  (2026-06-19)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 183 nodes · 253 edges · 25 communities
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS · INFERRED: 1 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `4233cbb6`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]

## God Nodes (most connected - your core abstractions)
1. `main()` - 14 edges
2. `WooBatchManager` - 13 edges
3. `run_image_bot()` - 9 edges
4. `run_sync_bot()` - 9 edges
5. `run_inventory_cleaner()` - 8 edges
6. `sincronizar_csv()` - 8 edges
7. `run_image_uploader()` - 7 edges
8. `log_activity()` - 6 edges
9. `process_ai_enrichment()` - 6 edges
10. `woocommerce_request()` - 6 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `WooBatchManager`  [EXTRACTED]
  force_woo_images.py → woo_batch_manager.py
- `process_ai_enrichment()` --calls--> `WooBatchManager`  [EXTRACTED]
  ia_webhook_trigger.py → woo_batch_manager.py
- `main()` --calls--> `run_ia_webhook_trigger()`  [EXTRACTED]
  main_orchestrator.py → ia_webhook_trigger.py
- `main()` --calls--> `run_image_bot()`  [EXTRACTED]
  main_orchestrator.py → image_bot.py
- `main()` --calls--> `run_image_uploader()`  [EXTRACTED]
  main_orchestrator.py → image_uploader.py

## Import Cycles
- None detected.

## Communities (25 total, 0 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (38): calculate_sale_price(), clean_price_to_float(), close_banners(), create_product_in_woocommerce(), detect_csv_encoding(), download_category_csv(), enviar_reporte(), escribir_como_humano() (+30 more)

### Community 1 - "Community 1"
Cohesion: 0.13
Nodes (22): _load_logs(), log_activity(), Registra una nueva actividad en el dashboard.          Categorías sugeridas: Sin, _save_logs(), Exception, generate_daily_snapshot(), load_json(), save_json() (+14 more)

### Community 2 - "Community 2"
Cohesion: 0.13
Nodes (14): main(), load_state(), preload_wc_ids(), Carga IDs de productos en paralelo., Sube imagen binaria a WP Mediateca., run_image_uploader(), save_state(), upload_single_image() (+6 more)

### Community 3 - "Community 3"
Cohesion: 0.13
Nodes (8): ejecutar_orquestador(), get_allowed_chat_id(), job_wrapper(), Ejecuta el main_orchestrator.py como subproceso con lock para evitar ejecuciones, Loop infinito para el crontab (schedule), Wrapper para la tarea de schedule que lanza el thread.     Detecta si el job se, Obtiene el Chat ID numérico para comparar, run_schedule()

### Community 4 - "Community 4"
Cohesion: 0.36
Nodes (9): download_image(), harvest_single_sku(), load_state(), Descarga una imagen y la guarda localmente., Intenta obtener la imagen de un SKU usando una instancia de driver (o pronto usa, run_image_bot(), save_state(), setup_driver() (+1 more)

### Community 5 - "Community 5"
Cohesion: 0.33
Nodes (8): load_state(), preload_wc_ids(), process_ai_enrichment(), process_single_ia_request(), Carga todos los IDs de productos de una vez para evitar GETs individuales (Optim, Procesa una sola solicitud a n8n., run_ia_webhook_trigger(), save_state()

### Community 6 - "Community 6"
Cohesion: 0.33
Nodes (8): get_all_woo_products(), load_state(), Obtiene todos los productos publicados de WooCommerce., Ejecuta la lógica de limpieza y gestión de inventario., run_inventory_cleaner(), save_state(), init_woocommerce_api(), Inicializa la conexión con la API de WooCommerce.          Returns:         A

### Community 7 - "Community 7"
Cohesion: 0.25
Nodes (8): assign_task(), broadcast(), init_team(), Asigna una nueva tarea con soporte para dependencias., Envía un mensaje a todos los miembros del equipo., Envía un mensaje al buzón de un agente específico., Inicializa la infraestructura del equipo., send_message()

### Community 8 - "Community 8"
Cohesion: 0.36
Nodes (7): check_intcomex(), check_n8n(), check_woo(), Verifica la API de WooCommerce., Verifica si n8n está arriba., Verifica si el portal de Intcomex es accesible., run_health_check()

### Community 9 - "Community 9"
Cohesion: 0.53
Nodes (5): assign_custom_placeholders(), get_placeholder_media_id(), load_json(), Obtiene el ID del medio en WordPress o lo sube si no existe / no se encuentra., save_json()

### Community 10 - "Community 10"
Cohesion: 0.70
Nodes (4): fix_bad_images(), get_hash(), load_json(), save_json()

### Community 11 - "Community 11"
Cohesion: 0.67
Nodes (3): audit_descriptions(), looks_like_ai_content(), Detecta si el contenido parece enriquecido por IA basado en etiquetas HTML

### Community 12 - "Community 12"
Cohesion: 0.83
Nodes (3): clean_generic_images(), load_json(), save_json()

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `WooBatchManager` connect `Community 2` to `Community 5`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **Why does `run_image_uploader()` connect `Community 2` to `Community 1`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Why does `main()` connect `Community 1` to `Community 2`, `Community 4`, `Community 5`, `Community 6`, `Community 8`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **What connects `Registra una nueva actividad en el dashboard.          Categorías sugeridas: Sin`, `Obtiene el ID del medio en WordPress o lo sube si no existe / no se encuentra.`, `Detecta si el contenido parece enriquecido por IA basado en etiquetas HTML` to the rest of the system?**
  _53 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.06477732793522267 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.13333333333333333 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.12987012987012986 - nodes in this community are weakly interconnected._