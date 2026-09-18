"""Una página de números de emergencia por país, en los ocho idiomas (17-sep-2026).

El operador, ayer: «cuando la gente busque número de emergencia de un país, a lo mejor el SEO hace
que si aparece directamente en la página, nos pueda vincular con esa página directamente». Tiene
razón y es barato: el dato ya está, sólo había que escribirlo en un sitio que se pueda enlazar.

35 países × 8 idiomas = 280 páginas. Ninguna es una página vacía con un número: llevan el número,
el de toxicología, el de salud mental, la lista de signos de alarma —la misma de los pediatras de
urgencias que ya usa el sitio— y el enlace al calendario vacunal y a las tablas de crecimiento de
ESE país cuando los tenemos.
"""

from pathlib import Path

PAGES = Path(__file__).resolve().parents[1] / "web" / "site" / "src" / "pages"
IDIOMAS = ("en", "es", "fr", "de", "ru", "ar", "pt", "hi")

PLANTILLA = '''---
/**
 * Los números de emergencia de un país, uno por página (17-sep-2026; África, 18-sep-2026).
 *
 * Idea del operador: quien busca «número de emergencias en Catar» merece una página que conteste
 * eso, y no una portada con un desplegable. El dato ya estaba en el sitio desde el 11-sep; lo que
 * no había era una dirección que enlazar.
 *
 * Desde el 18-sep-2026 hay un caso que en Europa no se daba: países donde la fuente dice que NO
 * existe un número nacional (RD del Congo, Gambia, Liberia, Sudán del Sur, Congo, Comoras,
 * Guinea) y uno donde no hemos podido verificarlo (Zambia). Esas páginas se publican igual: en
 * lugar del número grande ponen la frase, y debajo, entrecomillada y en su idioma original, la
 * letra pequeña de la fuente. Callar el país sería fingir que no existe; ponerle un 112 que nadie
 * contesta sería mandar a un padre a esperar a una ambulancia que no va a venir.
 *
 * La página no es un número suelto: lleva también toxicología, salud mental, los signos de alarma
 * tal como los publican los pediatras de urgencias, y el calendario vacunal y las tablas de
 * crecimiento de ese mismo país cuando los tenemos. Todo escrito en el HTML.
 *
 * ESTE FICHERO SE GENERA. Se escribe en los ocho idiomas desde
 * scripts/build_emergency_pages.py; editar una copia a mano la deja desparejada de las otras.
 */
import Base from '{subir}layouts/Base.astro';
import Checklist from '{subir}components/Checklist.astro';
import emergency from '{subir}data/emergency.json';
import vaccines from '{subir}data/vaccines.json';
import charts from '{subir}data/growth_charts.json';
import {{ t, langPrefix }} from '{subir}i18n';

const lang = '{lang}'; const s = t(lang); const pref = langPrefix(lang);

export async function getStaticPaths() {{
  return Object.entries(emergency as any).map(([code, data]) => ({{
    params: {{ country: code.toLowerCase() }},
    props: {{ code, data }},
  }}));
}}

const {{ code, data }} = Astro.props as any;
let name = code;
try {{ name = new Intl.DisplayNames([lang], {{ type: 'region' }}).of(code) || code; }} catch (e) {{}}

const h1 = s.emgc_h1.replace('{{name}}', name);
const desc = s.emgc_desc.replace('{{name}}', name);
const lede = s.emgc_lede.replace('{{name}}', name);
// «15 / 112»: al marcar se llama al primero
const tel = String(data.emergency || '').split('/')[0].trim();
const tieneCalendario = Object.keys(vaccines as any).includes(code);
const tieneTablas = Object.keys(charts as any).includes(code);

let nombreDe = (cc: string) => cc;
try {{
  const dn = new Intl.DisplayNames([lang], {{ type: 'region' }});
  nombreDe = (cc: string) => dn.of(cc) || cc;
}} catch (e) {{}}
const otros = Object.keys(emergency as any)
  .filter((cc) => cc !== code)
  .map((cc) => [cc, nombreDe(cc)] as [string, string])
  .sort((a, b) => a[1].localeCompare(b[1], lang));

const jsonld = {{
  '@context': 'https://schema.org',
  '@type': 'MedicalWebPage',
  name: h1,
  description: desc,
  about: {{ '@type': 'MedicalCondition', name: s.emg_about }},
  audience: {{ '@type': 'Patient' }},
}};
---
<Base lang={{lang}} title={{`${{h1}} — PediBot`}} description={{desc}} path={{`${{pref}}/emergency/${{code.toLowerCase()}}`}} jsonld={{jsonld}}>
  <div class="wrap" style="padding:40px 18px">
    <p class="eyebrow">{{s.emg_eyebrow}}</p>
    <h1 style="margin-top:8px">{{h1}}</h1>
    {{data.emergency && <p class="lede">{{lede}}</p>}}

    {{data.emergency ? (
      <div class="big">
        <span class="lbl">{{s.mine_call}}</span>
        <a class="tel" href={{`tel:${{tel}}`}}>{{data.emergency}}</a>
      </div>
    ) : (
      <p class="nohay">{{data.no_national ? s.emgc_none : s.emgc_unsure}}</p>
    )}}
    {{data.note && (
      <p class="letra"><b>{{s.emgc_note}}</b> <q lang="en" dir="ltr">{{data.note}}</q></p>
    )}}
    <ul class="otras">
      {{data.poison && <li><b>{{s.mine_poison}}:</b> {{data.poison}}</li>}}
      {{data.mental && <li><b>{{s.mine_mental}}:</b> {{data.mental}}</li>}}
    </ul>

    <p class="sitio">
      <button class="btn btn-ghost" id="near" type="button">📍 {{s.emg_near}}</button>
      <span id="near-hint" class="n"></span>
      {{tieneCalendario && <a class="btn btn-ghost" href={{`${{pref}}/vaccines/${{code.toLowerCase()}}`}}>{{s.nav_vaccines}} →</a>}}
      {{tieneTablas && <a class="btn btn-ghost" href={{`${{pref}}/growth/${{code.toLowerCase()}}`}}>{{s.nav_growth}} →</a>}}
    </p>

    <Checklist lang={{lang}} />

    <h2 style="margin-top:34px">{{s.emgc_others}}</h2>
    <p class="lista">
      {{otros.map(([cc, nombre]) => (
        <a href={{`${{pref}}/emergency/${{cc.toLowerCase()}}`}}>{{nombre}}</a>
      ))}}
    </p>
  </div>
  <script is:inline define:vars={{{{ query: s.emg_map_q }}}}>
    document.getElementById('near')?.addEventListener('click', () => {{
      const hint = document.getElementById('near-hint');
      const open = (extra) => window.open('https://www.openstreetmap.org/search?query=' + encodeURIComponent(query) + (extra || ''), '_blank');
      if (!navigator.geolocation) {{ open(); return; }}
      hint.textContent = '…';
      navigator.geolocation.getCurrentPosition((pos) => {{
        const la = pos.coords.latitude, lo = pos.coords.longitude;
        open(`&lat=${{la}}&lon=${{lo}}#map=14/${{la}}/${{lo}}`); hint.textContent = '';
      }}, () => {{ open(); hint.textContent = ''; }});
    }});
  </script>
</Base>

<style>
  .big {{ margin-top: 22px; }}
  .big .lbl {{ display: block; font-size: .86rem; color: var(--ink-3); }}
  .big .tel {{
    font-family: 'JetBrains Mono', ui-monospace, monospace;
    font-size: clamp(2.6rem, 12vw, 4.4rem); line-height: 1.05; color: var(--coral);
    font-variant-numeric: tabular-nums; text-decoration: none;
  }}
  .nohay {{
    margin: 22px 0 0; font-size: clamp(1.5rem, 5vw, 2.1rem); line-height: 1.15;
    font-weight: 700; color: var(--ink-1); max-width: 22ch;
  }}
  .letra {{ margin: 12px 0 0; max-width: 62ch; font-size: .94rem; color: var(--ink-2); }}
  .letra b {{ color: var(--ink-3); font-weight: 600; display: block; font-size: .84rem; }}
  .letra q {{ font-style: italic; }}
  .otras {{ list-style: none; padding: 0; margin: 10px 0 0; display: grid; gap: 4px; }}
  .otras b {{ color: var(--ink-3); font-weight: 600; }}
  .sitio {{ margin-top: 22px; display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }}
  .lista {{ display: flex; flex-wrap: wrap; gap: 10px 16px; font-size: .92rem; }}
</style>
'''


