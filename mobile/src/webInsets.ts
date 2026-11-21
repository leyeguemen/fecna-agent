// Zona segura inferior (px) en la versión web: se mide una vez con env(safe-area-inset-bottom).
// La barra de pestañas necesita números (no calc()) para repartir bien el alto entre iconos y etiquetas.
// Tope: en algunos iPhone env() reporta una zona segura inferior exagerada y deja un hueco
// enorme bajo las etiquetas; el indicador de inicio solo necesita unos pocos píxeles.
const MAX_BOTTOM = 20;
let cached: number | null = null;

export function webSafeBottom(): number {
  if (cached !== null) return cached;
  try {
    const probe = document.createElement('div');
    probe.style.cssText = 'position:fixed;visibility:hidden;padding-bottom:env(safe-area-inset-bottom)';
    document.body.appendChild(probe);
    cached = Math.min(parseFloat(getComputedStyle(probe).paddingBottom) || 0, MAX_BOTTOM);
    document.body.removeChild(probe);
  } catch {
    cached = 0;
  }
  return cached;
}
