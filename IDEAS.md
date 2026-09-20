# IDEAS.md — cuaderno de ideas y mejoras sin decidir

> Aquí se anota todo lo que surja. Nada de esta lista se implementa sin decidirlo juntos. Cada idea: qué es, por qué podría valer, qué costaría, y estado (`nueva` / `aceptada → fase` / `descartada: motivo`).

## Producto — funciones que no son "ChatGPT"

| Id | Idea | Por qué | Coste | Estado |
|---|---|---|---|---|
| I-01 | **Comparador de medicamentos de venta libre** (paracetamol vs ibuprofeno; jarabes para la tos que NO recomienda la AEP; sueros de rehidratación) con tabla de edad mínima, dosis, intervalo, cuándo no dar | Pregunta real y frecuente; determinista; muy compartible | Medio (tablas + página) | nueva (mencionada por el operador) |
| I-02 | **"¿Debo ir a urgencias?" interactivo**: checklist guiada por edad y síntoma a partir de la hoja SEUP/AEP, sin LLM | Es el caso de uso nº 1 y se puede hacer 100 % determinista | Bajo | HECHA 25-ago (config/er_checklist.yaml + /emergency) |
| I-03 | **Diario de síntomas** local (en el navegador, sin cuenta): temperatura, dosis dadas y hora → evita doble dosis y da al pediatra un registro | Utilidad diaria real; sin datos en servidor (localStorage) | Medio | HECHA 25-ago (/diary: localStorage + Notification API) |
| I-04 | **Recordatorio de próxima dosis** (notificación del navegador) | Complementa I-03 | Bajo | HECHA 25-ago (/diary: localStorage + Notification API) |
| I-05 | **Calculadora de percentiles con curva dibujada** (OMS 0-5, y OMS 5-19) | Los padres lo buscan mucho; SEO | Medio | nueva |
| I-06 | **"Explícaselo a mi hijo"**: versión de la respuesta para leer a un niño de 5-10 años | Diferenciador cálido; barato (un prompt) | Bajo | HECHA 25-ago (mode=child, botón 🧸) |
| I-07 | **Modo pediatra**: respuesta con el nivel de la guía clínica (Manual PUC, antibióticos Donostia) para profesionales, con toggle | Segundo usuario; las fuentes ya están | Bajo-medio | DESCARTADA por el operador 25-ago (responsabilidad) |
| I-08 | **Voz** (dictar la pregunta, escuchar la respuesta) — Web Speech API gratis | Padre con el niño en brazos | Bajo | HECHA 25-ago (Web Speech: dictar 🎤 y escuchar 🔊) |
| I-09 | **WhatsApp** (Cloud API, gratis hasta cierto volumen) | Canal natural de padres | Medio-alto; verificación Meta | nueva |
| I-10 | **Fotos**: "¿qué es este sarpullido?" con modelo de visión | Muy demandado, muy arriesgado clínicamente | Bajo en coste (vision-exp ≈ 0,0002 $/foto), alto en riesgo | descartada como diagnóstico; ver I-10b |
| I-10b | **Foto solo para signos de alarma**: la imagen se compara con la lista SEUP (petequias, cianosis, hinchazón de labios) y el bot responde "urgencias" o "no veo signos de alarma, pero no puedo decirte qué es" — nunca un nombre de enfermedad | Cubre lo que los padres quieren sin diagnosticar | Medio | nueva (propuesta 25-ago tras pregunta del operador) |
| I-11 | **Mapa de urgencias pediátricas cercanas** (OpenStreetMap) | Cierra el "ve a urgencias" con "¿dónde?" | Medio | HECHA 25-ago (botón «urgencias cerca de mí» → OpenStreetMap con geolocalización) |
| I-12 | **Chat precargado desde cada artículo** ("pregunta sobre esto") | Convierte SEO en uso | Bajo | aceptada → F3 |
| I-13 | **Historial multi-hijo con edades** (local) para no repetir la edad cada vez | Fricción menor | Bajo | nueva |
| I-14 | **Alertas estacionales** en la home (bronquiolitis en invierno, golpe de calor en verano, gastroenteritis) | Contenido fresco sin esfuerzo | Bajo | nueva |
| I-15 | **Traducción a inglés / portugués** con las mismas fuentes | LatAm / Brasil; e5 es multilingüe | Medio | nueva; después de España |

## Fuentes

| Id | Idea | Estado |
|---|---|---|
| F-01 | Añadir las hojas "En Familia" de la AEP (enfamilia.aeped.es) — muchas, en español, actualizadas | nueva; comprobar licencia |
| F-02 | Hojas de la AEPap "Familia y salud" | nueva |
| F-03 | Fichas de Toxicología (Instituto Nacional de Toxicología, 91 562 04 20) | nueva |
| F-04 | Calendario vacunal por comunidad autónoma (difieren) | nueva |
| F-05 | Reemplazar/actualizar la guía cubana 2016 y el Manual PUC por guías españolas equivalentes | nueva |
| F-06 | Versión estructurada (tabla) de la guía de dosificación AEPap para las calculadoras | aceptada → F2 |

## Web / SEO / difusión

