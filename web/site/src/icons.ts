// Los iconos de las herramientas (30-sep-2026). Trazos de 24 × 24, sin relleno: el color lo pone
// quien los usa. Viven aquí y no en cada componente porque los comparten la página /tools, el
// panel del menú y las tarjetas que se ven al compartir un enlace (scripts/make-og-cards.mjs),
// y un icono que cambia en un sitio y no en otro es una herramienta que parece dos.
export const ICON: Record<string, string> = {
  chat: '<path d="M4 5h16v11H9l-5 4z"/><path d="M8 9.5h8M8 12.5h5"/>',
  er: '<path d="M12 3 2.5 20h19z"/><path d="M12 9v5M12 17h.01"/>',
  signs: '<circle cx="12" cy="12" r="9"/><path d="M12 7v6M12 16.5h.01"/>',
  phone: '<path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a1 1 0 0 1-1 1A16 16 0 0 1 4 5a1 1 0 0 1 1-1z"/>',
  dose: '<path d="M9 3h6v4H9zM8 7h8v13a1 1 0 0 1-1 1H9a1 1 0 0 1-1-1z"/><path d="M8 12h8M10.5 15h3"/>',
  growth: '<path d="M4 20V4M4 20h16"/><path d="M7 16c3-1 5-4 6-7s3-4 6-4"/>',
  vax: '<path d="m15 3 6 6M18 6l-9.5 9.5M13 5l6 6M7 14l3 3-4.5 4.5-3-3zM11 9l4 4"/>',
  muac: '<rect x="3" y="8" width="18" height="8" rx="2"/><path d="M7 8v3M11 8v4M15 8v3M19 8v2"/>',
  diary: '<path d="M6 3h11a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H6z"/><path d="M6 3v18M9 8h6M9 12h6M9 16h4"/>',
  kids: '<circle cx="9" cy="8" r="3"/><circle cx="17" cy="10" r="2.3"/><path d="M3.5 20c.5-3.5 2.8-5.5 5.5-5.5s5 2 5.5 5.5M14.5 20c.3-2.3 1.5-3.8 3-3.8s2.7 1.5 3 3.8"/>',
  home: '<path d="M3 11 12 4l9 7"/><path d="M5 10v10h14V10"/><path d="M10 15h4M12 13v4"/>',
  guides: '<path d="M4 5.5C6.5 4 9.5 4 12 5.5v14C9.5 18 6.5 18 4 19.5z"/><path d="M20 5.5C17.5 4 14.5 4 12 5.5v14c2.5-1.5 5.5-1.5 8 0z"/>',
  sources: '<path d="M6 4h9l3 3v13H6z"/><path d="M15 4v3h3M9 11h6M9 14h6M9 17h4"/>',
  about: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5h.01"/>',
};

export const iconSvg = (k: string, size = 24, stroke = 1.8): string =>
  `<svg viewBox="0 0 24 24" width="${size}" height="${size}" fill="none" stroke="currentColor" stroke-width="${stroke}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON[k] ?? ''}</svg>`;
