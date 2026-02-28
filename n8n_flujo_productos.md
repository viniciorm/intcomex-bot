# Guía de Automatización en n8n: Enriquecimiento de Productos con IA

Esta guía describe el flujo paso a paso para construir la automatización en n8n que mejora las descripciones de los productos y genera imágenes genéricas (estilo premium/dark) para aquellos que no tienen foto.

## 1. Estructura del Flujo (Nodos recomendados)

1. **Schedule Trigger (o Webhook):**
   - Configura el nodo para que se ejecute en un horario de baja carga (ej. 2:00 AM todos los días).

2. **WooCommerce Node (Get Many):**
   - **Operación:** Get All / Get Many.
   - **Filtros:** Aquí está la magia. Asegúrate de filtrar los productos donde el Custom Field (meta data) `_n8n_mejorado` NO exista o sea falso. 
   - *Nota:* En la API de WooCommerce a veces es necesario traer los productos y filtrarlos usando un nodo **If** o **Filter** si la API directamente no permite buscar por la ausencia de un Custom Field.

## 2. Prompt de Generación de Imagen (Estilo Dark/Premium)

Basado en las referencias que enviaste (computadores, portátiles Alienware con RGB, impresoras y monitores curvos con iluminación dramática), el prompt exacto que debes poner en tu nodo generador de imágenes (OpenAI DALL-E 3) debería verse así (utilizando variables dinámicas de n8n):

```text
Professional studio product photography of a {{ $json.categories[0].name }}, dark moody background, cinematic low-key lighting, sleek and premium aesthetic, high-end electronics, subtle edge lighting, realistic textures, 8k resolution, minimalist setup, blank brand.
```
*(Se utiliza la categoría del producto en lugar del modelo exacto para evitar que la IA alucine detalles de un modelo específico de forma incorrecta).*

## 3. Puntos de Atención (Best Practices)

- **Filtro de Imágenes IA vs Intcomex:** El Custom Field `_n8n_imagen_ia = true` es la clave. Tu otro script de sincronización con Intcomex podrá leer este campo y, si lo encuentra, sabrá que esa foto es genérica y debe ser reemplazada tan pronto como Intcomex proporcione una foto real/oficial del producto específico.
- **Tiempo de Espera (Sleep):** Entre iteraciones del ciclo, considera poner un nodo *Wait* de 2 o 3 segundos para no gatillar los límites de uso por minuto (Rate Limits) de OpenAI ni saturar el servidor de WooCommerce.
- **Control de Errores:** Enlaza una salida de "Error Trigger" en n8n que te envíe un mensaje a Slack o Telegram si un producto falla al subirse.
- **Prueba Piloto:** Selecciona solo 1 o 2 productos manualmente por ID en el nodo inicial de WooCommerce para probar todo el flujo antes de ejecutarlo masivamente.
