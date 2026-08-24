# PRD — PediBot v2

> Documento canónico de plan. Si contradice a CLAUDE.md sobre el qué/por qué, gana este y se corrige CLAUDE.md en el mismo turno. Estado vivo en `STATE.md`. Ideas sin decidir en `IDEAS.md`.

Versión 0.1 — 2026-08-24. Redactado como plan completo del relanzamiento; se corrige sobre la marcha.

---

## 1. Tesis del producto

**Problema.** Un padre con un niño con fiebre a las 3 de la mañana tiene tres opciones malas: Google (ruido y miedo), ChatGPT (fluido pero sin fuente ni responsabilidad) o urgencias (colapsadas, muchas visitas innecesarias). Las sociedades científicas (AEP, SEUP, AEPap) tienen hojas excelentes "para padres", pero nadie las encuentra a esa hora.

**Solución.** Un asistente que responde en español llano, **solo** con lo que dicen esas guías, cita la hoja concreta y, si hay señales de alarma, lo primero que dice es "ve a urgencias". Gratis, sin registro, en web.

**Por qué ahora y por qué nosotros.**
- Los modelos baratos (DeepSeek V4 Flash a 0,14/0,28 $ por millón de tokens) hacen que una consulta cueste < 0,002 €. Un servicio gratuito es sostenible con donaciones + afiliación.
- Ya existen los activos: 50 fuentes seleccionadas a mano, marca, logo, cuenta de X con seguidores, correo, token con 3.900 holders.
- El diferencial frente a ChatGPT no es la inteligencia, es la **confianza verificable**: fuente, sección, página, organismo, año. Eso se construye con ingesta cuidada y disciplina de evaluación, no con un modelo mejor.

**Lo que aprendimos de la v1** (n8n + OpenAI + Wix): la herramienta no-code no daba control sobre el retrieval ni sobre las citas; el coste fijo (Wix Premium + OpenAI) no compensaba con uso bajo; no había forma de medir si el bot respondía bien. La v2 invierte exactamente ahí: código propio, coste variable ≈ 0 y evaluación medida.

## 2. Usuarios y casos de uso

**Usuario principal**: madre/padre/cuidador **de cualquier país** (decisión operador 2026-08-24: internacional desde el inicio; web en inglés primero, español después, otros idiomas más tarde) de un niño de 0-14 años, sin formación sanitaria, a menudo con el móvil en una mano y el niño en la otra. Preguntas típicas (de las hojas SEUP "Información para padres" y de la guía "las 50 principales consultas"):

1. "Tiene 38,5 y 2 años, ¿le doy algo? ¿cuánto?" → fiebre + calculadora de dosis.
2. "Se ha dado un golpe en la cabeza y ha vomitado" → traumatismo craneal → red flag → urgencias.
3. "Lleva 3 días con diarrea, ¿qué le doy de comer?" → gastroenteritis, rehidratación.
4. "Tos de perro por la noche" → laringitis.
5. "¿Cuándo empiezo con sólidos?" → alimentación complementaria AEP/OMS.
6. "¿Qué vacunas le tocan a los 4 meses?" → calendario 2025 del Ministerio.
7. "Ha tomado un trago de lejía" → intoxicación → red flag → 112 / Toxicología 91 562 04 20.
8. "Mi hijo de 13 años se hace cortes" → salud mental → protocolo fijo (024, SEUP).

**Usuario secundario**: pediatra/enfermera que quiere una hoja para dar a los padres → los artículos y las hojas fuente enlazadas.

**No usuarios**: nadie de fuera de la franja pediátrica; no se responde sobre adultos, embarazo (más allá de lo que digan las guías del recién nacido) ni veterinaria.

## 3. Principios de diseño

1. **Confianza > fluidez.** Mejor una respuesta corta con dos citas que una larga sin ellas.
2. **Fail-safe clínico.** Cualquier duda del sistema se resuelve hacia "consulta al pediatra / urgencias".
3. **Gratis y sin fricción.** Sin registro, sin app, sin wallet. El token es opcional y está en una página aparte.
4. **Medible.** Golden set, coste por respuesta, tasa de "no sé", feedback 👍/👎 por respuesta.
5. **Barato de mantener.** Un VPS, un SQLite, unos cron. Sin SaaS con cuota fija salvo el dominio.
6. **Web como carta de presentación.** La web tiene que parecer de una fundación médica seria, no de un side project cripto.

