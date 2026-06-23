# Informe de Seguridad - DashboardBot TuPartnerTI

**Fecha de revision:** 23 de junio de 2026  
**Objetivo revisado:** `https://dashboardbot.tupartnerti.cl/dashboard/index.html`  
**Tipo de revision:** Analisis no intrusivo de superficie publica

## Alcance

La revision se realizo sobre recursos publicos entregados normalmente por el sitio al navegador: HTML, JavaScript, CSS, cabeceras HTTP y archivos JSON referenciados por el frontend.

No se realizaron pruebas destructivas, fuerza bruta, fuzzing, explotacion activa, bypasses de autenticacion ni acciones que pudieran afectar disponibilidad o integridad del servicio.

## Resumen Ejecutivo

Se identifico una exposicion publica de datos internos comerciales y operacionales del dashboard. La pagina carga archivos JSON directamente desde rutas publicas sin autenticacion, incluyendo informacion de productos, costos, precios, stock, estados de sincronizacion y logs del orquestador.

El hallazgo mas critico es que cualquier usuario con la URL puede acceder a datos internos mediante endpoints JSON publicos. Adicionalmente, el frontend usa `innerHTML` para insertar datos dinamicos, lo que puede habilitar XSS almacenado o DOM-based si alguno de esos datos puede ser influenciado por fuentes externas como CSV, WooCommerce, proveedores o procesos internos.

## Hallazgos

## 1. Datos internos publicados sin autenticacion

**Severidad:** Critica  
**Estado:** Confirmado  
**Tipo:** Exposicion de informacion sensible

### Evidencia

Los siguientes archivos JSON responden publicamente con `HTTP/1.1 200 OK`:

```text
https://dashboardbot.tupartnerti.cl/data_activa/estado_productos.json
https://dashboardbot.tupartnerti.cl/data_activa/historico_stats.json
https://dashboardbot.tupartnerti.cl/data_activa/actividades.json
```

El archivo `estado_productos.json` tiene un tamano aproximado de **526 KB** y contiene informacion detallada del catalogo.

Campos observados en la muestra:

```text
sku
nombre
cost_price
sale_price
stock
categoria_principal
categoria_csv
subcategoria_csv
subido_a_woo
ia_mejorado
status_web
motivo_estado
ultima_sincronizacion
ultima_ia
```

El archivo `actividades.json` expone eventos operacionales como:

```text
Orquestador iniciado
Orquestador finalizado
Iniciando Fase A: Sincronizacion
Fase C Completada. Vinculadas/Actualizadas
Iniciando Fase C: Subida a Woo
Iniciando Fase E: IA Enrichment
```

### Impacto

Esta exposicion permite a terceros consultar:

- Costos internos de productos.
- Precios de venta.
- Stock disponible.
- Estados de publicacion en WooCommerce.
- Funcionamiento y horarios del orquestador.
- Volumenes procesados por fase.
- Estado de sincronizacion e IA de productos.

Esto puede derivar en:

- Inteligencia comercial por competidores.
- Analisis de margenes.
- Monitoreo de inventario.
- Preparacion de ataques dirigidos.
- Exposicion de patrones operacionales internos.

### Recomendacion

- Poner `/dashboard/` y `/data_activa/` detras de autenticacion.
- No servir archivos JSON internos directamente desde rutas publicas.
- Crear una API autenticada que entregue solo los campos estrictamente necesarios.
- Eliminar campos sensibles del frontend, especialmente `cost_price`, estados internos y logs detallados.
- Aplicar control de acceso a nivel Nginx o aplicacion.
- Separar datos publicos de datos administrativos.

## 2. Riesgo de XSS almacenado o DOM-based por uso de innerHTML

**Severidad:** Alta  
**Estado:** Riesgo confirmado por patron inseguro  
**Tipo:** Cross-Site Scripting potencial

### Evidencia

El archivo `app.js` inserta datos dinamicos usando `innerHTML`.

Campos dinamicos afectados:

```text
p.sku
p.nombre
act.message
act.categoria
act.icon
```

Ejemplos de patron observado:

```javascript
row.innerHTML = `
    <td>${p.nombre.substring(0, 50)}</td>
`;
```

```javascript
container.innerHTML += `
    <div class="activity-item">
        <div class="activity-details"><p class="activity-msg">${msg}</p></div>
    </div>
`;
```

### Impacto

Si un nombre de producto, mensaje de actividad, categoria, SKU o icono puede ser alterado desde una fuente externa o semiconfiable, podria inyectarse HTML o JavaScript que se ejecutaria en el navegador de quien abra el dashboard.

El riesgo aumenta porque el dashboard parece estar orientado a administracion interna.

### Recomendacion

- Reemplazar `innerHTML` por `textContent` para datos no confiables.
- Construir elementos con `document.createElement`.
- Sanitizar cualquier HTML permitido con una libreria confiable como DOMPurify.
- Validar y normalizar datos antes de escribirlos en los JSON.
- Aplicar una `Content-Security-Policy` restrictiva para reducir impacto si ocurre una inyeccion.

## 3. Faltan cabeceras de seguridad HTTP

**Severidad:** Alta  
**Estado:** Confirmado  
**Tipo:** Hardening insuficiente

