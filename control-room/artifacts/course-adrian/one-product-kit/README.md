# Primer módulo ejecutable de la one product store

Project Rich / rato. · strategy_id: adrian-one-product-v1 · 27 septiembre 2026

Estado: CÓDIGO GUARDADO Y PRUEBAS LOCALES COMPLETADAS. No instalado en Shopify, no desplegado en Render, sin campaña ni checkout activados. PR-TEST-001 sigue sin producto comercial seleccionado.

## Fuente docente y decisión técnica

De la transcripción aportada por el propietario:
- 00:28:01–00:31:28: tienda de un producto, marca/esqueleto reutilizables y pruebas sucesivas.
- 00:32:26–00:33:59: producto protagonista, movimiento, beneficios, uso y confianza.
- 01:03:54–01:07:36: combinar bloques personalizados y normales; probar y corregir.
- 03:17:00–03:17:44: enlace al producto, no a un catálogo innecesario.
- 03:21:24–03:32:35: cliente, dolor, solución y valor percibido.

Esta sección es nuestra implementación original de esas ideas. Los interruptores de aprobación, carga diferida, accesibilidad y tratamiento de fallos son decisiones de ingeniería del proyecto, no texto del curso. No acredita estudio íntegro de 27 horas ni resultados de negocio.

## Archivo entregado

`pr-product-story.liquid`: sección autocontenida para un tema Shopify. Incluye Liquid, CSS, JavaScript y schema; no es un tema completo ni un checkout propio.

SHA-256 de la versión probada: `ae496831d611800a1f08ed97d9d7175daddac8e36eb7b74c2b9e4127380dfb34`.
Git blob de la versión probada y leída de vuelta: `722a063f08d1891d41b329b542b8c2ac6a34751d`.
Commit inicial del código: `39a9bbc6e30c034ee4ee1b6118ae03da96497291`.

El paquete de esta conversación `project_rich_primer_test.zip` incluye además los tests de Python/Playwright, exportaciones de CSS/JS para pruebas, vídeo sintético de QA y reportes. Su copia local no es una URL de despliegue.

## Qué hace

El editor selecciona un producto; en una ficha puede utilizar el producto del contexto. Muestra nombre, introducción y fotografía correspondientes, no un objeto inventado. Añade bloques reordenables de beneficios, pasos y FAQ. El precio se obtiene del producto; no está fijado a Muda Cero ni a 39,90 EUR. Usa «Desde» cuando el precio varía y remite a la ficha para seleccionar variantes y consultar condiciones.

El vídeo procede de los medios de ese producto, tiene controles y no tiene reproducción automática por defecto. La opción de reproducción al abrir respeta movimiento reducido, pausa manual, pestaña oculta y salida de pantalla. El 3D solo se ofrece cuando hay un modelo del producto: carga la función Shopify al solicitarla, muestra un mensaje si falla y mantiene disponibles fotografía y detalles. No se genera un modelo ni un vídeo comercial por este módulo.

No contiene reseñas, contador de unidades, descuentos, píxeles, cookies de marketing, carrito propio ni llamadas de compra. Los bloques y activos pendientes tienen avisos de edición en vez de afirmaciones inventadas.

## Integración para Store Builder

1. Leer `control-room/strategy/current.json` y `control-room/strategy/plan_aplicacion_adrian.md`, después el último código y SHA. La antigua obligación de 20–50 productos está sustituida; el manual anterior se ha corregido.
2. Trabajar únicamente en copia de tema NO PUBLICADA, cuando exista conexión autorizada. No abrir cuentas, comprar planes ni comenzar renovaciones para hacer esta prueba. No eliminar la demo propia anterior ni sobrescribir versiones recientes.
3. Colocar el archivo como `sections/pr-product-story.liquid` y añadir «PR · Un producto» en el editor. No pegar el archivo entero en un bloque Custom Liquid: lleva schema y etiquetas de assets de sección.
4. No instalar a la vez los CSS/JS extraídos del ZIP: son para las pruebas; Shopify procesa las etiquetas de assets de la sección.
5. Añadir un producto real seleccionado, revisar título, beneficios, uso, FAQ, medios y derechos. Confirmar manualmente los ajustes de revisión solo después de comprobar sus fuentes.
6. En la portada elegir H1 únicamente si no hay otro título principal. En la ficha mantener H2 y el formulario nativo del tema. El módulo es presentación: no sustituye el selector de variantes ni el checkout.
7. Confirmar política de entrega completa, subtítulos/transcripción accesible del vídeo si corresponde, y funcionamiento de `Shopify.loadFeatures` / ModelViewerUI en el tema concreto. No hemos probado este runtime en una tienda real.
8. Pasar Theme Check, renderizado Liquid y pruebas con el tema real; comprobar galería, variantes, navegación y ausencia de interferencia con la ficha/medición existentes. Solo después preparar el handoff de aprobación.