| Id | Idea | Estado |
|---|---|---|
| W-01 | Página "Fuentes" con logos de organismos citados (con permiso de uso de marca) | aceptada → F3 |
| W-02 | Publicar las métricas del golden set en `/metodo` (transparencia como marketing) | aceptada → F3 |
| W-03 | Widget embebible para blogs de crianza / webs de pediatras (`<script>`) | nueva |
| W-04 | Instagram automático (había token en la v1) — carruseles a partir de artículos | nueva; después de X |
| W-05 | Newsletter mensual (Buttondown gratis) con las guías del mes | nueva |
| W-06 | Colaboración con pediatras para "revisado por" en los artículos | aceptada 25-ago → F6 (buscar colaboradores) |
| W-07 | Búsqueda del sitio con el mismo índice del bot | nueva |
| W-08 | CAPTCHA/Turnstile si aparece abuso del rate limit | nueva |

## Token PDBT

| Id | Idea | Estado |
|---|---|---|
| T-01 | Página `/apoya` con libro de cuentas público y recompras verificables on-chain | HECHA 25-ago (/support con libro de cuentas; recompras pendientes de decisión D-09) |
| T-02 | Actualizar el perfil del agente en Virtuals con la web nueva y enlaces | nueva |
| T-03 | Muro de "familias que apoyan" (firma opcional de wallet) | nueva |
| T-04 | Acceso anticipado a features para holders — SIEMPRE gratis para todos después | nueva |
| T-05 | Informe mensual "estado de PediBot" en X: consultas, coste, fuentes nuevas, recompras | aceptada → F6 |
| T-06 | Explorar si Virtuals ACP (agent commerce) permite que PediBot sea un "agente" invocable por otros agentes con pago en PDBT — utilidad sin gating al usuario humano | aceptada 25-ago → investigar en F6 |
| T-07 | Recompra + quema vs recompra + bloqueo (bóveda) | pendiente de decidir |

## Operación

| Id | Idea | Estado |
|---|---|---|
| O-01 | Caché de respuestas por pregunta normalizada (misma pregunta → misma respuesta, coste 0) | nueva; ojo con contexto de edad |
| O-02 | Juez LLM nocturno sobre las conversaciones del día → informe de fidelidad | nueva |
| O-03 | Panel `/admin` con las métricas del PRD §8 | aceptada → F4 |
| O-04 | Reutilizar el bot de Telegram de MultiBot como código base para las alertas | aceptada → F4 |

## Añadidas el 24-ago (noche)

| Id | Idea | Estado |
|---|---|---|
| I-16 | Selector de país en el widget (banderita) para el número de emergencias; por defecto el del navegador (`navigator.language`). | aceptada → F3 |
| I-17 | Expansión de sinónimos es→en para las 9 guías en inglés (hoy solo en→es). | nueva |
| I-18 | "Modo noche" como tema por defecto entre 22:00 y 07:00 hora local (la web como linterna). | nueva |
| I-19 | Router de intención: dosis (hecho), vacunas por edad (calendario tabulado, sin LLM), "¿urgencias?" (checklist), resto → RAG. | aceptada → F2 |
| I-20 | Reintroducir X solo si vuelve un tier gratuito; mientras, cola de posts en texto para pegar a mano. | aceptada |

## Añadidas el 25-ago (revisión del boceto + LLM real)

| Id | Idea | Estado |
|---|---|---|
| I-21 | **Web chat-first** (como ChatGPT/Claude): el cuadro de conversación ocupa la pantalla, el resto (cómo funciona, calculadora, fuentes, token) va debajo al hacer scroll. Paleta calma: blancos, crema, pasteles menta/melocotón/lavanda. | aceptada por el operador → boceto v2 |
| I-22 | **Fuente nombrada en la frase** ("Según la SEUP…", "La OMS recomienda…") además del [n] verificable. | aceptada → prompt `answer_v2` desplegado |
| I-23 | **Juez de fidelidad** (2.ª llamada al LLM que comprueba frase a frase contra los pasajes citados). Como métrica en `eval --llm --judge`; no como puerta en vivo (duplicaría coste y latencia). Nocturno sobre las conversaciones del día cuando haya tráfico. | aceptada → hecho en eval |
| I-24 | **Calculadora de dosis con marcas por país** (Calpol, Tylenol, Apiretal, Dalsy, Nurofen, Advil, Motrin, Doliprane, Panadol, Tachipirina, Alivium…) → `config/drugs.yaml`, `/api/dose`, `/api/drugs`. Solo paracetamol e ibuprofeno; aspirina, jarabes para la tos y antihistamínicos excluidos a propósito. | aceptada → hecho |
| I-25 | Contexto de edad y peso como "chips" en el compositor del chat (se envían con la pregunta; evita repetir la edad). | HECHA 25-ago (chips edad/peso/país en el compositor) |
| I-26 | Selector de idioma de interfaz (EN/ES) en la barra; el bot ya responde en el idioma del mensaje. | aceptada 25-ago → F3 |
| I-27 | "Tarjetas" de sugerencia en la pantalla de bienvenida con las 4 preguntas más frecuentes por temporada (bronquiolitis en invierno, golpe de calor en verano). | HECHA 25-ago (4.ª tarjeta cambia por temporada y hemisferio) |
| I-28 | Botón "Compartir esta respuesta" → enlace público a la respuesta (sin datos del usuario) para mandarla a la pareja/abuelos. | HECHA 25-ago (/api/share → /a/<token>, noindex, sin sesión) |
| I-29 | Calculadora de dosis como página propia con URL (`/dose/calpol-14kg`) para SEO: "how much calpol for a 14 kg child". | HECHA 25-ago (685 páginas /dose/<marca>-<kg>kg en EN y ES, 5-40 kg) |
| I-30 | Ampliar la calculadora a suero oral (cantidad por kg tras cada deposición, hoja SEUP) — determinista y muy preguntado. | HECHA 25-ago (prospecto AEMPS Sueroral + hoja SEUP vómitos → /api/ors y sección en /dose) |
| I-31 | Conversación con memoria corta (últimos turnos) para poder preguntar "¿y si además vomita?" sin repetir todo. El motor hoy es de un turno. | HECHA 25-ago (commit a478e1b) |
| I-32 | Aviso por Telegram cuando el saldo de DeepSeek baje del 20 % (`pedibot balance`) — parte del watchdog de F4. | aceptada → F4 |

