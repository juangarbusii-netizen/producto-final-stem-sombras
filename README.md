# Uso de la Inteligencia Artificial en el proyecto Sombra

Este documento explica **cómo, para qué y con qué límites** usamos Inteligencia Artificial (Claude, de Anthropic) en el producto final de Sombra para el patio.

Somos estudiantes, no expertos en estructuras, cálculo de cargas, instalación de textiles ni presupuestos de obra. Lo tuvimos presente en todo momento y condicionó la forma en que usamos la IA.

---

## 1. Principio general: la IA como herramienta, no como autora

La IA **no reemplazó nuestro trabajo ni nuestras decisiones**. La usamos como ayuda en dos situaciones concretas:

1. **Tareas que sobrepasaban los conocimientos del equipo.**
2. **Tareas repetitivas del presupuesto que no aportaban aprendizaje.**

Las decisiones de fondo (qué idea elegir, cómo es la solución, por qué conviene, cuánto se invierte y cómo se recupera) las tomamos nosotros y las fundamentamos en la entrega.

---

## 2. En qué usamos la IA

### 2.1 Tareas que sobrepasaban nuestros conocimientos

Hay partes del proyecto que requieren conocimientos de ingeniería y de herramientas técnicas que todavía no tenemos. Ahí la IA nos acompañó para entender y resolver:

- **Orientación y geometría del patio:** cálculos de dónde cae el sol y qué zonas quedan siempre a la sombra o nunca a la sombra, hechos con un script de Python (`calculos/sombra_orientacion.py`) a partir de las medidas reales del patio.
- **Recomendaciones estructurales:** cantidad y ubicación de postes, anclajes y bases (ver `Recomendacion_postes_Idea2.docx`). En estos casos pedimos siempre **la opción con más margen de seguridad** y no la más barata.
- **Modelado 3D y renders en Blender:** scripts para armar detalles de anclajes y la ubicación de cámaras (`calculos/blender_detalle_anclajes.py`, `calculos/blender_botones_camaras.py`), y la regeneración de las imágenes.
- **Planilla y archivos de apoyo:** ayuda con fórmulas y estructura de las hojas de gastos y rentabilidad, y del archivo de GeoGebra del plan de pagos.

### 2.2 Tareas repetitivas del presupuesto

El presupuesto exigía buscar el precio de muchísimos materiales pequeños. Esa búsqueda es repetitiva y no nos enseña nada nuevo sobre el problema, así que se la delegamos a la IA. Por ejemplo:

- cuánto cuestan las **arandelas**,
- cuánto cuesta el **pegamento químico** para anclajes,
- y otros materiales y accesorios del mismo tipo (tornillería, herrajes, etc.).

La IA buscó y ordenó esos precios, y nosotros los cargamos y revisamos en `entrega-final/Gastos.xlsx`. Las cotizaciones que respaldan los precios principales están en la carpeta `Cotizaciones/`.

---

## 3. Cómo controlamos lo que generó la IA

Esta es la parte más importante: **todo lo generado por la IA fue revisado por el equipo**, teniendo en cuenta nuestras limitaciones.

Como no somos expertos, no podíamos limitarnos a confiar. Por eso:

- **Revisamos todo el contenido** antes de incluirlo en la entrega. Nada se copió sin leerlo y entenderlo.
- **Pedimos explicaciones**, no solo resultados, para poder entender y defender lo que presentamos.
- **Contrastamos los datos** con la realidad: los precios con cotizaciones y páginas de venta, las medidas con las del patio, los resultados con lo que vemos en el lugar.
- **Elegimos siempre el margen de seguridad**: ante la duda en algo estructural, optamos por la solución más conservadora aunque costara más.
- **Detectamos y corrigimos errores.** Por ejemplo, vimos que la orientación del norte estaba mal cargada (7° hacia el oeste en lugar de hacia el este) y se rehizo todo lo que dependía de ese dato: presentación, documentos, modelos 3D y renders. Esto muestra que la revisión humana fue necesaria y efectiva.
- **Reconocemos nuestros límites:** lo que depende de un experto (por ejemplo, la resistencia final de los anclajes o la estructura) debería ser validado por un profesional antes de construirse de verdad.

---

## 4. Qué NO hicimos con la IA

- No le pedimos que "hiciera el proyecto" por nosotros.
- No incluimos datos que no pudimos revisar o entender.
- No usamos precios o cálculos sin verificar su origen.
- No presentamos como definitivo algo que requiere validación profesional.

---

## 5. Herramienta utilizada

- **Claude (Anthropic)**, usado mediante Claude Code, trabajando directamente sobre los archivos del proyecto.

---

## 6. Estructura del repositorio (referencia)

| Carpeta / archivo | Contenido |
|---|---|
| `entrega-final/` | Entrega final: gastos, rentabilidad, plan de pagos, modelo 3D, renders, fundamentación y preguntas para la presentación |
| `calculos/` | Scripts de orientación del patio y de Blender |
| `Cotizaciones/` | Cotizaciones que respaldan los precios |
| `Ideas/`, `Renders ideas iniciales/` | Ideas iniciales y sus renders |
| `Sombra_patio_17_octubre.pptx` | Fuente de las medidas y zonas del patio |

---

## Conclusión

Usamos la IA para **aprender y avanzar más lejos de lo que nuestros conocimientos nos permitían** y para **ahorrar tiempo en tareas repetitivas**, pero la responsabilidad del proyecto es nuestra: revisamos, corregimos y entendimos lo que presentamos, siendo conscientes de que no somos expertos.
