- Terminos y condiciones de la informacion
- Informar al usuario que la app no esta avalada por la fecna, pero que si se esta tomando los datos de la fecna
## Estado: implementado (2026-11-21)
- Texto en `mobile/src/legal.ts` (se edita ahí) y pantalla `mobile/src/app/terminos.tsx`, accesible con o sin sesión.
- Aviso corto en Login, Registro, Ranking, Nadador y en la ficha descargable: "NATIA es una app independiente: no está avalada por FECNA. Los datos se toman del ranking público de FECNA."
- Registro: casilla obligatoria de aceptación. El backend guarda `terms_version` y `terms_accepted_at` por usuario (`app_user`).
- Perfil → "Términos y condiciones".
- Si cambia el texto de forma importante: sube `TERMS_VERSION` en `mobile/src/legal.ts` y `api/routers/auth.py`.
- Pendiente: que un asesor legal revise el texto y agregar un correo de contacto para solicitudes sobre datos.
