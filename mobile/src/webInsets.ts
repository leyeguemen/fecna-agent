// Zona segura inferior (px) en la versión web: se mide una vez con env(safe-area-inset-bottom).
// La barra de pestañas necesita números (no calc()) para repartir bien el alto entre iconos y etiquetas.
let cached: number | null = null;

export function webSafeBottom(): number {
  if (cached !== null) return cached;
  try {
    const probe = document.createElement('div');
    probe.style.cssText = 'position:fixed;visibility:hidden;padding-bottom:env(safe-area-inset-bottom)';
    document.body.appendChild(probe);
    cached = parseFloat(getComputedStyle(probe).paddingBottom) || 0;
    document.body.removeChild(probe);
  } catch {
    cached = 0;
  }
  return cached;
}
