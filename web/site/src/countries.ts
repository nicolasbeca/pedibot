/**
 * Los países, con su bandera y su nombre (19-sep-2026).
 *
 * El operador, entrando en la web: «en el calendario de vacunas has puesto un listado de todos
 * los países que es infumable. Igual para las curvas. Quizás un desplegable con los nombres y
 * las banderas». Y en el chat era peor: el selector mostraba **el código ISO pelado** —AE, AO,
 * AR…—, así que para elegir España había que saber que España es ES y bajar sesenta líneas de
 * siglas. Un desplegable que hay que descifrar no lo usa nadie.
 *
 * Aquí viven las tres cosas que hacían falta y estaban repetidas o ausentes en cinco sitios: la
 * bandera, el nombre en el idioma de la página y el orden alfabético de ESE idioma (que no es
 * el del código: en castellano Alemania va antes que Angola, y en el código DE va después de AO).
 *
 * Sobre la bandera, y hay que decirlo porque se ve distinto según dónde se mire: los emojis de
 * bandera son dos letras invisibles del bloque «regional indicator». En Android, iPhone y Mac se
 * pintan como banderas. **En Windows no**: Microsoft nunca metió las banderas en su fuente de
 * emojis, así que en un Chrome de escritorio Windows se ven las dos letras del país. No es un
 * fallo del sitio, y no es grave, porque al lado va siempre el nombre escrito; y el público que
 * este proyecto persigue —India, países árabes, África— entra desde el móvil, donde sí se ven.
 */

/** La bandera como emoji, o cadena vacía si el código no es de país. */
export function flag(cc: string): string {
  if (!/^[A-Za-z]{2}$/.test(cc)) return '';
  const base = 0x1f1e6;
  return String.fromCodePoint(
    ...[...cc.toUpperCase()].map((c) => base + c.charCodeAt(0) - 65)
  );
}

/**
 * El nombre del país en el idioma de la página.
 *
 * `Intl.DisplayNames` también existe en Node, así que esto se resuelve al CONSTRUIR y el nombre
 * viaja escrito en el HTML: un país que sólo existe después de ejecutar un script no lo indexa
 * nadie, y «vacunas en Kenia» es justo lo que este sitio puede contestar.
 */
export function countryName(cc: string, lang: string): string {
  try {
    return new Intl.DisplayNames([lang], { type: 'region' }).of(cc.toUpperCase()) || cc;
  } catch {
    return cc; // sin ICU completo se queda el código, que se entiende
  }
}

export interface CountryOption {
  cc: string;
  name: string;
  flag: string;
  /** Lo que se ve: bandera y nombre, ya juntos. */
  label: string;
}

/** Los países que se le den, ordenados por su nombre en ese idioma, con bandera. */
export function countryOptions(codes: readonly string[], lang: string): CountryOption[] {
  const opciones = codes.map((cc) => {
    const name = countryName(cc, lang);
    const bandera = flag(cc);
    return { cc, name, flag: bandera, label: bandera ? `${bandera} ${name}` : name };
  });
  try {
    // El orden alfabético depende de la lengua: en alemán Ö va con O, en castellano la Ñ va
    // después de la N. `localeCompare` lo sabe; `sort()` a secas, no.
    const collator = new Intl.Collator(lang);
    opciones.sort((a, b) => collator.compare(a.name, b.name));
  } catch {
    opciones.sort((a, b) => (a.name < b.name ? -1 : 1));
  }
  return opciones;
}
