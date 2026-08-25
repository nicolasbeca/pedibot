# IDEAS.md — cuaderno de ideas y mejoras sin decidir

> Aquí se anota todo lo que surja. Nada de esta lista se implementa sin decidirlo juntos. Cada idea: qué es, por qué podría valer, qué costaría, y estado (`nueva` / `aceptada → fase` / `descartada: motivo`).

## Producto — funciones que no son "ChatGPT"

| Id | Idea | Por qué | Coste | Estado |
|---|---|---|---|---|
| I-01 | **Comparador de medicamentos de venta libre** (paracetamol vs ibuprofeno; jarabes para la tos que NO recomienda la AEP; sueros de rehidratación) con tabla de edad mínima, dosis, intervalo, cuándo no dar | Pregunta real y frecuente; determinista; muy compartible | Medio (tablas + página) | nueva (mencionada por el operador) |
| I-02 | **"¿Debo ir a urgencias?" interactivo**: checklist guiada por edad y síntoma a partir de la hoja SEUP/AEP, sin LLM | Es el caso de uso nº 1 y se puede hacer 100 % determinista | Bajo | nueva |
| I-03 | **Diario de síntomas** local (en el navegador, sin cuenta): temperatura, dosis dadas y hora → evita doble dosis y da al pediatra un registro | Utilidad diaria real; sin datos en servidor (localStorage) | Medio | nueva |
| I-04 | **Recordatorio de próxima dosis** (notificación del navegador) | Complementa I-03 | Bajo | nueva |
| I-05 | **Calculadora de percentiles con curva dibujada** (OMS 0-5, y OMS 5-19) | Los padres lo buscan mucho; SEO | Medio | nueva |
| I-06 | **"Explícaselo a mi hijo"**: versión de la respuesta para leer a un niño de 5-10 años | Diferenciador cálido; barato (un prompt) | Bajo | nueva |
| I-07 | **Modo pediatra**: respuesta con el nivel de la guía clínica (Manual PUC, antibióticos Donostia) para profesionales, con toggle | Segundo usuario; las fuentes ya están | Bajo-medio | nueva; ojo con responsabilidad |
| I-08 | **Voz** (dictar la pregunta, escuchar la respuesta) — Web Speech API gratis | Padre con el niño en brazos | Bajo | nueva |
| I-09 | **WhatsApp** (Cloud API, gratis hasta cierto volumen) | Canal natural de padres | Medio-alto; verificación Meta | nueva |
| I-10 | **Fotos**: "¿qué es este sarpullido?" con modelo de visión | Muy demandado, muy arriesgado clínicamente | Alto | descartada por ahora: riesgo |
| I-11 | **Mapa de urgencias pediátricas cercanas** (OpenStreetMap) | Cierra el "ve a urgencias" con "¿dónde?" | Medio | nueva |
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
| W-06 | Colaboración con pediatras para "revisado por" en los artículos | nueva; muy valioso para confianza y SEO (E-E-A-T) |
| W-07 | Búsqueda del sitio con el mismo índice del bot | nueva |
| W-08 | CAPTCHA/Turnstile si aparece abuso del rate limit | nueva |

## Token PDBT

| Id | Idea | Estado |
|---|---|---|
| T-01 | Página `/apoya` con libro de cuentas público y recompras verificables on-chain | aceptada → F3/F6 (detalle en PRD §9, duda D-09) |
| T-02 | Actualizar el perfil del agente en Virtuals con la web nueva y enlaces | nueva |
| T-03 | Muro de "familias que apoyan" (firma opcional de wallet) | nueva |
| T-04 | Acceso anticipado a features para holders — SIEMPRE gratis para todos después | nueva |
| T-05 | Informe mensual "estado de PediBot" en X: consultas, coste, fuentes nuevas, recompras | aceptada → F6 |
| T-06 | Explorar si Virtuals ACP (agent commerce) permite que PediBot sea un "agente" invocable por otros agentes con pago en PDBT — utilidad sin gating al usuario humano | nueva; investigar |
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
| I-25 | Contexto de edad y peso como "chips" en el compositor del chat (se envían con la pregunta; evita repetir la edad). | nueva (en el boceto v2) |
| I-26 | Selector de idioma de interfaz (EN/ES) en la barra; el bot ya responde en el idioma del mensaje. | nueva |
| I-27 | "Tarjetas" de sugerencia en la pantalla de bienvenida con las 4 preguntas más frecuentes por temporada (bronquiolitis en invierno, golpe de calor en verano). | nueva |
| I-28 | Botón "Compartir esta respuesta" → enlace público a la respuesta (sin datos del usuario) para mandarla a la pareja/abuelos. | nueva |
| I-29 | Calculadora de dosis como página propia con URL (`/dose/calpol-14kg`) para SEO: "how much calpol for a 14 kg child". | nueva |
| I-30 | Ampliar la calculadora a suero oral (cantidad por kg tras cada deposición, hoja SEUP) — determinista y muy preguntado. | nueva |
| I-31 | Conversación con memoria corta (últimos turnos) para poder preguntar "¿y si además vomita?" sin repetir todo. El motor hoy es de un turno. | nueva; prioridad alta |
| I-32 | Aviso por Telegram cuando el saldo de DeepSeek baje del 20 % (`pedibot balance`) — parte del watchdog de F4. | aceptada → F4 |