## Investigación T-06 — Virtuals ACP (25-ago)

Virtuals tiene el **Agent Commerce Protocol (ACP)**: un mercado on-chain donde agentes de IA se contratan y pagan entre sí (roles Cliente / Proveedor / Evaluador; fases petición → negociación → escrow → evaluación → liquidación). En 2026 lanzaron la "Revenue Network" (hasta 1 M$/mes repartidos entre agentes que venden servicios por ACP) y ACP v2 (SDK/CLI unificados, wallet no custodial, multi-cadena). **Encaje para PediBot**: registrar "PediBot" como agente **proveedor** con un servicio "respuesta pediátrica con fuentes" (la misma API `/api/ask`) cobrando en PDBT o VIRTUAL — utilidad real del token **sin exigir nada al padre** (la web sigue gratis; pagan otros agentes). Riesgos: uso médico por agentes sin contexto → mantener el mismo triaje/disclaimer y **rechazar** peticiones fuera de ámbito; revisar los términos del ACP sobre servicios de salud. Coste: medio (SDK de Virtuals + un endpoint firmado). Estado: **aceptada por el operador; para después del despliegue (F4)**. Fuentes: whitepaper.virtuals.io (ACP, Commerce Layer, changelogs), rockawayx.com, prnewswire (feb-2026).

| I-33 | **Chatbot por Telegram** (mismo motor, sesión por chat, 👍/👎, /country, /lang). Pedido por el operador 25-ago. | HECHA 25-ago (`pedibot telegram`, unit systemd; falta el token del bot nuevo) |

## Visibilidad (25-ago) — plan de difusión sin presupuesto

