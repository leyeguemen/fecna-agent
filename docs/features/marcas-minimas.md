- Poder cargar las marcas minimas para participar en el campeonato nacional.
- Que se pueda analizar desde el chat que marcas se necesitan y comparar con sus pruebas

---

## Plan propuesto (2026-11-21, pendiente de aprobar)

**Estado:** sin implementar. Hay dudas abiertas (abajo) que se resuelven antes de programar.

### Enfoque recomendado: el admin carga el documento oficial
1. **Datos:** nueva tabla de marcas mínimas asociada a un campeonato (p. ej. nacional 2026), con fecha de vigencia. Cada fila: prueba, piscina, género, categoría y tiempo mínimo.
2. **Carga (Admin):** subir el documento oficial (PDF o Excel/CSV), mostrar lo leído para revisarlo y publicar. Similar a la carga de programas de campeonato.
3. **Chat:** que responda «¿qué marcas necesita X para el nacional?» y «¿en qué pruebas ya clasifica?», comparando con sus mejores marcas (herramienta nueva en `claude_agent.py`, sobre `ranking_public` + la tabla nueva).
4. **Perfil del nadador:** resumen de pruebas donde cumple la marca o le falta poco (diferencia en segundos).

Alternativas descartadas: formulario manual (lento) y traerlas desde FECNA (no hay fuente estructurada conocida).

### Dudas abiertas
- ¿En qué formato publica FECNA las marcas mínimas (PDF, Excel, imagen)? Hace falta un **ejemplo real** del documento.
- ¿Varían por categoría de edad y por género? ¿Solo piscina larga (LC) o también corta (SC)?
- ¿Hay una ventana de tiempo en que cuentan las marcas (p. ej. solo las logradas entre fechas X e Y)?
- ¿Una sola lista nacional o varias (nacional infantil, juvenil, mayores)?
- ¿Se debe avisar al nadador seguido cuando cumple una marca mínima?


---

## Implementado (2026-11-22)
- Fuente: Reglamento FECNA 2026, art. 13 (Infantiles, Interligas, Interclubes). Piscina larga (50 m). Categoría = año del campeonato − año de nacimiento.
- Las tablas del PDF son imágenes (no se pueden leer por texto ni OCR de forma fiable): se transcribieron a `fecna_agent/minimas.py` y se cargan solas en `minimum_mark` si la tabla está vacía. El admin corrige tiempos en Config → «Cargar marcas mínimas» (permiso `cargar_minimas`).
- Pestaña «Mínimas» (permiso `ver_minimas`): «Mi nadador» (por defecto el vinculado, o buscar otro; cumple / diferencia por prueba) y «Por categoría».
- Pendiente: que el chat consulte las mínimas; aviso al cumplir una marca; la ventana de fechas en que cuentan las marcas (no está en el reglamento).
- Rarezas del propio reglamento (se cargaron tal cual): p. ej. 200 M femenino 14 años Interclubes 03:19,27 frente a 02:54,27 en las demás categorías.
