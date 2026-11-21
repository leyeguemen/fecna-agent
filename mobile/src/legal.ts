// Términos y condiciones de NATIA. Si cambia el texto, sube TERMS_VERSION también en api/routers/auth.py.
export const TERMS_VERSION = '2026-11-21';

// Aviso corto que se muestra junto a los datos.
export const SOURCE_NOTE =
  'NATIA es una app independiente: no está avalada por FECNA. Los datos se toman del ranking público de FECNA.';

export const TERMS: { title: string; body: string }[] = [
  {
    title: '1. Qué es NATIA',
    body: 'NATIA es un asistente de natación que permite consultar rankings, marcas, evolución de nadadores y programas de campeonatos, y hacer preguntas en lenguaje natural.',
  },
  {
    title: '2. Sin aval de FECNA',
    body: 'NATIA es una aplicación independiente. No está avalada, patrocinada ni afiliada a FECNA (Federación Colombiana de Natación). El nombre FECNA se usa únicamente para indicar de dónde provienen los datos.',
  },
  {
    title: '3. Origen de la información',
    body: 'Los rankings y marcas se toman de la información pública que FECNA publica en su sitio web, y se sincronizan periódicamente. NATIA no modifica los resultados: solo los organiza y presenta.',
  },
  {
    title: '4. Exactitud y vigencia',
    body: 'La información puede tener retrasos, omisiones o diferencias respecto al sitio de FECNA, incluso por errores de la propia fuente. NATIA no sustituye los resultados oficiales: para cualquier efecto oficial, consulta directamente a FECNA o al organizador de la competencia.',
  },
  {
    title: '5. Asistente con inteligencia artificial',
    body: 'Las respuestas del chat las genera un sistema de inteligencia artificial a partir de los datos disponibles. Pueden contener errores o interpretaciones equivocadas: verifica los datos importantes en las pantallas de Ranking y Nadador.',
  },
  {
    title: '6. Datos personales',
    body: 'La app muestra nombre, club, liga, categoría, año de nacimiento y marcas de deportistas, incluidos menores de edad, tomados de una fuente pública; no muestra la fecha de nacimiento exacta. El acceso exige una cuenta. Vincular tu nadador se verifica con su fecha de nacimiento: hazlo solo con tu propia ficha o la de un menor a tu cargo. De tu cuenta guardamos tu correo y el vínculo con tu nadador, solo para prestar el servicio, y puedes eliminarlos en Perfil → Eliminar mi cuenta. Tratamos los datos conforme a la normativa colombiana de protección de datos personales (Ley 1581 de 2012). Para pedir la corrección o el retiro de los datos de un deportista, escribe a leoye.work@gmail.com.',
  },
  {
    title: '7. Uso aceptable',
    body: 'No uses la app para suplantar a otra persona, extraer datos de forma masiva ni darles un uso comercial sin permiso. El chat tiene un límite diario de preguntas por usuario.',
  },
  {
    title: '8. Cambios',
    body: 'Podemos actualizar estos términos. La versión vigente y su fecha aparecen al final de esta pantalla; si cambian de forma importante, te pediremos aceptarlos de nuevo.',
  },
];