| Id | Acción | Coste | Estado |
|---|---|---|---|
| V-01 | Google Search Console + Bing con sitemap y RSS | 0 | operador |
| V-02 | Bluesky @pedibot + canal Telegram @pedibot_news con sindicación automática diaria | 0 | hecho en código; faltan cuentas/credenciales |
| V-03 | X @pedibotai: pegar a mano desde `publish/queue/x/` o activar pago por uso (~6 $/mes) | 0-6 $/mes | operador decide |
| V-04 | Lanzamientos manuales honestos: Product Hunt, Hacker News "Show HN", r/Parenting, r/daddit, foros de crianza en español | 0 | tras la beta cerrada |
| V-05 | Pediatras y matronas que enlacen/revisen (W-06) | 0 | operador |
| V-06 | Directorios de herramientas de IA (There's An AI For That, Futurepedia, AI Tools) | 0 | tras la beta |
| V-07 | Comunidad Virtuals: perfil verificado (hecho), post de lanzamiento, ACP (T-06) | 0 | en curso |
| V-08 | Mastodon/Threads (API gratuita) como 3.º y 4.º canal automáticos | 0 | nueva |

## Lote del 26-ago (10 ideas propuestas; decisión del operador)

| # | Idea | Estado |
|---|---|---|
| 1 | Perfil del niño en el navegador (multi-hijo) | aceptada, **más adelante** |
| 2 | Vacunas tabuladas por país | **HECHA** (ES/GB/US desde documentos oficiales; `/vaccines`, `/api/vaccines`, enrutado en el chat) |
| 3 | Aclaración guiada en el chat | **HECHA** (mensaje vago con mención al niño → 7 opciones; nunca en seguimientos) |
| 4 | Calendario editorial por temporada | **HECHA** (`config/seasonal.yaml`; publish prioriza el mes) |
| 5 | Guías comparativas "qué dicen las guías" | **HECHA** (5 temas con ≥2 organismos, prompt `article_compare_v1` con tabla) |
| 6 | Widget embebible | aceptada, **más adelante** |
| 7 | Avisos de salud pública en la home | **HECHA** (WHO/PAHO/UKHSA/CDC, filtro estricto a eventos infantiles, máx. 3, 14 días) |
| 8 | Foto solo para signos de alarma (I-10b) | **HECHA** (`/api/photo`, botón 📷; vision-exp; nunca nombra enfermedades) |
| 9 | Panel privado `/admin` | **HECHA** (basic auth Caddy; métricas, PDBT, conversaciones, flag → golden set) |
| 10 | Virtuals ACP | **endpoint hecho** (`/api/agent/ask` con clave); registro como proveedor = operador, pasos en `ops/ACP.md` |

## Lote SEO del 10-sep-2026 — medido, en orden de prioridad

> Salen del primer diagnóstico con datos (Search Console + registro del servidor + auditoría del
> sitio construido). Lo que había que arreglar ya está arreglado (el sitemap que declaraba 296
> páginas cambiadas cada día, L121-L122); esto es lo que queda y **pide una decisión**.
>
> **El aviso honesto que va delante de la lista**: a ojos de Google el sitio tiene catorce días
> —primera impresión el 26-ago-2026, posición media 69— y en ese punto casi nada de lo de abajo
> mueve tanto como el simple paso del tiempo y que termine de rastrear. Las dos primeras sí son
> tapones de verdad: un motor entero al que no llegamos, y la señal que Google mira en salud.

| Id | Prioridad | Idea | Por qué | Coste | Estado |
|---|---|---|---|---|---|
| S-01 | **1** | **Averiguar por qué Bing no rastrea**, teniéndolo todo en regla | ~~Verificar el sitio en Bing Webmaster Tools~~ — **ya estaba hecho** (11-sep-2026): el sitio está verificado, el sitemap entregado y `ops/indexnow.py` avisando a diario. Lo propuse por inferir desde el comportamiento del rastreador sin comprobar el panel, que es la L123 otra vez. Lo que dice el registro completo: bingbot ha hecho **36 peticiones, de las que 17 son suplantadores** pidiendo `/api/.env` y `/credentials.json`; las reales son `robots.txt` ×7, los dos sitemaps ×5, la portada ×2 y **el fichero de la clave de IndexNow ×2** — o sea que IndexNow sí se está procesando. Bing lo sabe todo de nosotros y ha decidido no rastrear: dominio de dos semanas y sin enlaces entrantes. El tapón no es técnico | 0 € | **replanteada**: lo que falta son enlaces (V-04, V-05, V-06), no configuración |
| S-02 | **2** | **Página de «quién está detrás» + revisor médico**, y sólo entonces `reviewedBy` y `lastReviewed` en el JSON-LD | En salud (YMYL) es la señal de fondo, y hoy no existe: no hay página que explique quién hace esto ni con qué método, y las guías llevan `citation`, `datePublished` y `dateModified` pero ningún revisor. **La página se puede escribir ya y es honesta** (sólo fuentes, verificador de citas, sin anuncios, sin cuentas, sin rastreadores). Las dos propiedades del marcado **no**: ponerlas sin que un pediatra haya revisado sería mentir, y esa es la línea del proyecto | Bajo la página; el revisor depende de V-05 / W-06 | **hecha a medias (11-sep-2026)**: la página está viva en las ocho lenguas en `/about`, enlazada desde el pie, con las cifras contadas del catálogo y la frase «ningún pediatra ha revisado estos textos». Falta el revisor; hasta que lo haya, `reviewedBy` y `lastReviewed` siguen prohibidos y hay candado que lo comprueba |
| S-03 | 3 | **Deshacer los 11 pares de páginas de marca casi idénticas** (por idioma): o se diferencian por presentación y concentración, o se consolidan con canónica | Máximo medido: **97 % de solapamiento de 5-gramas entre apirofeno y junifen** (mismo principio activo y mismas presentaciones); 11 pares por encima del 70 %. Es la forma clásica de acabar en «rastreada y descartada», que es exactamente donde están 28 páginas | Medio | nueva |
| S-04 | 4 | **Acortar los 157 títulos de más de 60 caracteres** | Se cortan en el resultado y se llevan por delante la parte que convence. Afecta al CTR, que hoy es 0,29 % | Bajo | **hecha (11-sep-2026)**: eran 166 medidos sobre el título decodificado. Arreglado en la plantilla: si no cabe, primero se cae «— PediBot», y si aún no cabe se corta por una pausa del propio título. 0 de 804 pasan de 60; el h1 y la tarjeta social siguen enteros |
| S-05 | 5 | **Bloquear AhrefsBot y SemrushBot en `robots.txt`** | 1.715 peticiones en 7 días que no traen a nadie. A cambio, dejaríamos de aparecer en las herramientas con las que otros analizan la competencia — que puede interesar o no | Bajo | nueva — decisión del operador |

**Lo que este lote NO incluye, a propósito**: nada de comprar enlaces, granjas de contenido ni
directorios de pago. La lista «nunca hacer esto» de `CLAUDE.md` ya lo cubre para el token y vale
igual aquí.

## Lote del 19-sep-2026 — la ficha del niño: darse de alta y llevar su curva

> Pedido por el operador el 19-sep: «quiero que puedas darte de alta tanto en web como en app
> para guardar datos de tus hijos y que dé los datos directamente y puedas apuntar la curva de
> crecimiento y peso». Anotado para decidirlo después; nada de esto está construido.

### Qué sería

Una **ficha por hijo** —nombre o mote, fecha de nacimiento, sexo, país— y un **historial de
medidas** (peso, talla, perímetro craneal, con su fecha). Con eso:

- el chat **deja de preguntar la edad y el peso**: los sabe, y la respuesta sale directa. Hoy hay
  dos desplegables que el padre rellena en cada pregunta, y si no los toca, la respuesta pide la
  edad que ya estaba escrita en la frase;
- la **calculadora de dosis** deja de necesitar que se teclee el peso;
- la curva de crecimiento deja de ser un punto suelto y pasa a ser **la línea de ese niño**: sus
  medidas sobre las tablas de la OMS, que es justo lo que enseña la cartilla y lo que un padre
  quiere comparar;
- el **calendario de vacunas** se vuelve suyo: no «a los 4 meses toca», sino «el 12 de octubre
  toca», que es lo que hace falta para los recordatorios de la app (D-A3 en `APP.md`).

### La tensión, dicha antes que nada

Hoy `/legal` promete esto, con estas palabras, en las ocho lenguas: **«No account, no name, no
e-mail. We never ask for personal data and you should not type any.»** Y es medio argumento del
proyecto: un sitio gratis que no pide nada y del que no hay nada que perder.

Lo que el operador pide es **datos de salud de un menor identificado**, que en el RGPD es
categoría especial (artículo 9) con el consentimiento del titular de la patria potestad, y que en
las dos tiendas cambia las declaraciones de privacidad de arriba abajo (Apple 5.1.3, el
formulario de *Data safety* de Google). No es un no: es que la forma de hacerlo decide si esto
suma o si nos come.

### Por dónde lo haría, en dos fases

**Fase 1 — la ficha vive en el aparato, sin cuenta.** Es el 90 % del valor y no toca la promesa:
lo que está en el teléfono no lo tenemos nosotros. El diario de síntomas (`pedibot_diary`) y el
país ya funcionan así desde agosto, y esto es lo mismo con más campos. En la app es todavía mejor,
porque es un fichero suyo y no un `localStorage` que el navegador borra cuando quiere. Coste
medio: la ficha, el historial, la curva dibujada con las medidas encima y el enganche con el chat
y con la calculadora. Extiende la I-13, que ya estaba anotada.

**Fase 2 — cuenta, y sólo para lo que la fase 1 no puede: cambiar de teléfono sin perderlo.** Y
ahí, tres condiciones que yo no me saltaría:

1. **Opcional siempre.** Quien no quiera cuenta sigue usándolo entero. La portada no pide
   registrarse.
2. **Cifrado en el aparato**, de modo que el servidor guarde un bulto que no puede leer. Si
   nosotros no podemos leer el peso de su hija, media conversación legal desaparece y la promesa
   de `/legal` se puede reescribir sin mentir: «no podemos ver lo que guardas».
3. **Exportar y borrar en un botón**, y borrar que borre de verdad.

Lo que costaría de más: el alta (mejor con *passkey* o enlace por correo que con contraseña), la
recuperación —que con cifrado de extremo a extremo es el problema difícil de verdad, porque
perder la clave es perder los datos—, reescribir `/legal` en ocho idiomas, los dos formularios de
tienda y una política de borrado. **Alto.**

| Id | Idea | Estado |
|---|---|---|
| I-16 | **Ficha por hijo + historial de medidas** (extiende I-13): el chat deja de preguntar la edad y el peso; la curva se dibuja con sus medidas | **HECHA 19-sep**, y no «en el aparato»: el operador eligió la fase 2 directamente, con cuenta en el servidor |
| I-17 | **Curva propia sobre las tablas de la OMS**: los puntos de ese niño a lo largo del tiempo, no un percentil suelto | **HECHA 19-sep** (`/api/growth/bands` + el SVG de `Family.astro`, sin bibliotecas) |
| I-18 | **Calendario de vacunas con fechas reales** a partir de la fecha de nacimiento, y de ahí los recordatorios de la app (D-A3) | a medias: el chat ya contesta por la edad del hijo («¿qué vacunas le tocan a Laura?»); faltan las FECHAS en la ficha y el aviso |
| I-19 | **Cuenta opcional**, con correo y contraseña, exportar y borrar | **HECHA 19-sep.** Decisión del operador: fase 2 directamente y sin cifrado en el cliente, «la cuenta puede ser simplemente un email y una contraseña». `/legal` reescrita en ocho idiomas: ya no dice «sin cuenta» sino «no hace falta cuenta». Queda pendiente lo que necesita correo saliente: verificar la dirección, recuperar la contraseña y el propio boletín |

### Lo que la cuenta dejó pendiente (19-sep-2026)

| Id | Idea | Por qué | Estado |
|---|---|---|---|
| I-20 | **Correo saliente** (Resend, Brevo, SES…) | Sin él no hay verificación de la dirección, ni «he olvidado mi contraseña», ni boletín: las tres cosas que la cuenta promete y todavía no puede | nueva; decide el operador el proveedor y quién paga |
| I-21 | **Fechas reales de vacunas por hijo** y aviso antes de cada una | Es lo que convierte el calendario en algo que se usa dos veces al año en vez de leerse una | nueva; con D-A3 de `APP.md` |
| I-22 | **La foto del hijo en su ficha** | Sale en las capturas que mandó el operador y es lo que hace que la pantalla parezca suya. Cuesta poco y obliga a decidir dónde se guarda una imagen de un menor | nueva |
| I-23 | **Perímetro craneal sobre su tabla** | Se puede apuntar ya, pero no hay banda que dibujar: falta la tabla `hcfa` de la OMS en `who_growth.json` | nueva |

### La vía que sostiene el proyecto (19-sep-2026, del operador)

> «En el futuro nuestro motor se le puede vender a apps de seguros médicos, hospitales o
> consultas privadas para el primer triaje y clasificación de pacientes, para sostener el
> proyecto y que siga siendo gratis para quien lo necesite de verdad.»

Es la primera vía de ingreso que no contradice el proyecto, y conviene entender por qué: **lo que
se licencia es el motor, no la gente**. Las reglas, las tablas de dosis, el catálogo de fuentes y
la clasificación de urgencia; nunca los datos de nadie, que es la línea que no se cruza y que
`/legal` promete en ocho idiomas.

Y encaja con lo que ya está construido: el triaje es determinista (83 reglas con su fuente, no un
modelo), lo cual es justo lo que una institución necesita para poder auditarlo y responder de
él. Un hospital no puede justificar una clasificación hecha por un modelo que no explica por qué;
sí puede justificar una regla escrita, con su documento detrás y su prueba.

| Id | Idea | Por qué | Estado |
|---|---|---|---|
| I-24 | **Licenciar el motor de triaje** a aseguradoras, hospitales y consultas privadas para el primer filtro y la clasificación de pacientes | Sostiene el proyecto sin tocar lo que lo hace honesto: para el padre sigue siendo gratis, sin anuncios y sin venta de datos | nueva (operador, 19-sep). Antes hace falta: medir la concordancia del triaje con la clasificación de un profesional, y decidir la forma legal (producto sanitario en la UE si se usa para decidir sobre pacientes) |
| I-25 | **Medir el triaje contra un pediatra** en un lote de casos reales | Es el requisito de I-24 y además mejora el producto gratis: sin esa medida no hay conversación posible con una institución | nueva; necesita a los pediatras revisores de W-06 |

## I-26 · Backable, la vía sin curar de MetaDAO (20-sep-2026)

La solicitud curada se envió el 20-sep-2026. Su propio acuse dice dos cosas que conviene leer
juntas: que el proceso curado «no es muy distinto de un VC», y que **no recibir respuesta es lo
normal**. Recomiendan la vía sin permiso, backable.biz, y ahí no hay que esperar a nadie.

Mecánica, de su guía y su FAQ:

- objetivo entre 10.000 y 2.000.000 $; **el 80 % va a tesorería y el 20 % a liquidez**, así que
  lo que la empresa puede gastar es el 80 % de lo que se pide;
- presupuesto mensual topado en **objetivo ÷ 6**, y gastar por encima del presupuesto exige una
  propuesta aprobada por el mercado;
- si no se llega al objetivo, cada uno reclama el 100 % de lo suyo (la reclamación no es
  automática); los 15 $ del borrador no se devuelven;
- el paquete del fundador se bloquea **18 meses** y luego se abre en cinco tramos a 2x, 4x, 8x,
  16x y 32x del precio de entrada, y sólo mientras la media de tres meses aguante por encima del
  umbral. Si nunca llega a 2x, no se abre nada;
- la entidad legal la forma MetaLeX dentro del propio flujo, sin coste aparte;
- una venta de la empresa o un cierre exigen propuesta, diciendo qué pasa con tesorería, paquete
  y propiedad intelectual;
- cada ronda publica un `agents.md` para que la lean los asistentes. Aquí ya existe `llms.txt`:
  es el mismo gesto y encaja solo.

**La cuenta que hay que hacer antes de nada.** El plan aprobado son 210.000 $ de gasto, 17.500 al
mes durante un año. Con un objetivo de 210.000 la tesorería serían 168.000, o sea 14.000 al mes.
Para que el plan salga tal cual está escrito, el objetivo tiene que ser **262.500 $**: el 80 % de
eso son los 210.000 de siempre, y el resto se queda en liquidez sin llegar nunca a la empresa.
Eso se dice en una frase y se entiende; lo que no se puede es pedir 210.000 y prometer 17.500 al
mes, porque no salen.

Los seis capítulos del asistente son Company, Raise, Pitch, Controls, Legal y Review. Los cinco
primeros están casi escritos: el memo de /memo es el Pitch, el desglose del gasto es el Raise, y
los riesgos ya están redactados. Lo que **no** está decidido y es suyo: qué cartera firma y si va
sola o con varias firmas (Controls), y si se forma la entidad de MetaLeX o se usa una propia
(Legal).

## I-27 · Las curvas de los cinco del norte de África (20-sep-2026)

`config/growth_charts.yaml` cubre 69 países, 49 de ellos africanos. Faltan **Marruecos, Argelia,
Túnez, Libia y Sudán**, que son justo los cinco que entraron esta semana con calendario de
vacunas.

Lo que **no** falta, y conviene tenerlo claro antes de tocar nada: el percentil ya se calcula
bien para ellos. Una madre marroquí que escribe «mi hija de 18 meses pesa 9 kg, ¿está bien?»
recibe hoy su percentil 14,5 con las tablas de la OMS. Lo que falta es la página `/growth/ma`,
que es la que dice **qué tabla usa la cartilla de su país**, para que pueda comparar el número
de aquí con el papel que tiene en casa.

Los 49 africanos que sí están usan el cuadernillo AIEPI de la OMS/UNICEF como fuente, con
`match: partial`. Sería cómodo extender eso a los cinco y cerrar el mapa, y **no se ha hecho a
propósito**: el propio fichero dice que no se añade un país por suposición, y no he encontrado
confirmación de que esos cinco usen ese cuadernillo. Egipto, que sí está, tiene su propia fuente
del Ministerio de Salud y Población.

Lo que hace falta es leer, por país, qué curva trae su cartilla:

- Marruecos: «carnet de santé de l'enfant» del Ministère de la Santé;
- Túnez y Argelia: el carnet de santé de sus ministerios;
- Sudán y Libia: el registro infantil del ministerio, o la implantación regional de AIEPI
  documentada por la oficina de la OMS para el Mediterráneo Oriental.

Es trabajo de leer y transcribir, no de programar, y es exactamente la clase de cosa que la
partida de «segunda persona a media jornada» del plan de financiación paga.

## I-28 · Etiopía, el Congo, Angola y Mozambique: qué falta y qué NO se ha inventado (20-sep-2026)

Las marcas africanas pasaron de 1 país a 31. Los cuatro grandes que siguen sin ninguna suman
unos 300 millones de personas: **Etiopía (126 M), RD Congo (102 M), Angola (36 M) y Mozambique
(33 M)**.

Lo que se buscó y lo que salió, para que nadie repita el trabajo:

- **Etiopía tiene registro público y sirve.** La EFDA publica la *List of Medicines for Drug
  Shop* y una lista de medicamentos sin receta. Leídas: incluyen «Acetaminophen/Paracetamol
  Drops 100mg/ml» y «Ibuprofen Oral liquid 100mg/5ml». Hay además productos registrados con
  nombre propio, como **Parakant** (solución pediátrica 120 mg/5 ml, con su ficha en la EFDA).
  Falta decidir si una marca de ese tamaño merece entrar o si lo que ayuda allí son las
  concentraciones, que es lo que un padre lee en la caja de un genérico.
- **RD Congo**: sólo aparecen farmacias francesas vendiendo Doliprane y la Lista Nacional de
  Medicamentos Esenciales de 2020 (alojada en la OMS). Doliprane es LA marca del África
  francófona y sería cómodo extenderla, pero **no se ha hecho**: no encontré una fuente
  congoleña que lo diga, y el Congo es demasiado grande para añadirlo de oído.
- **Angola y Mozambique**: nada concluyente. Salen cadenas de farmacias reales —Mecofarma en
  Luanda, Farmácias de Moçambique en Maputo— y Bluepharma distribuyendo allí desde 2011, pero
  ninguna fuente que diga qué jarabe pediátrico se vende. Ben-u-ron es portugués y es plausible;
  plausible no es una fuente.

**La regla que se siguió, y que conviene no aflojar**: una marca dice al padre «esto que tienes
en la mano es esto». Meter un país de oído convierte esa frase en una suposición, y la frase
entera deja de valer. Es mejor no reconocer el bote que reconocerlo mal.

Lo que sí se hizo mientras tanto, y no necesitaba datos nuevos: **los botes que se venden en tu
país salen primero** aunque no escribas la marca, dándole la vuelta a la tabla de marcas. En
Marruecos, Argelia y Túnez eso sube la única concentración que se vende allí desde el fondo de
una lista de ocho.

## I-29 · Abrir el repositorio: qué abre y qué cuesta (20-sep-2026)

Sale al mirar financiación con el nombre ya expuesto, y es una decisión del operador, no mía.
Hoy el repositorio es privado: comprobado el 20-sep-2026, `github.com/nicolasbeca/pedibot`
devuelve 404 a quien no tenga permiso.

**Lo que se abre si se abre.** El reconocimiento de bien público digital lo exige, y con él el
vocabulario con el que hablan UNICEF, la OMS y los ministerios. NLnet lo exige —de 5.000 a
50.000 €, y un particular puede pedirlo—. Una parte grande de las becas de software libre lo
exige. Y en el Show HN, que es la vía de exposición más barata que hay, «el código está aquí»
cambia cómo se lee todo lo demás: ese público audita antes de creer.

**Lo que cuesta.** El trabajo de años queda copiable en una tarde. Aunque conviene mirar bien
qué se copia: las reglas de alarma salen de guías públicas, y el catálogo de fuentes ya está en
dominio público y se descarga entero desde el sitio. Lo que no es copiable es haberlas reunido,
cruzado por país y probado; eso es el histórico de commits, no un fichero.

**Un término medio que probablemente es la respuesta:** abrir el motor —triaje, dosis, crecimiento,
vacunas, con sus pruebas— y dejar fuera lo operativo: despliegue, claves, el panel, `ops/` entero
y los ficheros de trabajo. Cumple los requisitos de las becas, da la credibilidad del Show HN, y
no regala ni la infraestructura ni la estrategia. Falta comprobar una cosa antes de nada: que no
haya quedado ninguna clave en el histórico, porque abrir un repositorio publica también su
pasado.

## I-30 · El zinc, y por qué en Kenia la OMS tiene que ir delante (20-sep-2026)

Probando la web viva como un padre en los mercados a los que vamos, con preguntas escritas como
las escribe un padre y no como las escribe un programador. El caso: *«my baby is 7 months and has
watery diarrhoea since yesterday»*, con Kenia seleccionada.

La respuesta es correcta y segura: suero de rehidratación en cantidades pequeñas y frecuentes,
nada de refrescos ni preparados caseros, no dar antidiarreicos, y cuándo ir al médico. Cita a
MedlinePlus y a la SEUP.

**Lo que no dice: el zinc.** Y en Kenia, en Nigeria, en Etiopía y en la India, el zinc no es un
detalle: es la mitad del tratamiento estándar. La OMS lo recomienda de 10 a 14 días, acorta el
episodio alrededor de un 25 % y reduce el volumen de heces alrededor de un 30 %, y es política
nacional en esos países. Que no aparezca en una respuesta sobre diarrea a un lactante allí es un
hueco real.

**Lo comprobado antes de proponer nada, que es lo que cambia el diagnóstico:**

- El documento de la OMS **sí está en el corpus**, en tres idiomas, con su ficha y su cita.
- Y **sí sale** cuando la pregunta es de tratamiento: preguntando «should I give my child zinc
  for diarrhoea» contesta con la OMS delante y las dos cifras. Preguntando «my 1 year old has had
  diarrhoea for 3 days in Kenya, what treatment» también lo menciona.
- O sea que **no falta información y no hay que añadir fuentes.** Lo que pasa es que cuando el
  padre describe un síntoma en vez de pedir un tratamiento, ganan las fuentes europeas, que no
  hablan de zinc porque en Europa no se usa así.

**Lo que habría que hacer, y es pequeño:** cuando la pregunta es de diarrea en un menor de cinco
años **y el país es uno donde la diarrea sigue siendo causa mayor de muerte infantil**, empujar
los términos de la OMS en la recuperación —suero de rehidratación y zinc— aunque el padre no los
haya nombrado. No es inventar nada ni cambiar el texto: es que el documento que en ese país es la
norma nacional entre entre los pasajes que el modelo tiene delante.

**Lo que NO hay que hacer:** meter el zinc a mano en la respuesta. La dosis depende de la edad
—son distintas por debajo y por encima de los seis meses— y eso es una cifra, o sea que va por la
vía de las dosis, con su fuente, o no va. Una recomendación de suplemento sin dosis y sin fuente
es exactamente lo que este proyecto no hace.

**Y la lección de método, que vale más que el caso:** esto no salió leyendo código. Salió
escribiendo la pregunta como la escribe un padre de Nairobi a las tres de la mañana. Es la
séptima vez que ese método encuentra algo y el código no.

**Y por qué NO lo he aplicado hoy, aunque el resto de mejoras de esta tanda sí se han aplicado
directas:** porque el empujón necesita saber *en qué países* la norma es la de la OMS, y esa
lista no existe en el repositorio ni la he encontrado en una fuente que se pueda citar. Podría
escribir «los 54 africanos y los del sur de Asia» y sonaría razonable, pero sería exactamente lo
que no se hizo con las marcas de Etiopía y del Congo: **plausible no es una fuente.** Y la
alternativa de meter el documento de la OMS siempre, en todos los países, cambia también la
respuesta en España, donde el zinc no es práctica habitual, y eso ya es criterio clínico y no
mío.

Lo que hace falta para desbloquearlo es una sola cosa citable: una lista de países donde el zinc
en la diarrea infantil sea política nacional, o una clasificación de renta que se pueda citar y
descargar. Con eso, el cambio son veinte líneas y una prueba.

**Actualización de media hora después, porque la fuente estaba dentro del propio documento.** El
texto de la OMS que ya tenemos indexado acota él mismo dónde aplica: *«Diarrhoea due to infection
is widespread throughout developing countries. In low-income countries, children under 3 years
old experience on average three episodes of diarrhoea every year»*, y pone el zinc y el suero
juntos como las medidas clave de tratamiento. O sea que **no hay que inventarse el criterio: lo
da la fuente**.

Lo que falta entonces es sólo traducir «low-income countries» a una lista, y de eso sí hay una
publicada, anual y descargable: la clasificación por renta del Banco Mundial (renta baja y
media-baja). Con eso el cambio queda sostenido de punta a punta —la OMS dice dónde, el Banco
Mundial dice cuáles— y se puede escribir sin suponer nada.

Queda para la siguiente tanda, después de subir lo que hay pendiente, porque implica traer un
fichero de datos nuevo con su ingesta y sus pruebas, y no es algo que se meta a medias entre dos
despliegues.
