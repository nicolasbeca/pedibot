# Tarjetas — la imagen que sale al compartir un enlace de PediBot

> Creado el 30-sep-2026, a petición del operador: «anótalo todo para cuando haya que
> actualizarlas».

## Qué son

Cuando alguien pega un enlace de pedibot.xyz en WhatsApp, X, Bluesky, Telegram o Facebook, la
plataforma pide la imagen que la página anuncia en `og:image` y la pinta como tarjeta de
1200 × 630. Hasta el 30-sep había **una sola** para todas las páginas (`public/og.png`, el logo y
una frase). Desde entonces hay **una por tipo de página y lengua**: icono grande, el nombre de la
página en letras grandes y una línea con lo que hace.

La más importante es la de **Herramientas** (`/tools`, `/es/tools`…): el título a un lado y el
bot en el centro con las diez herramientas alrededor. Es la que el operador quiere enlazar en X,
porque enseña de golpe todo lo que hace PediBot.

## Dónde está cada cosa

| qué | dónde |
|---|---|
| el generador | `web/site/scripts/make-og-cards.mjs` |
| las tarjetas | `web/site/public/og/<lengua>/<tipo>.jpg` (se suben con el código) |
| qué tarjeta lleva cada página | `web/site/src/layouts/Base.astro`, bloque `ogImage` |
| los textos | `web/site/src/i18n.ts`, objeto `tools` de cada lengua (y los nombres de siempre: `nav_dose`, `nav_growth`…) |
| los iconos | `web/site/src/icons.ts` (los mismos de la página de herramientas) |
| la tarjeta general, para lo que no tiene tipo | `web/site/public/og.png`, hecha con `scripts/make_og.py` |
| la prueba | `tests/test_every_page_has_its_card.py` |

## Los 15 tipos

`home` (el chat), `tools`, `emergency` (¿voy a urgencias?), `warning-signs`, `numbers` (las
páginas `/emergency/<país>`), `dose` (también cada marca), `growth` (también cada país),
`vaccines` (también cada país), `muac`, `diary`, `family`, `kit`, `guides` (también cada guía),
`sources`, `about`. Legal, Apoyo, el memo y lo demás siguen con la general.

Base.astro elige por la dirección: la primera parte tras la lengua. Si esa tarjeta no existe,
pone la general, así que una página nueva nunca sale sin imagen.

## Cuándo hay que regenerarlas

- cambia el nombre o la frase de una herramienta en `i18n.ts`;
- cambia un icono en `icons.ts`, o la paleta;
- se añade una lengua (se hace sola: el generador recorre `LANGS`);
- se añade un tipo de página: añadirlo en `CARDS` del generador **y** en `OG_TIPOS` de
  Base.astro **y** en `TIPOS` de la prueba.

## Cómo se regeneran

En el PC (necesita Chrome o Edge instalado; en el servidor no se hace):

```bash
cd web/site
node scripts/make-og-cards.mjs      # unos 4 minutos: 120 tarjetas
npm run build
cd ../.. && uv run python -m pytest tests/test_every_page_has_its_card.py
```

Después, commit y despliegue como siempre. Los JPEG pesan unos 45-60 kB cada uno (5 MB las 120);
el móvil no los descarga nunca, sólo las plataformas que pintan la tarjeta.

## Cómo comprobar que una plataforma la ve

- **X**: pegar el enlace en un tuit sin publicar; la tarjeta sale en la vista previa.
- **Facebook / WhatsApp**: https://developers.facebook.com/tools/debug/ (también sirve para
  obligarles a refrescar una tarjeta vieja: «Scrape again»).
- **Cualquiera**: `curl -s https://pedibot.xyz/es/tools | grep og:image` y abrir la dirección.

Las plataformas guardan la imagen en su caché unos días: una tarjeta cambiada puede tardar en
verse en un enlace que ya se había compartido.

## Lo que se aprendió al hacerlas

- Se pintan con el navegador y no con PIL (como `og.png`): así salen las mismas fuentes que en
  la web, el árabe de derecha a izquierda sin hacer nada y el hindi con la letra del sistema.
- La hoja de fuentes de la web apunta a `/fonts/…`, que desde un fichero local no existe: la
  primera tanda salió con la letra del sistema. El generador la mete con la ruta completa.
- En PNG pesaban 300 kB cada una (32 MB). En JPEG de calidad 86, una quinta parte.
- El texto se escala con el largo del nombre (de 104 a 62 px) para que «Calculadora de dosis» y
  «Cinta del brazo (MUAC)» quepan sin cortarse.

## Pendiente, por si se quiere más

- Tarjeta propia por **país** (vacunas de Kenia, urgencias de Kenia): hoy llevan la del tipo.
- Tarjeta propia por **guía**, con su título: hoy llevan la de Guías. Son 525 y el servidor
  escribe guías nuevas cada día, así que habría que generarlas allí o aceptar que las nuevas
  lleven la del tipo hasta la siguiente tanda.
