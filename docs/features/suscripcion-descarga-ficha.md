# Feature (por hacer): suscripción de pago para descargar la ficha

**Estado:** propuesto / por implementar
**Origen:** idea registrada el 2026-06-14
**Objetivo:** que la descarga de la ficha del nadador (PNG/PDF) en la pestaña
**Ficha** requiera una **suscripción de pago** activa.

> Este documento guarda la idea y el plan para no perderlos. No hay código de
> esta funcionalidad todavía. Antes de implementar, decidir lo de "Decisiones
> pendientes".

---

## 1. Realidad del entorno (a resolver primero)

- **Streamlit no es un servidor web con rutas.** No puede exponer un endpoint
  `/webhook` para recibir avisos del proveedor de pago. O se usa un backend
  aparte para webhooks, o se **consulta el estado de la suscripción al proveedor
  en cada carga** (polling) en vez de webhooks.
- **El disco de Streamlit Cloud es efímero.** La base SQLite local no sirve para
  guardar suscripciones: se necesita un **almacén externo persistente**
  (Postgres en Supabase/Neon, Firebase) o usar al **proveedor de pagos como
  fuente de verdad**.
- **Streamlit Community Cloud (gratis) no es adecuado para cobrar** (términos de
  servicio, fiabilidad y manejo de secretos). Un producto de pago debería ir en
  un host propio (Render, Railway, Fly, VM, Hugging Face). Probablemente sea el
  primer cambio.

## 2. Piezas a construir

1. **Identidad del usuario (login).** Saber quién paga. Streamlit tiene
   `st.login()` (OIDC: Google/Auth0/…) desde la 1.42. Alternativa más simple:
   **clave de licencia** (el usuario compra y recibe una clave que pega en la app).
2. **Pasarela de pago / suscripción.** Por ser contexto colombiano (COP, PSE,
   Nequi, tarjeta): **Wompi, Mercado Pago, PayU, ePayco o Bold**. Todas ofrecen
   pagos recurrentes y página de pago alojada. (Stripe tiene cobertura limitada
   para entidades colombianas.)
3. **Registro de derechos (entitlement).** Tabla `usuario → estado + vigencia`,
   en almacén externo o derivada de la API del proveedor.
4. **Candado en la página de Ficha.** Generar y mostrar los botones de descarga
   solo si hay suscripción activa; si no, mostrar CTA "Suscríbete".
5. **Sincronización de estado.** Webhooks (requiere backend) o **polling** de la
   API del proveedor por sesión (encaja mejor con Streamlit).

## 3. Camino recomendado (MVP)

Sin montar webhooks:

```
Usuario entra → st.login() (OIDC) → email
   ↓
¿Suscripción activa? → consulta API del proveedor por email (cacheado unos min)
   ↓ sí                          ↓ no
botones PNG/PDF            enlace a la página de pago del proveedor (prellenada
                          con su email); al volver, el polling detecta el pago
```

- El cobro real lo hace la **página alojada del proveedor** (menos riesgo PCI).
- El estado se verifica en el **servidor** (Python): el candado va donde se
  generan los bytes → seguro por diseño.

**Variante sin login:** modelo de **clave de licencia**. El usuario compra
(enlace del proveedor), recibe una clave, la pega en la app y se valida contra
el proveedor o una tabla. Menos fricción técnica, algo más manual.

## 4. Cambios concretos en este código

- **`pages/ficha.py`**: envolver el bloque de descargas (hoy llama
  `_ficha_png(html)` / `_ficha_pdf(html)` y los `st.download_button`) en
  `if billing.usuario_activo(): … else: CTA de suscripción`. Como
  `st.download_button` calcula los bytes en el servidor, basta con no generarlos
  si no hay suscripción (candado real, no solo visual).
- **Nuevo módulo `fecna_agent/billing.py`**: `login()/usuario_actual()`,
  `suscripcion_activa(email)` (consulta proveedor o almacén) y cache.
- **Secrets** (`st.secrets` / variables de entorno): API key e IDs de plan del
  proveedor, config OIDC, credenciales del almacén. Nunca en el repo.
- **`requirements.txt`**: SDK del proveedor (p. ej. `mercadopago`), `Authlib`
  para OIDC y cliente del almacén (p. ej. `supabase`/`psycopg`).
- **Hosting**: mover el despliegue a un host de pago (ver punto 1).

## 5. Advertencias

- **Legal / datos personales (Colombia):** comercializar fichas personalizadas,
  sobre todo de **menores**, toca la Ley 1581 de 2012 (habeas data) y la
  vigilancia de la SIC. Aunque los datos vengan del sitio público de FECNA,
  monetizar perfiles individuales de menores puede requerir consentimiento/base
  legal. No es asesoría legal: revisar antes de cobrar.
- **Facturación/impuestos:** el cobro recurrente implica facturación electrónica
  e IVA; el proveedor ayuda, pero hay que contemplarlo.
- **Seguridad:** mantener el candado en el servidor, proteger secretos y validar
  el estado en cada descarga (cache corto). No confiar en el cliente.

## 6. Decisiones pendientes (definir antes de implementar)

- **Modelo de cobro:** suscripción mensual recurrente · pago único por ficha ·
  paquete de créditos.
- **Pasarela:** Wompi · Mercado Pago · PayU · ePayco · otra (según cuenta existente).
- **Identidad:** login con Google (OIDC) · clave de licencia.
- **Hosting:** seguir en Streamlit Cloud (no recomendado para cobrar) · mover a
  host de pago.
- **Almacén de suscripciones:** API del proveedor como fuente de verdad ·
  Postgres (Supabase/Neon) · Firebase.

## 7. Pasos de implementación (cuando se apruebe)

1. Elegir las opciones del punto 6.
2. Mover el despliegue al host elegido y configurar secrets.
3. Crear cuenta y plan en la pasarela; obtener API keys e IDs de plan.
4. Implementar `fecna_agent/billing.py` (identidad + verificación de suscripción).
5. Poner el candado en `pages/ficha.py`.
6. Probar el flujo completo (sin suscripción → pago → con suscripción →
   expiración) en sandbox del proveedor.
7. Documentar despliegue/secrets en `DEPLOY.md`.