## Advertencia importante de publicación

`publication_approved`, `offer_verified`, `media_verified` y los bloques `verified` son recordatorios de aprobación humana. NO verifican datos automáticamente. Desactivar esta sección NO bloquea las rutas del producto, otros botones ni el checkout de Shopify. La protección de toda la tienda depende de su modo borrador/acceso y configuración independiente.

Sin aprobación, el módulo solo se presenta en el editor; en modo público la sección no se renderiza. Esto no equivale a una política de control de acceso de todo el negocio.

## QA ejecutado

31 pruebas superadas: 14 comprobaciones de fuente/configuración y 17 pruebas de comportamiento sobre una fixture HTML local con el CSS/JS exacto extraído del módulo.

Verificado: JSON del schema, identificadores únicos, opciones de aprobación desactivadas por defecto, fuente de precio/medios del producto, ausencia de compra/ads y sintaxis JavaScript; tamaños 360/390/768/1440 px sin desbordamiento horizontal; FAQ nativa; ausencia de JavaScript; reproducción y pausa de un vídeo sintético; movimiento reducido; pausa manual y salida de pantalla; carga 3D bajo demanda, fallo, reintento, desmontaje y reinserción del componente; ausencia de errores JS en las acciones probadas.

El navegador utilizado es Chromium del sistema mediante Playwright. La fixture se cargó en memoria, sin peticiones externas; el acceso HTTP a localhost estaba bloqueado en este entorno. No se alteraron sus políticas. El vídeo de cinco segundos es un patrón técnico generado por FFmpeg, no una demostración de producto.

Límites: la fixture NO es salida de Shopify Liquid. No se dispuso de renderizador Liquid/Theme Check; el intento de obtener un parser adicional no terminó. Los tests de ModelViewerUI usan un doble de prueba, no renderizado 3D real ni hardware WebGL. No se ha probado iPhone Safari, producción, pagos, AutoDS, accesibilidad completa, Core Web Vitals ni conversión. No extrapolar estas 31 pruebas a autorización comercial.

Durante QA se corrigió la inicialización al reinsertar el elemento y se hizo visible el reintento tras fallo del modelo. El reporte final corresponde al hash indicado, no al primer intento.

## Referencias técnicas primarias consultadas

- Secciones: https://shopify.dev/docs/storefronts/themes/architecture/sections
- Schema: https://shopify.dev/docs/storefronts/themes/architecture/sections/section-schema
- Vídeo: https://shopify.dev/docs/api/liquid/filters/video_tag
- Modelos: https://shopify.dev/docs/api/liquid/filters/model_viewer_tag
- Medios de producto: https://shopify.dev/docs/storefronts/themes/product-merchandising/media/support-media
- Patrón oficial de carga de ModelViewerUI: https://raw.githubusercontent.com/Shopify/dawn/main/assets/product-model.js

## Handoff de negocio

Este código no elige el producto. Product Scout/Supplier deben completar una candidatura con problema, comprador, alternativa, coste/entrega y material demostrativo utilizable. Creative prepara el mensaje y dos hipótesis de anuncio del mismo producto. No completar PR-TEST-001 con números ficticios para desbloquear la interfaz. El gasto aprobado sigue en cero; presupuesto, publicación y compromisos externos requieren autorización.