## 4. Bloque 1 — Ingesta de fuentes (`ingest/`)

Objetivo: convertir `FUENTES/*.pdf` en unidades citables, clasificadas y buscables, de forma reproducible.

### 4.1 Pipeline

```
PDF ──► extracción (pymupdf) ──► ¿texto vacío? ──► OCR (ocrmypdf spa) ──┐
                                                                          ▼
   limpieza (cabeceras/pies repetidos, guiones de corte, espacios) ──► detección de estructura
   (títulos por tamaño de fuente / mayúsculas / patrones "¿QUÉ ES…?") ──► troceado por sección
   (objetivo 300-600 tokens, solape 15 %, nunca partir una tabla de dosis) ──► clasificación
   (reglas + LLM: tema, subtemas, franja de edad, tipo de doc, organismo, año, nivel de evidencia)
   ──► export JSONL (`index/chunks/<doc_id>.jsonl`) ──► índice SQLite (FTS5 + sqlite-vec)
```

### 4.2 Esquema de chunk (pydantic)

| Campo | Ejemplo |
|---|---|
| `chunk_id` | `seup_fiebre_2023#signos_alarma#2` |
| `doc_id` | `seup_fiebre_2023` |
| `organismo` | `SEUP` (Sociedad Española de Urgencias de Pediatría) |
| `titulo_doc` | "Fiebre. Información para padres" |
| `anio` | 2023 (o `null` si no consta → duda al operador) |
| `seccion` | "¿Cuándo debo consultar en urgencias?" |
| `paginas` | `[2]` |
| `texto` | fragmento limpio |
| `tema` | `fiebre` (taxonomía cerrada en `config/taxonomia.yaml`, ~40 temas) |
| `subtemas` | `["signos_alarma", "antitermicos"]` |
| `edad` | `["lactante", "preescolar", "escolar"]` o `["todas"]` |
| `tipo` | `hoja_padres` / `guia_clinica` / `calendario` / `manual` / `libro` |
| `evidencia` | `sociedad_cientifica` / `organismo_publico` / `universidad` / `editorial` |
| `es_red_flag` | `true` si la sección es de signos de alarma |
| `es_tabla_dosis` | `true` si contiene posología (se indexa pero el LLM no la calcula) |
| `uso` | `publico` / `citar_solo` / `excluido` (heredado del catálogo) |
| `hash_fuente` | sha256 del PDF, para idempotencia |

### 4.3 Decisiones

- **OCR** con `ocrmypdf --language spa` para los 2 escaneados detectados (`14_Estreñimiento.pdf`, `las_50_principales_consultas.pdf`). No hay tesseract en el Windows local: el OCR se hace en el VPS o en WSL (decisión: VPS, es parte de `make ingest` allí).
- **Clasificación** en dos pasos: reglas (nombre de fichero + títulos) y después el LLM solo para lo que las reglas no resuelven. Salida revisable en `index/clasificacion_review.csv` para que el operador corrija a mano en un pase.
- **Fuentes largas** (Manual PUC, Pediatría Cuba 2016, Guía antibióticos Donostia, Guía dosificación AEPap, AAP en inglés) son de nivel clínico, no "para padres". Se indexan con `tipo=guia_clinica` y el motor las usa como respaldo, priorizando siempre hojas para padres cuando existen. Las de inglés se indexan en inglés (e5 es multilingüe) y la respuesta se da en español.
- **Fuentes excluidas** del índice público hasta aclarar licencia: `dermatologia_pedi.pdf` (Elsevier, texto casi vacío además). Ver catálogo.
- **Idempotencia**: si el hash del PDF no cambia, no se reprocesa. El índice se reconstruye entero desde los JSONL (< 1 min).

### 4.4 Criterio de salida del bloque

- 100 % de los PDFs `publico`/`citar_solo` con texto extraído (OCR incluido) y ≥ 1 chunk.
- Cero chunks sin `seccion` ni `paginas`.
- Clasificación revisada por el operador en el CSV (un pase).
- Búsqueda léxica de 20 consultas de prueba devuelve el documento esperado en top-3 en ≥ 90 %.

## 5. Bloque 2 — Motor de respuesta (`bot/`)

### 5.1 Pipeline por consulta

