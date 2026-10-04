# Uso de la Inteligencia Artificial en el proyecto Sombra

Usamos IA (Claude, de Anthropic, mediante Claude Code) como herramienta de apoyo. Somos estudiantes, no expertos en estructuras ni en presupuestos de obra, y eso condicionó cómo la usamos. **Las decisiones del proyecto fueron del equipo.**

## En qué la usamos

**1. Tareas que sobrepasaban nuestros conocimientos**
- Cálculo de orientación y zonas de sombra del patio (`calculos/sombra_orientacion.py`).
- Recomendaciones estructurales: postes, anclajes y bases. Pedimos siempre la opción con más margen de seguridad.
- Modelado y renders en Blender (`calculos/`).

**2. Tareas repetitivas del presupuesto que no aportaban aprendizaje**
- Buscar el precio de materiales chicos, como arandelas, pegamento químico, tornillería y herrajes. Los cargamos y revisamos en `entrega-final/Gastos.xlsx`.

**3. Primeras versiones de documentos**
- La IA generó borradores iniciales de algunos `.docx` y `.xlsx`. Los revisamos, corregimos y completamos nosotros.

## Cómo controlamos lo generado

**Todo lo generado por la IA fue revisado por el equipo, teniendo en cuenta que no somos expertos.**

- Leímos y entendimos cada contenido antes de incluirlo, y pedimos explicaciones, no solo resultados.
- Contrastamos precios con cotizaciones (`Cotizaciones/`) y medidas con las del patio real.
- Ante la duda en algo estructural, elegimos la solución más conservadora.
- Detectamos y corregimos errores, por ejemplo la orientación del norte, que estaba 7° al lado equivocado. Se rehizo todo lo que dependía de ese dato.
- Lo que depende de un experto, como la resistencia final de anclajes y estructura, debería validarlo un profesional antes de construir.

## Qué no hicimos

- No le pedimos que hiciera el proyecto por nosotros.
- No incluimos datos que no pudimos revisar o entender.
- No presentamos como definitivo algo que requiere validación profesional.
