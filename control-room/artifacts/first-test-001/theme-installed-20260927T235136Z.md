# PR-TEST-001 · landing instalada en tema no publicado

Registro UTC: 2026-09-27T23:51:36Z
Estado: INSTALLED_UNPUBLISHED_READBACK_VERIFIED. No es un lanzamiento comercial.

## Resultado real

Se duplicó Horizon sin publicar la copia. La copia final es `gid://shopify/OnlineStoreTheme/205996360023`, nombre `rato. · PR-TEST-001 · borrador`, rol `UNPUBLISHED`. La lectura posterior devuelve processing=false y processingFailed=false.

Se instalaron cuatro archivos mediante themeFilesUpsert. Las dos operaciones devolvieron userErrors vacío. Después se consultaron los archivos de nuevo y sus tamaños y MD5 coinciden exactamente con los bytes locales utilizados en las pruebas:

| Archivo | Bytes | MD5 |
| --- | ---: | --- |
| sections/pr-product-story.liquid | 20199 | 589f0eaaa9e8fd440b38ab1adcf18e03 |
| layout/pr-preview.liquid | 762 | 26d4450328a473f7bffad895762ec586 |
| templates/index.json | 3521 | 13159ecc87608892eadf2945f80d3e14 |
| templates/page.pr-test-001.json | 3521 | 13159ecc87608892eadf2945f80d3e14 |

Editor: https://admin.shopify.com/store/ghg2tn-1u/themes/205996360023/editor
Ruta prevista de previsualización: https://ghg2tn-1u.myshopify.com/?preview_theme_id=205996360023

La portada del tema duplicado usa el layout pr-preview y la sección. La plantilla page.pr-test-001 también está instalada, pero NO se ha creado ni publicado una entidad Page ni una nueva URL de landing comercial. page_url del experimento debe continuar vacío. El enlace de preview NO se debe utilizar como destino de anuncios.

## Diseño y comportamiento

Conserva la dirección editorial cálida y el planteamiento de un solo producto: titular, explicación, tres beneficios, tres pasos y dos preguntas desplegables. Navegación por anclas y diseño adaptable. Hay una banda permanente de vista de trabajo y los textos no comprobados se identifican como provisionales.

Se añadió preview_only para que la composición pueda verse aunque un producto DRAFT no sea resoluble en el escaparate. No se cambió el producto a ACTIVE para resolver esto. Esta vista NO es control de acceso ni una comprobación automática de veracidad. Todos los interruptores de oferta, medios y publicación siguen desactivados, y todos los bloques mantienen verified=false. El código de la vista de trabajo no ofrece compra, precio comercial, reserva ni formulario de correo.

La sección deriva de la original con blob 722a063f08d1891d41b329b542b8c2ac6a34751d, pero esta versión instalada no es idéntica. No reinstalar automáticamente el archivo antiguo porque se perdería el modo de revisión. El layout específico evita arrastrar la cabecera, catálogo y formulario de suscripción de muestra de Horizon a esta portada; no se modificaron esos archivos originales. Se mantiene content_for_header, sin manipular los scripts que genera Shopify; esto no acredita una auditoría completa de cookies o privacidad.

Fotos, vídeo de uso y modelo 3D reales siguen pendientes. Se muestran espacios identificados, no un producto inventado ni eficacia simulada. El código admite medios revisados, reproducción manual y modelo bajo demanda; no se ha probado un modelo real ni entregado una demostración comercial.

## Comprobaciones realizadas y límites

34 comprobaciones locales superadas: estructura/schema, separación de flags, bloques provisionales, ausencia de formulario/carrito en código propio, layout, y fixture HTML de la rama de previsualización en Chromium a 320/360/390/768/1440 px. FAQ nativa con y sin JavaScript, reinserción del componente y ausencia de errores JS en esa fixture. Se corrigió un desbordamiento del espacio de fotografía en 320 px y se repitieron todas las pruebas. JavaScript comprobado además con node --check.

La fixture utiliza CSS/JS exactos del módulo, pero NO es el motor Liquid de Shopify. No se han realizado pruebas en Safari/iPhone real, compras, cobros, medición, Core Web Vitals ni contenido audiovisual real. Las operaciones de Shopify aceptaron los archivos, pero eso no equivale a una prueba visual completa. El intento de abrir la URL de preview con la herramienta web devolvió URL no accesible; no se ha visto desde esta sesión el resultado renderizado dentro del editor autenticado.

Paquete local entregado en la conversación: PR-TEST-001-Tema-Instalado.zip, con código, configuraciones, generador, fixture, capturas locales, manifiesto y resultados. Es un paquete de extensión/pruebas, NO un tema Shopify completo para subir como ZIP.

## Verificación de preservación

MAIN continúa siendo Horizon `gid://shopify/OnlineStoreTheme/205995376983`. La lectura de sus archivos coincide con la base leída antes de editar la copia: layout/theme.liquid 00c8171bf7046ca93dacaa0254a2ea34; sections/header-group.json c695f9687a58acbcf7509343b186fe46; sections/footer-group.json ff2eda8aeca97f6132b73996b931f35d; templates/index.json c828067cbc7ea00ac09f4927419385ce. No hubo escrituras dirigidas a MAIN.

get-product volvió a confirmar que `gid://shopify/Product/11226693370199` sigue DRAFT, con inventario 0 y sin imágenes. No se creó otro producto. No se publicó un tema, no hubo pedido, publicidad, plan nuevo ni contacto con el proveedor. Presupuesto autorizado continúa en 0 EUR.

## Próxima acción

Trabajar sobre esta copia e identificadores, leyendo primero la versión actual de Shopify. La prioridad pendiente es confirmar stock/portes/coste facturado y autorización de medios del SKU 100102, o cambiar de candidatura si no cumple. La solicitud al proveedor sigue redactada pero NO enviada; no tratarla como respondida. Obtener activos utilizables y después comprobar la landing en Shopify, la medición y el circuito de compra antes de solicitar el GO comercial.

El propietario ya confirmó la dirección correcta de contacto de la tienda. No volver a pedirle confirmar la dirección; su cambio todavía no se ha aplicado desde este chat. Se ha proporcionado el enlace de Configuración general.

No modificar control-room/state.json ni estados ajenos. No presentar estas acciones del coordinador como ejecuciones de otros agentes. No crear otra copia de tema por defecto.

## Referencias técnicas consultadas

https://shopify.dev/docs/storefronts/themes/architecture/templates/json-templates
https://shopify.dev/docs/storefronts/themes/architecture/layouts
https://shopify.dev/docs/api/admin-graphql/2026-01/mutations/themeFilesUpsert

Los nombres de tipos y operaciones se contrastaron con graphql_schema y las operaciones se validaron antes de ejecutarlas.