```
mensaje ──► 0. filtros (idioma, longitud, fuera de ámbito: adultos/mascotas → respuesta fija)
        ──► 1. TRIAJE reglas (config/red_flags.yaml: <3 meses+fiebre, convulsión, dificultad respiratoria,
               intoxicación, TCE+vómitos, ideación suicida…) → nivel {emergencia, urgente, normal}
        ──► 2. extracción de contexto (edad, peso, síntoma principal, duración) → si falta edad y es
               relevante, el bot PREGUNTA antes de responder
        ──► 3. recuperación híbrida: FTS5 (BM25, top 20) + vectores e5 (top 20) → RRF → top 6
               (bonus a hojas_padres y a chunks del mismo tema; si nivel≥urgente, bonus a es_red_flag)
        ──► 4. umbral: si el mejor score < τ → respuesta "no tengo fuente fiable" (sin LLM)
        ──► 5. redacción DeepSeek con prompt v_N: solo con los chunks, formato fijo, citas [n]
        ──► 6. verificación: cada [n] existe; ninguna cifra de dosis fuera de un chunk es_tabla_dosis;
               si falla → 1 reintento con temperatura 0 → si falla → fallback "consulta al pediatra"
        ──► 7. ensamblado: banner urgencias (si nivel≥urgente) + respuesta + fuentes + disclaimer
        ──► 8. log auditable (chunks, prompt_version, modelo, tokens, coste, latencia) + feedback id
```

### 5.2 Formato de respuesta (contrato con el widget)

```
[BANNER si aplica]  🚨 Con estos síntomas, acude a urgencias ahora o llama al 112.
                    Motivo: <señal de alarma detectada>  [fuente]

Respuesta en 3-6 frases llanas, cada afirmación con [1], [2]…
• Qué puedes hacer en casa (si la fuente lo dice)
• Cuándo consultar (siempre presente)

Fuentes:
[1] SEUP — "Fiebre. Información para padres" (2023), sección "Tratamiento", pág. 2. [enlace PDF]
[2] AEPap — Guía rápida de dosificación (3.ª ed.), tabla paracetamol, pág. 14.

ℹ️ PediBot informa a partir de guías oficiales; no sustituye a tu pediatra.
```

### 5.3 Herramientas deterministas (no LLM)

- **Calculadora de dosis** (paracetamol, ibuprofeno; después otros de venta libre): entrada peso/edad, salida mg y ml según concentración comercial, con tope máximo diario y edad mínima. Tablas transcritas de la Guía de dosificación AEPap, con test unitario por fila. Doble check de la transcripción por el operador.
- **Calendario vacunal** 2025 (Ministerio): edad → vacunas que tocan; dato tabulado.
- **Percentiles OMS** (peso/talla/PC 0-5 años): tablas LMS de la OMS (dominio público), cálculo de z-score.
- **Triaje**: lista de patrones en YAML, con test de recall sobre `eval/red_flags.jsonl`.

El LLM puede **invocar** estas herramientas (function calling) pero no reproducir su cálculo.

### 5.4 Memoria de conversación

Ventana corta (últimos 6 turnos) en el servidor, ligada a un `session_id` aleatorio de cookie, expira a 24 h. Se guarda anonimizada para evaluación. Sin cuentas de usuario en v2.0.

### 5.5 Evaluación (`eval/`)

- `golden.jsonl`: ≥ 50 preguntas → {respuesta esperada resumida, doc_id esperado, nivel esperado, debe_decir_no_se}. Fuente de las preguntas: hojas SEUP, "50 consultas", experiencia propia.
- `red_flags.jsonl`: ≥ 40 frases con señal de alarma + 40 sin ella.
- Métricas: `source_hit@3`, `red_flag_recall` (= 1.0 obligatorio), `red_flag_precision` (≥ 0,7), `dont_know_correct`, `citation_validity` (= 1.0 obligatorio), coste medio, latencia p95.
- Juez LLM opcional para "fidelidad a la fuente" (¿la respuesta dice algo que el chunk no dice?). Se usa como señal, no como gate.

### 5.6 Criterio de salida del bloque

`make eval` verde: red_flag_recall 1.0, citation_validity 1.0, source_hit@3 ≥ 0,85, dont_know_correct ≥ 0,9, coste medio < 0,002 €, p95 < 8 s. Revisión manual del operador de 30 respuestas al azar: 0 "peligrosas".

## 6. Bloque 3 — Web (`web/`)

### 6.1 Objetivos

