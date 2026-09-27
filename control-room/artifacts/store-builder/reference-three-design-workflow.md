# rato. — Referencia 3: dirección de arte antes de añadir efectos

Estado: REFERENCIA REVISADA / CRITERIOS GUARDADOS. No es una nueva implementación ni un despliegue.
Fecha: 2026-09-27.
Fuente: grabación aportada por el propietario, ScreenRecording_09-27-2026 19-44-19_1.mp4, duración aproximada 6 min 09 s.
Alcance: revisión visual mediante fotogramas distribuidos a lo largo de la grabación y recortes de momentos concretos. No se ha transcrito ni validado la narración. Los tiempos siguientes son aproximados. No se copian ni publican los fotogramas o los activos de terceros.

## Evidencia visual observada

- 00:00–01:10: se alternan una galería de referencias y una web con figura escultórica blanca sobre paisaje azul/verde. Se combinan un titular sans serif y una frase serif en cursiva; el sujeto y el paisaje dominan, mientras la navegación permanece discreta.
- 01:10–02:10: aparecen una referencia oscura con globo y elementos dorados y documentación titulada Site Clone. Esto muestra un proceso apoyado en referencias; no acredita la calidad ni seguridad de ejecutar el código que aparece en pantalla.
- 02:25–03:45: se trabaja una figura con capucha y un elemento luminoso naranja, presentada contra áreas blancas y oscuras. El motivo luminoso varía y el sujeto se prepara antes de integrarlo en la página. La imagen no permite establecer si el recurso final es vídeo, capas, shader o malla 3D.
- Alrededor de 04:06: documentación de un flujo dividido en análisis/extracción y reinterpretación. No se han instalado ni ejecutado sus comandos o skills externos.
- 04:15–05:35: se integra la figura en una página clara, con texto a la izquierda, sujeto a la derecha y espacio vacío reservado a la lectura; se revisa en un área de vista más estrecha.
- 05:40–06:08: se comparan variantes oscuras, verde azulado y claras de la propuesta, con estructuras relacionadas. Son ejemplos visuales, no resultados medidos de ventas o conversión.

## Interpretación para nuestro proyecto

La lección principal es la preparación del sistema visual: referencia -> composición -> activo protagonista -> integración -> comparación. No es añadir animaciones indiscriminadamente ni multiplicar agentes.

Mantener lo que el propietario ya aprobó: identidad provisional rato., tonos cálidos, carácter editorial, navegación multiproducto y vídeo/3D que aporten una experiencia cuidada. No reemplazar la marca por estatuas, temática financiera, personajes, globos dorados o el estilo de un SaaS.

### 1. Escenas con continuidad

Mantener las tres entradas Quedarse / Salir / Llevar. Cada entrada debe tener un fotograma principal, una zona segura para el titular, el mismo producto entre sus planos y un enlace inequívoco a la colección. No mezclar colores, geometrías o acabados de supuestos productos diferentes al pasar de un plano a otro.

### 2. Separar la atmósfera de la prueba del producto

El material editorial puede crear ambiente. La demostración de limpieza, ajuste, capacidad o funcionamiento debe corresponder al SKU y a una prueba real. Las piezas conceptuales actuales siguen rotuladas como conceptos y no autorizan claims, materiales, variantes o stock.

### 3. Construir la composición estática antes de animarla

Definir fondo, encuadre, tamaño de sujeto, contraste tipográfico, sombras y ubicación del CTA antes de programar la transición. El primer fotograma debe ser convincente y legible sin esperar a que se reproduzca una película.

### 4. Movimiento selectivo

Un foco visual protagonista por pantalla como criterio de diseño. Mantener vídeo real o render conceptual claramente identificado, pausable y sin audio automático. Para 3D exploratorio usar vistas general/detalle/uso con control directo. Evitar partículas, disoluciones y resplandores alrededor de todo el catálogo: en la referencia responden a un motivo concreto, no a una obligación de diseño.

### 5. Catálogo normal y presentaciones especiales

Conservar el objetivo de 20–50 productos validados. Preparar presentaciones especiales para 3–5 productos principales y una ficha reutilizable para los demás. La entrada cinematográfica no debe esconder el buscador, las colecciones, la compatibilidad ni el acceso directo al catálogo. Más recursos animados no sustituyen datos de suministro o intención de compra.

### 6. Comparación de alternativas sin cambiar toda la web

Antes de rehacer el sitio, comparar dos encuadres del mismo producto dentro de la identidad existente: editorial cálido frente a estudio de objeto de alto contraste. Mantener iguales catálogo y mensajes para evaluar composición. No abrir nuevas marcas o nuevas versiones públicas por cada referencia.

## Handoff por responsabilidad

Creative & Offer: preparar una mini ficha visual por colección con fotograma principal, encuadres secundarios, luz, textura, tono y titular corto. No introducir urgencia, reseñas o beneficios no verificados.

Store Builder: leer esta referencia junto con reference-two-cinematic-collections.md y la última versión de store-preview.html. Integrar de forma incremental, preservando filtros, buscador, fichas y controles existentes. No sustituir código reciente por una copia local antigua. Las mejoras locales anteriores y las del repositorio deben reconciliarse antes de publicar.

QA: comprobar contraste en cada plano, CTA accesible, teclado, pausa, reduced-motion, pantalla pequeña y fallback de medios. Registrar por separado pruebas de código, navegador local, dispositivo real y despliegue. No declarar éxito de pruebas que no se han ejecutado.

Finance / Supplier: ninguna de estas decisiones cambia el precio aprobado, el coste del producto o su estado comercial.

## Criterios de aceptación para una próxima integración

1. Misma identidad editorial y tres colecciones reconocibles.
2. Mensaje comprensible y acceso al catálogo visibles sin completar la animación.
3. Objeto coherente entre planos; material conceptual identificado.
4. Movimiento pausable, scroll nativo, alternativa reducida y navegación sin dependencia de WebGL o reproducción de vídeo.
5. Composición revisada en escritorio y móvil; sin texto encima de zonas de imagen que dificulten leerlo.
6. Sin compras, pagos, ads o captura de datos activados por este cambio visual.
7. Commit y despliegue comprobados antes de decir que la referencia está aplicada en la web pública.

## Estado de esta revisión

Se ha analizado la referencia y guardado el handoff. No se ha modificado el frontend, ejecutado una nueva batería de pruebas, contratado servicios, instalado paquetes externos ni publicado una nueva versión en este ciclo.