INDICE = """---
/**
 * La portada de los números de emergencia (17-sep-2026).
 *
 * Tenía la lista de signos de alarma y ni un solo teléfono, teniendo el sitio los de 35 países.
 * Ahora los lleva todos, escritos, y cada uno enlaza a su página.
 *
 * ESTE FICHERO SE GENERA desde scripts/build_emergency_pages.py, junto con las páginas de cada
 * país. Editar una copia a mano la deja desparejada de las otras siete.
 */
import Base from '{subir}layouts/Base.astro';
import Checklist from '{subir}components/Checklist.astro';
import emergency from '{subir}data/emergency.json';
import langCountries from '{subir}data/lang_countries.json';
import {{ t, langPrefix }} from '{subir}i18n';

const lang = '{lang}'; const s = t(lang); const pref = langPrefix(lang);
const numeros = emergency as Record<string, any>;

let nombreDe = (cc: string) => cc;
try {{
  const dn = new Intl.DisplayNames([lang], {{ type: 'region' }});
  nombreDe = (cc: string) => dn.of(cc) || cc;
}} catch (e) {{}}

// primero los países donde se habla el idioma de la página: quien lee en árabe busca el suyo,
// no el británico. El resto va detrás, por nombre.
const mios: string[] = (langCountries as Record<string, string[]>)[lang] ?? [];
const resto = Object.keys(numeros)
  .filter((cc) => !mios.includes(cc))
  .map((cc) => [cc, nombreDe(cc)] as [string, string])
  .sort((a, b) => a[1].localeCompare(b[1], lang));
const orden: [string, string][] = [...mios.map((cc) => [cc, nombreDe(cc)] as [string, string]), ...resto];

const jsonld = {{ '@context': 'https://schema.org', '@type': 'MedicalWebPage', name: s.emg_name, about: s.emg_about }};
---
<Base lang={{lang}} title={{s.emg_title}} description={{s.emg_desc}} path={{`${{pref}}/emergency`}} jsonld={{jsonld}}>
  <div class="wrap" style="padding:40px 18px">
    <p class="eyebrow">{{s.emg_eyebrow}}</p>
    <h1 style="margin-top:8px">{{s.emg_h1}}</h1>
    <p class="lede">{{s.emg_lede}}</p>
    <p style="margin-top:14px"><button class="btn btn-ghost" id="near" type="button">📍 {{s.emg_near}}</button> <span id="near-hint" class="n"></span></p>

    <h2 style="margin-top:34px">{{s.emg_by_country}}</h2>
    <div class="nums">
      {{orden.map(([cc, nombre]) => (
        <a class="ncard" href={{`${{pref}}/emergency/${{cc.toLowerCase()}}`}}
           title={{numeros[cc]?.emergency ? nombre : (numeros[cc]?.no_national ? s.emgc_none : s.emgc_unsure)}}>
          <span class="pais">{{nombre}}</span>
          <b class={{numeros[cc]?.emergency ? '' : 'sin'}}>{{numeros[cc]?.emergency ?? '—'}}</b>
        </a>
      ))}}
    </div>

    <Checklist lang={{lang}} />
  </div>
  <script is:inline define:vars={{{{ query: s.emg_map_q }}}}>
    document.getElementById('near')?.addEventListener('click', () => {{
      const hint = document.getElementById('near-hint');
      const open = (extra) => window.open('https://www.openstreetmap.org/search?query=' + encodeURIComponent(query) + (extra || ''), '_blank');
      if (!navigator.geolocation) {{ open(); return; }}
      hint.textContent = '…';
      navigator.geolocation.getCurrentPosition((pos) => {{
        const la = pos.coords.latitude, lo = pos.coords.longitude;
        open(`&lat=${{la}}&lon=${{lo}}#map=14/${{la}}/${{lo}}`); hint.textContent = '';
      }}, () => {{ open(); hint.textContent = ''; }});
    }});
  </script>
</Base>

<style>
  .nums {{
    display: grid; gap: 10px; margin: 16px 0 6px;
    grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  }}
  .ncard {{
    display: flex; justify-content: space-between; align-items: baseline; gap: 10px;
    border: 1px solid var(--line); border-radius: 12px; padding: 10px 14px;
    text-decoration: none; color: inherit; background: var(--paper);
  }}
  .ncard:hover {{ border-color: var(--coral); }}
  .ncard .pais {{ font-size: .92rem; }}
  .ncard b {{
  .ncard b.sin {{ color: var(--ink-3); font-weight: 600; }}
    font-family: 'JetBrains Mono', ui-monospace, monospace; color: var(--coral);
    font-variant-numeric: tabular-nums; font-size: .98rem; white-space: nowrap;
  }}
</style>
"""


def main() -> None:
    hechas = []
    for lang in IDIOMAS:
        carpeta = PAGES / "emergency" if lang == "en" else PAGES / lang / "emergency"
        carpeta.mkdir(parents=True, exist_ok=True)
        subir = "../../" if lang == "en" else "../../../"
        destino = carpeta / "[country].astro"
        destino.write_text(PLANTILLA.format(subir=subir, lang=lang), encoding="utf-8")
        hechas.append(str(destino.relative_to(PAGES)))
        indice = carpeta.parent / "emergency.astro"
        arriba = "../" if lang == "en" else "../../"
        indice.write_text(INDICE.format(subir=arriba, lang=lang), encoding="utf-8")
        hechas.append(str(indice.relative_to(PAGES)))
    print("\n".join(hechas))


if __name__ == "__main__":
    main()