Carta de presentación. Debe transmitir: seriedad médica, calidez, gratuidad, transparencia. Rápida (Lighthouse ≥ 95), accesible (WCAG AA), SEO técnico impecable.

### 6.2 Identidad visual

Del logo: **verde menta** `#7FD1C4` (burbuja), **verde bosque** `#3D8C6E` (texto "pedibot"), **crema** `#FFF8E7` (cara), blanco. Acentos: **coral suave** `#F28B82` para alertas (nunca rojo agresivo) y **ámbar** `#F4B942` para avisos. Fondo blanco/crema, mucho aire. Tipografía: Nunito (títulos), Atkinson Hyperlegible (texto), JetBrains Mono (cifras, dosis). Tema día (crema `#FFFBF2`) y tema noche (verde noche `#0F2A22`, "las 3 de la mañana"). Boceto v1 en `web/mockups/home.html` (24-ago). Ilustraciones planas estilo del logo de familia (`LOGOS/minimalist_family_logo_no_bg.png`). Tono: cercano, sin infantilizar.

### 6.3 Mapa del sitio

| Ruta | Contenido |
|---|---|
| `/` | Hero con el chat **directamente usable** (sin scroll), 3 ejemplos de preguntas, "Cómo funciona" (fuente → cita → urgencias), logos de organismos citados, CTA a herramientas |
| `/chat` | Chat a pantalla completa |
| `/herramientas/dosis` | Calculadora de dosis |
| `/herramientas/vacunas` | Calendario vacunal por edad |
| `/herramientas/percentiles` | Curvas de crecimiento |
| `/urgencias` | "¿Debo ir a urgencias?" — la hoja SEUP/AEP en formato checklist, teléfonos (112, 024, Toxicología) |
| `/guias/<tema>` | Artículos temáticos (generados + revisados), con fuentes al pie y enlace al chat precargado |
| `/fuentes` | Las 50 fuentes, organismo, año, enlace original. Transparencia total |
| `/metodo` | Cómo responde el bot, qué no hace, evaluación (publicar las métricas del golden set) |
| `/support` | Explicación honesta del token PDBT + libro de cuentas público (sin donaciones fiat por ahora) |
| `/privacidad`, `/aviso-legal` | RGPD, no consejo médico |

### 6.4 SEO

- Estático (Astro) → HTML completo indexable, sin JS para el contenido.
- JSON-LD `MedicalWebPage` + `FAQPage` en cada guía; `Organization` en home.
- Sitemap, RSS, canonical, OpenGraph con imagen por artículo (generada en build).
- Artículos: 600-900 palabras, un tema, una pregunta real en el título ("¿Cuándo bajar la fiebre a un niño?"), fuentes al pie con enlace al PDF oficial. Interlinking entre guías y herramientas.
- Google Search Console + Bing Webmaster desde el día 1 para medir si sirve (duda D-08).

### 6.5 Widget de chat

Vanilla TS, streaming SSE, estados: escribiendo / banner urgencias / fuentes plegables / 👍👎 / "copiar" / "compartir". Consentimiento inline en el primer mensaje. Funciona en móvil a una mano. Sin login.

### 2.1 Implicaciones de "internacional desde el inicio"

- Las fuentes son ~80 % españolas. No es un problema para la calidad (las hojas SEUP/AEP son excelentes y el LLM traduce), pero la **cita** dirá "SEUP (Spanish Society of Paediatric Emergency Medicine)" y el enlace irá al PDF en español. En `/sources` se explica con claridad.
- **Números de emergencia por país** (`config/emergency_numbers.yaml`, 18 países + default). El usuario elige país en el widget (o se infiere del navegador); si no se sabe, el banner dice "your local emergency number (112 in the EU, 911 in the Americas)".
- Calendario vacunal y dosis: las tablas son españolas (Ministerio 2025, AEPap). En inglés se presentan como "Spanish schedule — check your country's"; añadir calendarios de otros países está en `IDEAS.md` (F-04).
- Idioma de respuesta = idioma del mensaje (detección heurística es/en + instrucción al LLM). Web: Astro con i18n (`/en/`, `/es/`), inglés por defecto.
- SEO: artículos en inglés primero; la versión española del mismo artículo se genera después con las mismas fuentes.

## 7. Bloque 4 — Publicación automática (`publish/`)

