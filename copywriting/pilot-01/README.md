# Copywriting — Piloto 01: MeterTruth

Versión 0.1 · 27/09/2026 · Propuesta editorial, no publicada como home.

## Objetivo

Aplicar el método del curso aportado por el usuario a una página de MeterTruth antes de abrir un negocio distinto. Una acción principal: comparar archivos y revisar evidencia. No hay campañas, compras, clientes contactados ni modificaciones de facturación.

La maqueta mantiene el inglés de la interfaz actual. Este documento de trabajo está en español.

## Evidencia y estado

Repositorio inspeccionado en el commit `f8958724399c6d13cfa31e3c73a3f651ce07350c`:

- `README.md`: versión 0.9, capacidades y límites.
- `app.py`, función `home()`: texto actual, formularios y rutas; blob `1c2367fb25654f46fd3fc0b76a6ce025cab97a9e`.
- `demo_stripe_portfolio_report.json`: fixture sintético de Stripe agregado; blob `9ac7de2eb0cd49d4b41859365735ef715766381b`.

El acceso a la web desplegada mediante la conexión Vercel fue denegado. «Texto actual» significa el código inspeccionado, no una captura de producción. No se ha reejecutado el motor ni la batería completa del producto.

Fuente metodológica: `copywritting.txt`, curso de Anna Raventós en el canal de Adrián Sáenz: 20:05–22:24 (cuatro pasos), 26:35–28:16 (cuestionario), 41:26–44:48 (home), 3:17:16–3:24:00 (auditoría).

## Método y pendientes

1. **Conocer al cliente ideal:** hipótesis definida; entrevistas pendientes.
2. **Estudiar el mercado:** investigación específica pendiente. No se afirma diferenciación competitiva validada.
3. **Escribir un borrador:** creado en `index.html`.
4. **Auditar y corregir:** revisión editorial y técnica de la maqueta, no validación comercial.

Se usa la estructura de home del curso. Los siete bloques son problema, dolor, deseo, beneficio del resultado, revelación, objeción y llamada a la acción. La auditoría conserva naturalidad, ritmo, dudas, economía de palabras y triple C: contexto, contraste, coherencia.

## Hipótesis de público

Una persona de ingeniería, operaciones de facturación o finanzas de un SaaS por uso, con registros de producto y uso medido que necesita comparar. Es una hipótesis de este proyecto, no una entrevista ni una cita de un cliente.

## Cambio central

Original del código: **Find usage that never became revenue.**

Propuesta: **Find the gaps between product usage and billing.**

Texto de apoyo: Compare your product events with metered usage. Get an evidence-backed list of discrepancies and their estimated financial impact, so your team knows what to investigate.

El original ya es concreto. La hipótesis de mejora es cubrir también duplicados y sobrecobros, explicar el informe y no equiparar discrepancia con recuperación de ingresos. No se afirma que el nuevo titular convierta mejor.

La acción principal propuesta al integrar es `Compare usage files`, con ancla al formulario existente. Se mantiene el acceso a preflight, Stripe e historial. La maqueta no tiene formulario: prepara el escaneo y permite inspeccionar el ejemplo. El único enlace externo abre la beta existente y advierte que el acceso no está verificado.

## Afirmaciones y límites

- CSV/JSON y otros formatos indicados están documentados; el primer escaneo compara origen con uso medido, no toda la factura.
- Facturas, créditos y precios efectivos necesitan entradas opcionales compatibles.
- Impacto estimado no equivale a deuda exigible, dinero recuperado ni resultado de cliente.
- Stripe es de solo lectura y agregado; no prueba cada evento individual.
- No se retienen archivos originales ni claves, pero sí hallazgos, evidencia, nombres saneados y resúmenes.
- SQLite es local a la máquina que ejecuta la app. En alojamiento, es el servidor y no el navegador. La evidencia puede ser sensible; en Vercel el historial es efímero.
- No usar datos de producción antes de revisar autenticación, retención y almacenamiento.

El ejemplo conserva los valores del fixture: `cus_demo_a` 200 frente a 190, `cus_demo_c` 200 frente a 220; posible infracobro €0,20 y sobrecobro €0,40. Está rotulado como sintético, agregado y estático. No son ahorros obtenidos ni ejecución en directo.

## Entregables y pruebas

- `index.html`: maqueta independiente sin scripts, fuentes remotas ni captura de datos.
- `copy_changes.json`: 13 sustituciones propuestas, NO aplicadas a app.py.
- `test_preview.py`: 10 pruebas estructurales, ejecutadas correctamente con biblioteca estándar.
- `QA.json`: resultado de navegación en Chromium, escritorio 1440×1000 y móvil 390×844; enlaces internos, FAQ, teclado, ausencia de desbordamiento y de peticiones externas automáticas.

Ejecutar las pruebas: `python -m unittest discover -s copywriting/pilot-01 -p 'test_*.py' -v`.

Estas pruebas no miden conversión ni sustituyen las pruebas de integración del producto. No hay entrevistas completadas, clientes captados, ingresos o mejoras porcentuales verificadas.

## Siguiente validación

Probar comprensión con cinco personas del perfil previsto. Preguntar qué se compara, qué archivos necesitan, qué reciben y si un hallazgo significa recuperación de dinero. Conservar respuestas reales.

Criterio operativo propuesto: cuatro de cinco entienden el flujo y ninguna interpreta recuperación garantizada. No es significación estadística. Después medir escaneo completado e informe revisado, no solo clics. Métricas actuales: sin medir. No se ha instalado analítica.

## Integración segura

Recuperar app.py actualizado y reconciliar cualquier cambio del blob antes de editar. Aplicar sustituciones solo en `home()`, mantener campos/defaults/validaciones y ejecutar la batería completa. Revisar una vista previa autenticada antes de publicar. Extraer el CSS embebido a un archivo externo al integrar: la CSP de la app no admite estilos inline y no debe debilitarse.

Este PR solo añade materiales de copywriting. No modifica app.py, RecoveryCore, seguridad, precios, datos ni la página pública.