### Evidencia

La respuesta principal no incluye cabeceras defensivas importantes.

Cabeceras observadas:

```text
HTTP/1.1 200 OK
Server: nginx/1.24.0 (Ubuntu)
Content-Type: text/html
Content-Length: 12453
Connection: keep-alive
Last-Modified: Tue, 26 May 2026 21:41:13 GMT
ETag: "6a161379-30a5"
Accept-Ranges: bytes
```

Cabeceras no observadas:

```text
Content-Security-Policy
Strict-Transport-Security
X-Content-Type-Options
Referrer-Policy
Permissions-Policy
X-Frame-Options
```

### Impacto

- Mayor impacto ante XSS.
- Riesgo de clickjacking.
- Politicas de permisos del navegador no restringidas.
- Posible filtracion innecesaria de referencias.
- Falta de endurecimiento del transporte HTTPS mediante HSTS.

### Recomendacion

Agregar cabeceras de seguridad en Nginx:

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
add_header X-Frame-Options "DENY" always;
```

Tambien se recomienda implementar una `Content-Security-Policy` ajustada a las dependencias usadas.

## 4. Dependencias externas sin SRI y una dependencia sin version fija

**Severidad:** Alta  
**Estado:** Confirmado  
**Tipo:** Riesgo de supply chain

### Evidencia

El HTML carga dependencias externas:

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
```

Problemas observados:

- `chart.js` se carga sin version fija.
- No se usa atributo `integrity`.
- No se usa atributo `crossorigin`.

### Impacto

- Cambios inesperados por actualizaciones de dependencias.
- Riesgo ante compromiso de CDN o paquete.
- Dificulta implementar una politica CSP estricta.

### Recomendacion

- Fijar version exacta de Chart.js.
- Usar Subresource Integrity.
- Agregar `crossorigin="anonymous"`.
- Considerar servir dependencias criticas desde el mismo dominio.

Ejemplo:

```html
<script
  src="https://cdn.jsdelivr.net/npm/chart.js@4.4.9/dist/chart.umd.min.js"
  integrity="..."
  crossorigin="anonymous"></script>
```

## 5. Divulgacion de version exacta del servidor

**Severidad:** Media  
**Estado:** Confirmado  
**Tipo:** Information disclosure

### Evidencia

El servidor expone:

```text
Server: nginx/1.24.0 (Ubuntu)
```

### Impacto

La divulgacion de version facilita fingerprinting y ayuda a un atacante a priorizar vulnerabilidades conocidas para esa version o plataforma.

### Recomendacion

Configurar Nginx para no exponer version:

```nginx
server_tokens off;
```

Tambien revisar si algun proxy, balanceador o capa adicional agrega cabeceras con informacion sensible.

## 6. Cache busting desde frontend sin politica explicita de privacidad

**Severidad:** Media  
**Estado:** Confirmado  
**Tipo:** Control de cache insuficiente para datos sensibles

### Evidencia

El JavaScript solicita datos agregando un timestamp:

```javascript
fetch(url + '?t=' + Date.now())
```

Sin embargo, los JSON publicos no muestran una politica explicita como:

```text
Cache-Control: no-store
```

### Impacto

Datos sensibles podrian quedar almacenados en caches intermedios o en navegadores. El parametro `?t=` reduce reutilizacion de cache, pero no reemplaza una politica formal de cache para informacion sensible.

### Recomendacion

Para datos sensibles:

```nginx
add_header Cache-Control "no-store" always;
```

Para archivos estaticos no sensibles, usar versionado de assets y cache fuerte.

## Aspectos positivos observados

- HTTP redirige a HTTPS correctamente con `301`.
- El listado directo de `/data_activa/` responde `403 Forbidden`.
- No se observaron tokens API visibles en HTML o JavaScript durante esta revision.
- No se observaron formularios de login ni endpoints de escritura desde la revision pasiva.

## Priorizacion de remediacion

1. Proteger `/dashboard/` y `/data_activa/` con autenticacion.
2. Retirar datos sensibles de los JSON publicos, especialmente `cost_price`, estados internos y logs operacionales.
3. Reemplazar `innerHTML` con APIs DOM seguras.
4. Agregar cabeceras de seguridad, especialmente CSP y HSTS.
5. Fijar versiones de dependencias externas y usar SRI.
6. Ocultar la version exacta de Nginx.
7. Definir politicas de cache adecuadas para datos sensibles.

## Conclusion

La vulnerabilidad principal es la exposicion publica de datos internos comerciales y operacionales. El dashboard no solo muestra metricas visuales, sino que entrega directamente archivos JSON con informacion sensible que puede ser consultada sin autenticacion.

El segundo riesgo mas relevante es la posibilidad de XSS almacenado o DOM-based por el uso de `innerHTML` con datos dinamicos. Aunque no se exploto este vector, el patron de implementacion es inseguro si cualquier dato mostrado puede venir de fuentes externas o modificables.

La mitigacion recomendada es tratar el dashboard como una superficie administrativa: autenticacion obligatoria, API con control de acceso, minimizacion de datos, sanitizacion del frontend y cabeceras de seguridad estrictas.
