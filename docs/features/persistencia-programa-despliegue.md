# Persistencia del programa entre despliegues (pendiente)

## Problema
Lo cargado en la pestaña 📋 Programa (tablas `competition`, `competition_entry`,
`competition_watch`) se pierde en cada *redeploy*/reinicio en Streamlit Community
Cloud, porque el disco es **efímero**: solo sobrevive lo que está en git.

Además, `export_anonymized` (`fecna_agent/db.py`) **no copia** esas tablas, así
que `data/fecna_public.db` del repo nunca incluye programas.

## Trampa de privacidad
El programa contiene **nombres completos de menores + su horario** (qué prueba,
a qué hora). Versionarlo en un repo público expondría eso (más sensible que el
ranking). Choca con la regla de privacidad del proyecto: *no subir información
privada / datos de menores*.

## Opciones evaluadas
1. **Solo local (recomendado).** Cargar programas en la máquina (persisten en
   `data/fecna.db`); el despliegue público queda solo lectura de rankings.
   Implementación: ocultar la subida y el seguimiento cuando `webui.PUBLIC`.
   Cero costo, cero riesgo.
2. **Base externa privada** (Turso/libSQL — compatible con SQLite, capa gratis;
   o Supabase Postgres). La app lee/escribe vía secreto y se protege con
   contraseña. Persiste entre deploys; los datos viven en una DB privada, no en
   el repo. Requiere montar el servicio y configurar un secreto.
3. **Versionar el programa en el repo.** Simple pero expone menores: descartada
   por privacidad salvo que el repo/app sea privado.

## Decisión
Pendiente. Falta definir si el despliegue es público o privado y si se necesita
cargar programas desde la nube o basta hacerlo en local.

## Relacionado
- Anonimización y despliegue: `DEPLOY.md`.
- La subida de programa hoy **no** está gateada por `webui.PUBLIC` (solo el botón
  de borrar lo está): si se opta por la opción 1, hay que gatearla.