- **Generador de artículos**: elige un tema de la taxonomía aún sin artículo (o con artículo > 6 meses), recupera los chunks del tema, redacta con DeepSeek bajo un prompt de artículo (estructura fija, fuentes al pie obligatorias, sin cifras de dosis fuera de tabla), pasa el **mismo verificador de citas** del bot, y deja el Markdown en `web/src/content/guias/` con `draft: true`.
- **Auto-publicación** (decisión operador 2026-08-24): el artículo se publica si pasa el verificador de citas y el juez de fidelidad; el operador recibe aviso por Telegram con el enlace y puede despublicar con un comando. Sin cola de revisión previa.
- **Cadencia**: 2 artículos/semana al principio (≈ 40 temas → 5 meses), después mantenimiento.
- **X (@pedibotai)**: **sin API** (no hay tier gratuito desde feb-2026; el operador descartó pagarla, D-06). El generador escribe el texto del post en `publish/queue/x/` y el operador lo pega a mano cuando quiera. Si X recupera un tier gratuito, se automatiza.
- **Instagram** (había token en la v1): en `IDEAS.md`, no en v2.0.

## 8. Bloque 5 — Operación (`ops/`)

- **VPS**: Hetzner CX22/CX23 nuevo, Ubuntu 24.04, usuario de servicio `pedibot`, ssh solo por clave (misma clave `multibot_hetzner_auto`), ufw 22/80/443.
- **Servicios systemd**: `pedibot-api` (uvicorn), `pedibot-publish.timer` (2×/semana), `pedibot-backup.timer` (diario, DB + JSONL a `backups/` + off-site a Storage Box/B2), `pedibot-watchdog.timer` (10 min: API responde, coste diario < tope, disco).
- **Caddy**: `pedibot.<dominio>` → estático `web/dist` + `/api/*` → 8601. TLS automático.
- **Alertas Telegram**: outbox SQLite con retry (patrón de MultiBot). Push solo si: API caída, coste diario > tope, error de verificación en > 5 % de respuestas, artículo pendiente de revisión, backup fallido.
- **Tope de gasto**: `MAX_DAILY_LLM_USD` (por defecto 2 $): al superarlo, el bot responde solo con retrieval sin LLM ("aquí tienes las fuentes") hasta el día siguiente.
- **Rate limit**: 20 mensajes / 10 min por IP; 200/día. Sin CAPTCHA en v2.0 (ver IDEAS).
- **Métricas** (panel mínimo `/admin` protegido por basic auth de Caddy): consultas/día, coste/día, tasa "no sé", tasa banner, 👍/👎, top temas, artículos publicados. SQLite + una página HTML.

## 9. Token PDBT — política

**Hechos** (24-ago-2026): PediBot (PDBT), Base, contrato `0x196A…15E1`, AgentTokenV2 de Virtuals (con tax en las transacciones), ya graduado a Uniswap (pool `0x94dfe42f…7784`), supply 998 M, **3.938 holders**, FDV ≈ 24,9 k$, volumen 24 h ≈ 77 $.

**Diagnóstico honesto.** 3.900 holders es un activo enorme para un proyecto de este tamaño: son 3.900 personas que en algún momento apostaron por PediBot. Lo que mata al token no es la falta de "utilidad" sino la falta de **noticias verificables**. Un token de un producto que no existe vale 25 k$; un token de un producto que publica métricas reales cada semana tiene, al menos, una historia.

**Política (decisión de partida, revisable)**:
1. **El token no compra acceso a nada.** Nunca. Línea roja en CLAUDE.md.
2. **El token es la "hucha transparente" del proyecto.** Página `/apoya` con: qué cuesta PediBot al mes (cifra real), cuánto se ha recibido en donaciones, cuánto hay en la reserva del token, y **qué se ha hecho con ello** (libro de cuentas público, actualizado cada mes).
3. **Compromiso de recompra medible** (a decidir, duda D-09): p. ej. "el 50 % de los ingresos de afiliación/donaciones se destina a recompras de PDBT que se queman o se bloquean", publicado on-chain con hash de cada operación. Es la única "utilidad" honesta para un token de financiación: convertir tracción del producto en demanda del token, sin exigir nada al usuario.
4. **Reconocimiento no económico a holders**: muro de agradecimiento opcional (quien quiera firma su wallet y aparece como "familia que apoya"), acceso anticipado a features **también disponibles gratis después**. Nada de descuentos ni gating.
5. **Comunicación**: cada hito del producto (fuente nueva, artículo, métrica del golden set, coste del mes) se publica en X con el mismo tono para todos, holders o no. Sin "shilling", sin promesas de precio. Registrar el proyecto en el ecosistema Virtuals (perfil actualizado, enlace a la web, ACP si aplica) para que quien mire el token vea un producto vivo.
6. **Qué NO haremos**: pagar listados, "trending", market makers, airdrops a cambio de engagement.

## 10. Fases y criterios de salida

| Fase | Contenido | Sale cuando |
|---|---|---|
| **F0 Cimientos** (esta semana) | Repo, docs, `.env`, rotación de claves, catálogo de fuentes, scaffold `uv`, CI local (`make test/lint`) | Repo con commit inicial, claves rotadas, catálogo revisado por el operador |
| **F1 Ingesta** | Bloque 1 completo, OCR de los 2 escaneados, clasificación revisada, índice construido | Criterios §4.4 |
| **F2 Motor** | Bloque 2: CLI `pedibot ask "..."`, triaje, retrieval, prompt v1, verificador, calculadoras, golden set, `make eval` | Criterios §5.6 |
| **F3 Web + API** | FastAPI + widget + sitio Astro completo (sin artículos aún), páginas de herramientas, `/fuentes`, `/apoya`, legal | Lighthouse ≥ 95, funciona en móvil, revisión visual del operador |
| **F4 Despliegue** | VPS, Caddy, units, backups, watchdog, Telegram, dominio, tope de gasto | 7 días estable con tráfico propio, 0 alertas falsas, coste medido |
| **F5 Beta cerrada** | 10-20 padres conocidos usan el bot 2 semanas; se revisan TODAS las conversaciones; se corrigen prompt/retrieval | 0 respuestas peligrosas en la revisión, ≥ 70 % 👍, golden set sin regresión |
| **F6 Lanzamiento público** | Anuncio en X, reactivación de @pedibotai, Search Console, primeros 4 artículos, página del token con el libro de cuentas | Publicado; métricas reales de la semana 1 en STATE.md |
| **F7 Publicación automática** | Bloque 4 con cola de revisión, 2 artículos/semana, hilos en X | 8 semanas de cadencia cumplida |
| **F8 Crecimiento y nuevas funciones** | Lo que decida `IDEAS.md`: comparador de fármacos OTC, diario de síntomas, LatAm, WhatsApp… | Por feature, con su propio gate |

Estimación de esfuerzo (sesiones de trabajo con Claude Code, orientativo): F0 1 · F1 3-4 · F2 5-6 · F3 5-6 · F4 2 · F5 2 (+2 semanas de calendario) · F6 1 · F7 3.

## 11. Presupuesto

| Partida | €/mes |
|---|---|
| VPS Hetzner CX22/CX23 | 4-6 |
| DeepSeek (1.000 consultas/día × 3 k tokens) | 1-3 |
| Dominio | ~1 |
| Backup off-site | 0-3 |
| **Total** | **≈ 5-13** |

Ingresos previstos (no medidos): reserva del token PDBT (vía principal, decisión operador 2026-08-24 — sin donaciones por ahora, D-11), afiliación Amazon más adelante. Objetivo mínimo: cubrir el coste.

## 12. Riesgos

| Riesgo | Mitigación |
|---|---|
| Respuesta clínicamente peligrosa | Triaje por reglas, fuente o silencio, verificador de citas, golden set, beta cerrada con revisión total, disclaimer |
| Responsabilidad legal | Aviso legal genérico claro, no diagnóstico, no datos personales. Sin asesoría legal por ahora (decisión operador, D-10) |
| Fuentes desactualizadas | Campo `anio` visible en cada cita; revisión anual del catálogo; alerta si una fuente > 5 años se cita mucho |
| Copyright de fuentes | Campo `uso`; solo hojas de organismos públicos/sociedades en el índice público; enlaces al PDF original, nunca rehosting de obras editoriales |
| Coste descontrolado | Tope diario, rate limit, modo degradado sin LLM |
| Dependencia de DeepSeek | Interfaz `LLMProvider`, `anthropic`/`openai` como respaldo con un cambio de `.env` |
| Token percibido como estafa | Transparencia radical (§9), nunca gating, nunca promesas |
| Abandono por falta de tiempo | Automatizar publicación y operación; watchdog; todo documentado para retomar en frío |
