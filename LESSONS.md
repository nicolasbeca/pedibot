# LESSONS.md — lecciones aprendidas de PediBot

> Consulta obligada antes de implementar algo nuevo. Se añade una entrada por cada fallo, corrección o sutileza no documentada. Las L0x son heredadas de la v1 (n8n/OpenAI/Wix) y de MultiBot, y siguen vigentes.

## Heredadas de la v1 de PediBot (2025)

- **L01 — No-code sin control del retrieval no sirve para un bot médico.** n8n + OpenAI daba respuestas fluidas pero no había forma de forzar citas verificables ni de medir si el bot acertaba. Un bot que cita fuentes necesita controlar el troceado, el índice y el verificador. → v2 en código propio.
- **L02 — Coste fijo mata a un producto gratuito con poco uso.** Wix Premium + vector DB gestionada + OpenAI eran cuota mensual independientemente del tráfico. → v2: VPS barato, SQLite, LLM de pago por uso.
- **L03 — Las métricas de tracción del dossier no estaban instrumentadas.** "100 usuarios/día" y "9,8 % CTR" salían de Meta Ads y de Wix; no había medición propia ni por consulta. → v2: cada consulta se registra con coste, fuente y feedback; no se publica ninguna cifra que no salga de la DB.
- **L04 — Las credenciales en un `.txt` acaban en cualquier sitio.** `pass.txt` con claves de 5 servicios en claro dentro de la carpeta del proyecto. → `.env` + `.gitignore` + rotación (deuda D1).
- **L05 — Las fuentes hay que catalogarlas ANTES de indexarlas.** En la v1 se subieron PDFs sueltos a un vector store sin organismo, año ni licencia; imposible citar bien y dudas de copyright después. → catálogo con `uso` por documento y esquema de chunk con cita completa.

## Heredadas de MultiBot (aplican aquí)

- **L06 — AVG inyecta `SSLKEYLOGFILE` y mata procesos Python con TLS en el Windows local** (MultiBot L65). Cualquier script local que llame a una API HTTPS puede morir en silencio. → Guard en `conftest.py`; scripts con red se ejecutan en el VPS.
- **L07 — Los wrappers `.sh` a 100644 pierden `+x` en checkout** (MultiBot, go-live 2026-07-06). → Los units de systemd invocan `uv run …` directamente, o el deploy hace `chmod +x`.
- **L08 — `exec` en pipeline ≠ reemplazar al shell** (MultiBot L71): el SIGINT de systemd moría en bash. → Sin pipes en `ExecStart`; logs por journald.
- **L09 — Outbox SQLite para Telegram con retry** funciona y es barato. → Reutilizar el patrón, no reescribir.
- **L10 — Un cambio sin golden set es un cambio sin medir.** MultiBot exige walk-forward y sensibilidad antes de desplegar; aquí el equivalente es `make eval` sin regresión. Sin excepciones.

## Propias de la v2

(Se añaden a partir de F1.)

- **L11 — Las guías en formato tabla se trocean en confeti si se confía en la detección de títulos.** La guía de dosificación AEPap produjo 693 chunks, 422 de ellos de < 15 palabras (cada nombre de fármaco en mayúsculas era "título"). → `merge_small` fusiona los trozos < 40 palabras en el vecino conservando el título dentro del texto ("PARACETAMOL: …"). De 6.981 chunks a 4.792, y solo 10 pequeños.
- **L12 — Nombres de fichero con ñ vienen descompuestos (n + U+0303) desde Windows.** `14_Estreñimiento.pdf` no casaba con el catálogo y pdftotext (Git Bash) devolvía 0 palabras, lo que se interpretó como "escaneado". → normalizar NFC en ambos lados; era un PDF con texto.
- **L13 — YAML convierte `112` o `911` en enteros.** Un `re.escape(112)` revienta con un TypeError críptico dentro de `re`. → `str(k)` siempre en listas de palabras clave; o entrecomillar en el YAML.
- **L14 — `\b` dentro de un heredoc de Python no crudo es un BACKSPACE.** Al generar código con `python - <<'EOF'` y cadenas normales, `"\b"` se escribe como `\b` (0x08) invisible en el fichero y la regex deja de casar sin error. → escribir regex siempre con `r"..."` en el fichero final y comprobar `'\x08' not in text` tras generar código.
- **L15 — BM25 no encuentra tablas.** "how much paracetamol for 12 kg" no sube la tabla pediátrica de la AEPap aunque exista. → las preguntas de dosis con peso van por un enrutador determinista a la calculadora (sin LLM); los embeddings quedan para F2.
- **L16 — El modelo repite las instrucciones del prompt como si fueran de la fuente.** El juez de fidelidad (25-ago, 54 respuestas) dio 74 % "fiel"; 6 de las 8 "infieles" eran frases como "debe ser evaluado hoy" o "no le dé medicación" que venían de NUESTRO contexto de edad/banner, no de un pasaje citado. Verdaderas y seguras, pero no citables → el juez las marca. → Cuando una regla de triaje dispara, se inyecta el chunk de signos de alarma de SU fuente (`seup_acudir_urgencias`, etc.) como primer pasaje, y el prompt pide citar el pasaje [WARNING SIGNS] o, si no existe, decirlo sin atribuirlo a ningún organismo.
- **L17 — El boost de "signos de alarma" contamina entre temas.** Con una pregunta de fiebre, el chunk "cuándo consultar" de la hoja de GOLPE DE CALOR subía (contiene "fiebre") y el modelo atribuía sus umbrales (39 °C) a la hoja de fiebre. → el boost de red flag solo se aplica a chunks del mismo tema que la pregunta.
- **L18 — En ACP, `acp job list --all` se cuelga con la política `restricted`.** El `--all` (y `--legacy`) añade los trabajos del contrato viejo, que se leen **on-chain**; la política del firmante deniega esa llamada RPC y la CLI se queda esperando una aprobación manual que nadie va a dar. Medido el 26-ago: `acp job list` a secas devuelve `{"jobs":[]}` en **3 s**; con `--all`, tres minutos y ni un dato — el sondeo del proveedor se quedaba muerto en cada ciclo. → sondear siempre con `acp job list` a secas (v2, REST puro), y desconfiar de cualquier subcomando de la CLI que toque la cadena.
- **L19 — El vigilante no se vigilaba a sí mismo.** `ops/watchdog.py` comprobaba el API, el saldo de DeepSeek y el disco, pero no que los servicios estuvieran vivos: si `pedibot-telegram` o el trabajador de ACP se paraban, el silencio era idéntico al de un día sano. → `dead_units()` comprueba `systemctl is-active` de los cuatro units cada 10 min y avisa por Telegram; lo que no se puede leer cuenta como parado (fail-loud), y funciona sin privilegios de root.

- **L20 — El puente entre idiomas solo se abre donde no hay fuente en el idioma de la pregunta.** La tabla completa español→inglés (70 entradas) hundió el acierto de fuente de 0,964 a 0,891: para una pregunta en español sobre fiebre, las hojas del NHS y MedlinePlus adelantaban a la del SEUP. Preferir la lengua de la pregunta fue todavía peor, porque el corpus es asimétrico (49 PDF en español, 163 páginas en inglés) y **las mejores hojas para padres están en español**: penalizarlas rompía las preguntas en inglés, que las necesitan. Lo que funciona: 11 entradas para lo que de verdad no existe en español (sueño, pantallas, actividad física), comprobado documento a documento, y con términos distintivos ("sleep duration", no "sleep" a secas, que se pierde entre las palabras españolas). Resultado: 60/60 del golden set.
- **L21 — Un guard de seguridad demasiado ancho bloquea contenido legítimo.** El verificador rechazaba cualquier cifra en mg **o ml** sin tabla de dosis entre las fuentes. Eso paraba en seco las guías de vómitos y gastroenteritis, cuyas fuentes dan volúmenes de **suero oral** (5-10 ml cada 10 min, SEUP) — que no son una dosis de medicamento. Estrechado por el lado seguro: los mg siempre cuentan; los ml solo se perdonan si alrededor (±90 caracteres) se habla de suero, agua, leche o tomas y no aparece ningún medicamento; y si el contexto no está claro, **cuenta como dosis**. Un falso positivo cuesta un artículo; un falso negativo, una dosis inventada.
- **L22 — `citar_solo` era una intención, no una regla.** El generador de artículos filtraba por licencia los pasajes de apoyo pero **no** los documentos ancla de cada tema, y el de atragantamiento estaba anclado en un libro con ISBN sin licencia de redistribución. No llegó a publicarse ningún artículo desde él (el tema aún no había salido). Arreglado el filtro y puesto un test que recorre los 78 temas y falla si alguno apunta a algo que no sea `publico`.
- **L23 — El modelo escribe en el idioma de sus fuentes aunque el prompt pida otro.** Un tema español generado con `--lang en` produjo una guía **en español dentro de `/en`** y con `lang: en` en el frontmatter, lo que además rompe canonical y hreflang. Doble arreglo: el verificador del artículo comprueba el idioma del texto y lo rechaza si no coincide (con reintento), y los temas con sufijo `_en` (anclados en calendarios de NHS/CDC) ya no se ofrecen en español, donde solo generaban una guía gemela del calendario español.
- **L24 — Palabras con doble sentido citaban la hoja equivocada.** Sondeando preguntas que el corpus NO cubre salieron respuestas seguras y falsas: «se hace **pis** en la cama» llegaba a la hoja de deshidratación (`pis → deshidratación`, pensado para «orina poco»), «le han **oído** un soplo» a la de otitis (*oído* de oír, no de oreja) y «un bulto en el **pecho**» de un niño de 11 años a la guía de lactancia materna. → esos disparadores pasan a ser **frases** («duele el oído», «dar el pecho», «poco pis»), que la expansión ya soporta. Dos de los tres casos quedan en silencio o aclaración, que es la respuesta correcta cuando no hay fuente.
- **L25 — Un umbral de relevancia NO separa "cubierto" de "no cubierto" (medido y descartado).** Se probaron dos: (a) un suelo absoluto de puntuación bm25 y (b) un mínimo de cobertura de términos. Los rangos se solapan con casos legítimos — la pregunta g23 acierta con **1 término de 7** y 42 puntos, mientras que «se hace pis en la cama» saca 10 puntos con 1 de 3; y una puntuación bm25 **no es comparable entre corpus** (el suelo silenció los 19 tests con índices sintéticos). Separarlos necesita similitud semántica (embeddings, F2), no otro número. No volver a intentarlo con umbrales.
- **L26 — La ingesta cachea por hash del PDF, así que los cambios del CATÁLOGO no entran solos.** Cambiar `year`, `usage` o una marca nueva en `fuentes.yaml` no reprocesa nada: los 211 documentos salen como `unchanged` y el índice conserva los valores viejos. Habría dejado la marca de fuente de dosis sin efecto (y en la dirección insegura: sin ella el guard bloquea todo, pero un despiste al revés sí sería peligroso). → tras tocar el catálogo, `pedibot ingest --force`.
- **L27 — Una fuente vieja y para profesionales no suma por tener muchas páginas.** El manual de las 50 consultas (402 páginas, OCR hecho) es de **2008**, está escrito para el pediatra e incluye dosis de corticoides y antibióticos. Medido con el golden set: **nunca** es la primera fuente, solo aparece en el top-3 en 3 de 60 y ahí desplaza a hojas mejores (rompía g23), y **no llega ni a las preguntas de sus propios capítulos** (cojera, adenopatías) porque su lenguaje no es el de un padre. → excluido del índice, con el OCR guardado y la ficha en el catálogo para poder revertirlo. Y una regla que sí se queda: la excepción que permite dar una dosis se ata a una **fuente autorizada explícita** (`dose_source: true`, hoy solo la guía de dosificación de la AEPap), no a "parece una tabla de dosis" — cualquier libro profesional lo parecía.
- **L28 — El sitemap no falla solo: `robots.txt` daba 404 y Googlebot lo pidió 6 veces.** Search Console decía «No se ha podido obtener», que es fácil confundir con «dale tiempo». El registro del servidor lo aclaró en un minuto: Googlebot llevaba 24 h visitando el sitio (146 peticiones, 85 con código 200) y pedía `/robots.txt` una y otra vez sin encontrarlo. Tras crearlo, a las 07:05:43 UTC leyó `/sitemap-index.xml` con un 200 limpio. → **el registro de Caddy es la fuente de verdad, no el panel de Google**, que va con horas de retraso; y el `robots.txt` es parte del despliegue, no un detalle.
- **L29 — La misma revisión destapó tres fallos de escaparate que nadie ve desde el navegador.** (1) `og:image` apuntaba a `/og.png`, que no existía: **cada enlace compartido en WhatsApp o X salía sin miniatura** (generado con `scripts/make_og_image.py`, y de paso el `favicon.ico` que el navegador pide aunque haya SVG). (2) El `hreflang` traducía solo el prefijo del idioma, así que la guía inglesa declaraba su gemela española como `/es/guides/<slug-inglés>` — un 404; ahora cada guía busca su gemela por `topic` y, si no la hay, no declara nada. (3) Los textos para redes de las guías inglesas enlazaban `/en/guides/…`, que tampoco existe (el inglés vive en la raíz). Los tres se veían en los 404 del registro.
- **L30 — Dos claves de tema para el mismo asunto = contenido duplicado.** El plan de artículos lleva un nombre español y otro inglés para varios asuntos (`golpe_calor`/`heat`, `urticaria`/`hives`, `cefalea`/`headache_en`…) y en inglés se generaron **dos guías casi idénticas sobre el golpe de calor**, que se reparten la señal de SEO. → un tema no se ofrece si ya hay publicada otra guía en ese idioma que comparte la mayoría de sus fuentes ancla; los artículos comparativos (`compare_*`, que reutilizan fuentes a propósito) quedan exentos. La duplicada se retiró con un 301 hacia la que se queda, no con un 404.
- **L31 — Una tabla que no dice quién pregunta convierte nuestras pruebas en lectores.** El operador abrió `/admin` y preguntó si las consultas que veía eran mías. De las 106 filas de la base, **103 eran cadenas de prueba enviadas desde esta máquina** mientras se hacían los ocho idiomas: el panel, el repaso diario y el `/api/stats` público las contaban igual que a una madre preguntando por su hijo, porque la fila no guardaba nada que las distinguiera. → la respuesta guarda `source`; el chat manda `x-pedibot-client: web`, Telegram y el agente ACP se nombran solos, y **lo que no lo dice queda fuera de la cuenta** (`unknown`). El sentido del error es deliberado: esconder a alguien real de vez en cuando es preferible a inflar el único número con el que se decide si esto funciona. Dos consecuencias operativas: (a) **cualquier `curl` de prueba contra producción debe llevar `-H 'x-pedibot-client: test'`**; (b) el `AnswerRecord` no tiene valor por defecto en `source`, así que un endpoint nuevo que se olvide no compila. El dinero es la excepción y se cuenta entero — una pregunta de prueba cuesta lo mismo.
- **L32 — "Pidió /admin" no es lo mismo que "entró en /admin".** Para dejar de contar al propio operador como visitante se le identificó por el panel, que lleva contraseña. Medido en el diario real: **65 navegadores distintos han pedido `/admin` y 64 son escáneres** buscando un panel, a los que Caddy contesta 401. Tomar la petición como prueba habría borrado 64 direcciones de la cuenta de visitas — halagador, y falso justo en la dirección que el cambio existía para evitar. → hace falta un **200**. Con el filtro correcto son 4 navegadores y 54 páginas vistas suyas de 3.760.
- **L33 — El código de salida de una tubería es el del último comando, no el del primero.** Encadené `pytest -q | tail -2 && deploy` y desplegué dos veces con tests rotos: `tail` devuelve 0 siempre. Es la misma lección que MultiBot tiene como L98 (`merge | tail` enmascaró un ff-merge fallido), cometida **el mismo día** en el proyecto de al lado. → nunca canalizar un verificador cuyo resultado decide algo: `pytest -q > /tmp/t.txt 2>&1; echo "exit=$?"` y leer el fichero. Y la comprobación final del despliegue tenía el defecto simétrico: `sleep 3` y **un solo** `curl` contra un API recién reiniciado, que salía con 7 (no pudo conectar) y hacía parecer fallido un despliegue perfecto — ahora reintenta 20 s y solo entonces sale con 1 diciéndolo.
- **L34 — Un nombre es tan falsificable como un número, y el verificador solo miraba números.** El trabajo que redacta los tuits semanales comprueba que toda cifra esté en una hoja de datos medida. Aun así publicó *"288 published documents by 18 bodies including WHO, RKI, NHS, and **Ecuchi**"*: no existe ningún Ecuchi — en el corpus hay un *Ecimed* y el modelo cogió algo con esa forma. Todos los números eran correctos, así que no saltó nada. → la comprobación se extiende a los nombres: una palabra en mayúscula a mitad de frase que no esté en la hoja de datos no se envía, y un título entrecomillado tiene que existir. Corolario aprendido en la misma tanda: **cuidado con los guardias demasiado anchos** — «listed» entró en el filtro del token pensando en *listed on an exchange* y tiró un borrador bueno, porque los documentos de una guía van *listados* al pie (mismo error que L21). Y tres borradores de cuatro tandas afirmaron que **las respuestas** llevan numeración: la lleva la **guía**; la respuesta del chat nombra sus fuentes sin números, y pedírselo al prompt no bastó — hubo que comprobarlo.
- **L35 — Un examen que se aprueba siempre ha dejado de examinar.** El conjunto dorado iba al **100 % en las seis métricas, cero fallos sobre 111 casos**, y eso se leía como «el triaje está bien». Se escribieron 31 preguntas nuevas diciendo la misma urgencia **como la diría un padre asustado, no como la escribiría un manual**, y **veinte se colaron**. Ninguna por falta de regla: cada regla casaba solo con la redacción exacta con la que se escribió (`se le marcan las costillas` sí, `se le marcan MUCHO las costillas` no; `doesn't fade` sí, `does not fade` no; `manchas que no desaparecen` sí, `sarpullido que no desaparece` no; `blaue Lippen` sí, `die Lippen sind blau` no). Entre las que se colaban, las dos señales más graves de la pediatría: labios azules en inglés y alemán, y el sarpullido que no blanquea —la prueba del vaso, con la que se reconoce una sepsis meningocócica— en español y en inglés. → **la cobertura de una regla de seguridad no se mide con los ejemplos que la inspiraron.** Hay que escribir el caso con otras palabras, en cada idioma, y eso ahora es un candado (`tests/test_triage_holes.py`, 21 urgencias que deben saltar y 7 rutinas que no). Al ensanchar seis reglas se volvió a medir: precisión y recall de alarmas siguen en 1.0 — **una alarma que salta con unos mocos enseña a ignorarla, y entonces no salta cuando toca**.
- **L36 — La causa de un fallo de triaje puede no estar en el patrón, sino en lo que la regla EXIGE además.** La regla de fiebre en un lactante menor de 3 meses no es solo una expresión: lleva `requires: [age_under_3_months, fever]`. Los patrones disparaban y la regla seguía sin activarse, porque **«está calentita» no contaba como fiebre**: la lista de contexto solo aceptaba la palabra «fiebre» o un número de grados. Un padre con un bebé de seis semanas en brazos a las tres de la mañana, sin termómetro a mano, no escribe «presenta fiebre». → al depurar una regla que no salta, mirar **las tres piezas**: el patrón, el `requires`, y los detectores de contexto (edad, fiebre) de los que ese `requires` depende. Corolario de la misma sesión: la pila de botón estaba con las monedas en `foreign_body_ingestion` a nivel **urgente**; una pila alojada en el esófago quema en dos horas, así que pasó a regla propia en **emergencia**, y hubo que actualizar 7 expectativas del conjunto dorado y 2 tests que guardaban el nivel viejo — **una expectativa guardada también puede estar equivocada**.
- **L37 — El camino de fallo se degradaba en la dirección contraria: perdía lo único que no podía perder.** Cuando se alcanza el tope de gasto del día —o si el modelo está caído— el API contesta sin LLM, devolviendo los pasajes de las guías. Ese camino construía la respuesta con el nivel **escrito a mano**: `Answer(text, "routine", None, ...)`. Es decir, **quien preguntara por el sarpullido que no blanquea, los labios azules o una convulsión el día que se agotó el presupuesto recibía «rutina» y ninguna alarma**, y lo recibía *precisamente* el día en que el sistema está peor. No había ninguna razón técnica: el **triaje es determinista y gratis** — no llama al modelo, no cuesta un céntimo y funciona igual con el presupuesto a cero; lo que se pierde sin modelo es la redacción, no la clasificación. Nadie lo vio porque el único test del modo degradado comprobaba lo que el modo degradado *es* (`degraded is True`, hay fuentes), no lo que un fallo **no debe llevarse por delante**. → al escribir un camino de emergencia, la pregunta no es «¿qué devuelve?» sino **«¿qué deja de hacer, y podía permitírselo?»**; y cada pieza que sobreviva al fallo necesita su propio candado (`tests/test_degraded.py`). Corolario del mismo sitio: el aviso de presupuesto estaba en **dos idiomas de ocho** —inglés, y español para los otros seis—, así que un padre alemán recibía una frase en español; el camino raro es donde se esconden los idiomas sin traducir, porque nunca se mira.
- **L38 — Un límite implementado en un frente no es un límite.** Buscando más caminos de fallo apareció algo peor que un fallo: **el tope de gasto diario solo existía en el API**. `TelegramFront.handle_message` llamaba a `engine.ask` sin mirar el presupuesto, así que el freno que existe para que esto no cueste dinero tenía una puerta abierta al lado; por Telegram se seguía gastando con el tope alcanzado. Nadie lo vio porque el tope se probaba —y se pensaba— como «una regla del API», cuando en realidad es una regla **del producto**, y el producto tiene dos frentes. El mismo sitio tenía la variante de L37: un `except Exception` en la capa de transporte que contestaba *"Something went wrong on our side"* **en inglés fijo**, dijera el chat el idioma que dijera, tirando a la basura el triaje ya hecho. → una regla que protege dinero o seguridad **vive en el motor, no en el frente**, y los frentes la llaman: `Engine.answer_without_model()` la comparten hoy la web y Telegram. Y al escribir un candado para una regla así, escribirlo **una vez por frente**: el que probaba el tope en el API pasaba en verde mientras Telegram lo ignoraba por completo. **Y hubo un tercero, encontrado al aplicar la propia lección**: el endpoint del agente ACP tenía los dos agujeros, y su docstring decía literalmente *"same safety checks"* — el frente más fácil de olvidar es el que no usa una persona. Arreglarlos de uno en uno no sirve, porque el cuarto frente nacerá igual: el candado que queda es **estructural** (`tests/test_fronts.py`), lee el código con el AST y falla si aparece un `engine.ask` sin recoger `LLMUnavailable` o un frente que no mire el gasto del día. Comprobado rompiendo Telegram a propósito: lo caza. Corolario medido: el cliente de OpenAI espera **600 s y reintenta 2 veces** por defecto —hasta media hora de reloj girando para un padre asustado— cuando las respuestas reales tardan 3,2 s de mediana y la más lenta de la historia fue 8,3 s (n=108); un valor por defecto que nadie eligió es una decisión igual, solo que tomada por otro.
- **L39 — Una fuente puede caducar sin morir, y todo lo que teníamos buscaba muertes.** `sources_alive.py` comprueba que cada dirección del corpus responda, no redirija a una página de retirada y no acabe en otro tema. El calendario de vacunas de **Portugal pasaba las tres** —HTTP 200, sin redirección, misma página— y llevaba **desde octubre de 2025 derogado**: la Direção-Geral da Saúde lo había sustituido por el PNV 2025, que cambia el **MenC de los 12 meses por MenACWY** y el neumococo **Pn13 por Pn20**. Estuvimos publicando el calendario de vacunas equivocado de un país entero, y nada podía notarlo, porque **una dirección viva no dice nada sobre si su contenido sigue siendo el mismo**. → `superseded()` compara el año de la edición que citamos con los años que aparecen en la página, y el informe semanal lo pone **el primero**; dice «conviene mirar», no «está caducado», porque un año posterior en una página puede ser una edición nueva o una nota al pie, y esa decisión es de una persona con el documento delante. Tres cosas aprendidas al hacerlo: (a) **la cita tiene que llevar el año de la edición** —sin él no hay con qué comparar y el detector se salta ese país en silencio; el candado nuevo cazó a Brasil, cuya fuente es una página viva sin edición impresa, y ahí lo honesto es la **fecha de consulta**; (b) España también estaba desfasada (2025 con el 2026 ya aprobado el 12-dic-2025), pero al comparar el calendario infantil **no había ningún cambio**: lo que caducó fue la cita, no el contenido — y eso solo se sabe mirando, no deduciendo; (c) la tabla oficial es un **gráfico**, así que `pdftotext -layout` mezcla las columnas y una transcripción a ojo habría inventado dosis; se leyó con las **coordenadas** de cada palabra (PyMuPDF, que ya es dependencia) asignando cada celda a su columna por posición, y así apareció además una ausencia vieja: **faltaba la Td de los 10 años** de Portugal.
- **L40 — Un calendario de vacunas es de un país; el consejo sobre la fiebre no.** La fiebre se trata igual en Hamburgo que en Sevilla, así que usar una hoja española para responder en alemán es correcto (es la L20: el corpus es asimétrico y las mejores hojas para padres están en español). **Con las vacunas no vale**: el MenACWY va a los 12 meses en Portugal y a los 12-14 AÑOS en Alemania. Al revisar las ocho guías de vacunas, siete decían de qué país hablaban —«el Ministerio de Sanidad español», «en Espagne», «das spanische Gesundheitsministerium»— y **la árabe no**: decía «en el calendario recomendado para 2025», sin país, estando escrita entera desde el calendario español. Ese es el error que no avisa: el texto es verdadero, está bien citado, y aun así está mal, porque el lector lo toma por el suyo. → candado que exige que una guía de vacunas nombre el país de su fuente dominante. Y una lección sobre el propio candado: su primera versión buscaba solo el sustantivo («Spanien») y **acusó a la guía alemana, que sí lo dice en adjetivo** («spanische»). Un candado que no conoce el idioma en el que mira señala a quien no debe, y eso cuesta más caro que no tenerlo — se comprueba antes de creerle.
- **L41 — Contar la unidad equivocada no da un número falso: da una FOTO falsa.** El ensayo general del trabajo semanal de tuits —que nunca se había ejecutado desde que se programó— salió bien y produjo esta frase: *"The 288 source documents come from 18 bodies, including Ecimed, PUC Chile, the College of the Canyons and Santé publique France"*. Cada palabra es verdad y el verificador de L34 la aprobó con razón: los tres nombres están en el corpus. Y aun así es **la peor foto posible del proyecto**, porque el NHS, la OMS, los CDC y MedlinePlus se quedan fuera de la frase. La causa: la lista de organismos se ordenaba con `orgs.most_common(10)` contando **trozos del índice**, mientras la frase habla de **documentos**. Un manual de 400 páginas se parte en miles de pedazos, así que Ecimed (2.056 trozos, **un** documento) y el College of the Canyons (658 trozos, **un** documento) adelantaban al NHS entero (361 trozos, **56** documentos). Ordenado por documentos, la lista empieza por MedlinePlus (74), NHS (56), OMS (54), RKI (30), SEUP (29) y CDC (19). → **la unidad con la que se ordena una lista tiene que ser la misma que nombra la frase que la usa**; si la frase dice «documentos», ordenar por trozos es un error aunque ningún número esté mal. Y dos corolarios: (a) un verificador que comprueba que cada nombre existe no comprueba que la **elección** sea representativa — eso no se puede automatizar del todo, pero sí se puede arreglar la fuente de la que elige; (b) esto solo apareció porque se ensayó un trabajo programado que **nunca había corrido**, y la columna «última ejecución» de `systemctl list-timers` lo decía a gritos: un trabajo automático que no se ha visto funcionar todavía no funciona, solo está escrito.
- **L42 — Cinco preguntas de lectores reales, y dos estaban mal contestadas.** Todo lo que se prueba aquí lo escribimos nosotros. Al mirar por primera vez lo que ha preguntado **la gente**, en la base había cinco consultas reales (el resto son pruebas nuestras), y dos fallaban: (1) *«My 4-year-old has a fever of 38.8 °C»*, llegada por la web, y el motor **preguntó la edad**, que estaba en la pregunta; (2) *«Cuando dalsy le doy a mi hijo?»*, por Telegram, y respondió *«no tengo información fiable sobre esto en mis fuentes»* teniendo la web una página entera para el Dalsy. La primera es de seguridad: los patrones de edad separan el número de la unidad con `\s*` y **un guion no es un espacio**, así que *«My 2 month old has a fever»* daba **urgente** y *«My 2-month-old has a fever»* daba **rutina** — la forma más natural de escribirlo en inglés apagaba en silencio la regla de fiebre en un lactante de menos de tres meses (L36). Se arregla **normalizando los guiones antes de leer la edad**, en un solo sitio, no parcheando diez expresiones: así lo heredan los ocho idiomas y las edades escritas en letra («six-week-old»). La segunda era el clon podrido de siempre: las marcas viven en `drugs.yaml` para la calculadora y los sinónimos en `synonyms.yaml` para el buscador, dos listas de lo mismo escritas a mano — **de 44 nombres, 39 no estaban en la segunda**. Ahora se derivan del catálogo. → **el conjunto de pruebas más valioso que existe es el registro de lo que la gente preguntó de verdad**, y con cinco consultas ya dio dos fallos que ningún examen escrito por nosotros habría encontrado (L35 otra vez).
- **L43 — Un test que construye el objeto él mismo valida la pieza, no el montaje.** El arreglo de las marcas pasó en verde y **en producción seguía sin funcionar**: `Synonyms` había aprendido a leer el catálogo de fármacos, pero ninguno de los **seis** sitios que construyen el buscador se lo pasaba —api, telegram, tres de la CLI y el evaluador—, y la prueba no lo notaba porque se construía su propio `Synonyms` con los dos ficheros. Verde arriba, roto abajo. Lo encontré por casualidad, al comprobar si el script que hacía el cableado había llegado a ejecutarse: había abortado antes en un `assert` y **el arreglo no estaba conectado en ninguna parte**. → cuando se añade una dependencia a una pieza, el candado no va en la pieza sino en **quién la construye**, leyendo el código (`tests/test_real_questions.py`, AST, como el de `test_fronts.py`). Corolario del mismo día: un script de parcheo que aborta a medias deja el trabajo en un estado que parece hecho — hay que comprobar el resultado, no la intención (es la L33 vestida de otra manera).
- **L44 — Un límite se dimensiona por lo que se apoya en lo que limitas, no por lo que parece razonable.** Por la mañana le puse un tope al journal del VPS, que corría **sin ninguno** — bien hecho, es como en MultiBot llegó a 4 GB. Elegí **300 MB** sin mirar para qué se usa. Por la tarde, tirando de otro hilo, apareció que **el panel vive de ese journal**: las visitas, las páginas vistas y el tiempo de permanencia salen de `journalctl -u caddy`. Medido entonces: 13 días ocupan 215 MB, o sea ~16,5 MB al día, así que 300 MB dejaban al panel viendo **18 días** — y el panel ofrece vistas de 7, 30 y **90**. No habría mentido (siempre dice desde cuándo tiene registro), pero habría perdido el mes y el trimestre en silencio, y el operador se habría enterado mirando una gráfica más corta sin saber por qué. Subido a 2 GB / 120 días, que sigue siendo un límite: **lo que había que evitar era que no hubiera ninguno, no que fuera generoso**. → antes de acotar algo, preguntar quién come de ello; y si la respuesta es «una función del producto», el número sale de esa función, no del sentido común. Corolario del mismo hilo, y peor si hubiera pasado: si Caddy dejara de escribir en el journal, el panel enseñaría **cero visitas**, y cero visitas no parece una avería —parece que no vino nadie (L31 otra vez, el silencio que no se distingue de la ausencia). El vigilante lo comprueba ahora cada diez minutos; el suelo son 5 líneas en dos horas frente a las 403 medidas en un rato tranquilo, para que el aviso signifique «esto está mudo» y nunca «hoy hubo poca gente».
- **L45 — Una página que vive en dos direcciones no suma: reparte.** Search Console lo enseñaba a 90 días y nadie lo había mirado: `/dose` en el puesto 49,2 con 10 impresiones y `/dose/` en el 70,6 con 17; `/es/dose` en el 80,8 y `/es/dose/` en el 61,2. **Las 779 páginas respondían 200 con barra final y sin ella.** No venía de un descuido sino de `disable_canonical_uris`, que está en el Caddyfile por un buen motivo (Astro construye con `trailingSlash: 'never'` y sin él Caddy contestaba un 308 a cada dirección del sitemap): al desactivar la canonicalización, la forma con barra dejó de redirigir y pasó a servirse también. → **antes de elegir la dirección del arreglo, mirar cuál es la forma buena**: el sitemap no tenía ni una dirección con barra, y las canónicas y todos los enlaces internos usaban la forma sin barra, así que la barra redirige a esa con un 301. Fuera de la regla, y por motivos distintos: la raíz (no puede redirigir a la cadena vacía) y el API y el panel (**un 301 sobre un POST lo rompe** — el navegador reenvía como GET y el cuerpo se pierde). Y una lección sobre mí mismo del mismo rato: **me equivoqué dos veces al verificar y las dos veces lo dije antes de comprobarlo bien.** Primero «demostré» que la validación del Caddyfile fallaba siempre, y era falso: `caddy validate` elige el adaptador por el **nombre del fichero**, y yo lo había copiado a `/tmp/cf_test`. Después medí el código de salida con `| tail` y lo que medí fue el de `tail` — la L33 otra vez, en mi propia comprobación. Repetido en condiciones: bueno → 0, roto → 1 con el motivo. **Una medición que confirma lo que esperabas merece la misma desconfianza que una que lo contradice.**
- **L46 — Dos implementaciones del mismo cálculo: la aritmética coincidía, los datos no.** La dosis se calcula **dos veces** en este proyecto: el chat, el API y Telegram por `src/pedibot/bot/dose.py`, con las constantes escritas a mano en el código; y las páginas de la web por `web/site/src/dosepages.ts`, que las lee de `config/drugs.yaml`. Al compararlas por primera vez —ejecutando las dos, no leyendo el código— **la aritmética coincidía exactamente**: 0 desacuerdos en 216 comparaciones de mililitros, peso a peso y bote a bote, incluido el redondeo **hacia abajo** que las dos hacen a propósito y por la misma razón escrita en los dos ficheros. Lo que no coincidía eran las presentaciones: el chat conocía **tres** concentraciones de paracetamol y el catálogo **siete** (24, 30, 32, 40, 50, 100 y 200 mg/ml), y **dos** de ibuprofeno frente a tres. O sea: un padre con gotas de 200 mg/ml —la presentación brasileña, que está en el catálogo y tiene su página en la web— pregunta al chat y **no ve su bote**; si coge por error la línea de las de 100 mg/ml, se pasa al **doble**. → cuando el mismo número se calcula en dos sitios, el candado no puede ser leer los dos códigos y opinar que hacen lo mismo: hay que **ejecutar los dos y comparar los resultados** sobre todo el rango (`tests/test_two_calculators_agree.py`, comprobado rompiéndolo por los dos lados — quitando un bote y moviendo un tope). Y un corolario sobre las expectativas: la prueba que se rompió al arreglarlo decía `len(ml_by_form) == 2`, un número clavado a mano que no comprobaba nada de lo que importa; ahora comprueba que **están todas las del medicamento**, que es lo que un padre necesita — contar no es comprobar.
- **L47 — Un comprobador que no comprueba nada informa de que todo va bien.** Verificando en producción que la tabla de dosis publicada y la calculadora dicen lo mismo, mi script mintió **dos veces seguidas, y las dos en la dirección cómoda**. Primero buscaba las celdas con `<td>` y el peso va en un `<th scope="row">`: no casó ninguna fila, comparó **cero** pesos y aun así imprimió «la tabla publicada y la calculadora dicen exactamente lo mismo». Después, ya arreglado, asumía cuatro columnas — y las marcas con dos presentaciones (Dalsy: 2 % y 4 %) tienen cinco, así que leyó los mililitros de la segunda como si fueran las dosis máximas al día y «descubrió» que la web recomendaba **48 dosis diarias**. Las dos veces el fallo era del comprobador, no del producto, y las dos veces el resultado era creíble a primera vista: una porque confirmaba lo que yo esperaba, otra porque un número absurdo parecía un hallazgo gordo. → **un comprobador tiene que decir cuánto ha comprobado y negarse a dar veredicto si es poco** (`if comparadas < 30: raise SystemExit(2)`), y las columnas se localizan por su **cabecera**, no por su posición. Es la misma familia que la L33 y que los «candados del candado» repartidos por la suite, y merece la pena decirlo aparte porque me mordió **mientras arreglaba exactamente esta clase de fallo en otro sitio**. Con el comprobador ya honesto: siete marcas × 36 pesos × 1-2 presentaciones contra producción, en miligramos, mililitros y dosis máximas al día — **coincidencia completa**.
- **L48 — El número al que llamar es la cifra más consecuente del producto, y faltaba la del idioma con sesenta guías.** Todo lo demás de una respuesta se lee con calma; el número del banner de emergencia se marca con un niño en brazos. Al cruzar por primera vez los 31 países con número contra lo que el proyecto sirve de verdad, la cobertura era buena —los siete calendarios de vacunas, todos los países de las marcas de la calculadora, siete de los ocho idiomas— y faltaba exactamente uno: **India**, el país del hindi, en el que se publican sesenta guías. Un padre allí, con una alarma en pantalla, no veía ninguna cifra; y la frase por defecto en hindi era además **la única de las ocho sin ningún número**, mientras las otras siete llevan «112 en la UE, 911 en América». Verificado antes de escribirlo: 112 es el número único oficial (ERSS, Ministerio del Interior) y Tele-MANAS 14416 la línea nacional de salud mental del Ministerio de Sanidad; **el centro de intoxicaciones se dejó vacío porque no se pudo verificar en fuente oficial** — un número de urgencias inventado es peor que ninguno, y el banner sabe callar cuando no hay dato. → y tirando del hilo apareció lo de siempre: el desplegable con el que un padre elige su país era una **tercera** lista escrita a mano dentro de `Chat.astro`, con 29 de los 31. India acababa de entrar, pero **Perú llevaba así desde siempre**: su número puesto y ningún padre peruano capaz de elegirlo. Ahora se deriva del catálogo en el exportador. **Un dato que existe pero que el lector no puede seleccionar es un dato que no existe**, y esa mitad —la de la interfaz— es la que se olvida cuando se añade algo a la configuración.
- **L49 — El clon podrido tiene por fin un detector general, y solo cubría media casa.** La misma avería ha mordido cinco veces en este proyecto —el aviso de presupuesto en dos idiomas de ocho, el catálogo de fármacos sin portugués ni hindi, las marcas que el buscador no conocía, la lista de países del chat, las guías de vacunas— y siempre igual: se añade un idioma o un país y **una tabla no se entera, sin que nada falle**. Había un candado (`tests/test_i18n_parity.py`) y era bueno, pero cubría el i18n de la web y **dos** ficheros exportados; los YAML de `config/`, de donde sale todo lo demás, no los miraba nadie. Ahora el barrido recorre **todos** los ficheros de configuración con la misma regla —*un nodo que se traduce a sí mismo tiene que traducirse entero*— y se comprobó que habría cazado solo el hueco de esta misma mañana. **Cuando encuentres a mano un fallo de una familia que ya ha mordido antes, el trabajo no acaba en arreglarlo: acaba en el barrido que encuentra a los hermanos.** De 99 mapas por idioma revisados, los dos que parecían incompletos eran falsos positivos de mis propios scripts (una clave escrita en la misma línea que otra; y `synonyms.yaml`, cuyo nivel superior no es una traducción sino un **registro de tablas** — los cuatro idiomas «que faltaban» se resuelven con tablas cruzadas hacia el español y el inglés, que es donde está el corpus). Ese segundo se convirtió en la comprobación que sí aplica ahí: que los ocho idiomas tengan por dónde expandir una consulta.
- **L50 — Un indicador de foco que existe pero no se ve es peor que no tenerlo: parece que el problema está resuelto.** Midiendo el peso real de las páginas —35-43 KB por el cable, 7-9 peticiones, con `font-display: swap` en las 53 caras, todo correcto y sin nada que tocar— pasé a mirar el teclado, y ahí sí: la web tiene `:focus-visible { outline: 3px solid var(--mint-2) }`, que es más de lo que hace la mayoría de sitios, pero el color nunca se eligió mirando el contraste. **1,06:1 de día y 1,29:1 de noche** en el peor de los nueve fondos, cuando WCAG 2.2 pide **3:1** para el indicador de foco (2.4.11 y 2.4.13). Quien navega con el teclado —porque no puede usar el ratón, o porque lleva un bebé en el otro brazo— no sabía dónde estaba. El candado de contraste que ya existía comprobaba once pares de **texto** sobre fondo y no miraba esto, porque el foco no es texto: su umbral es 3:1, no 4.5, y hay que comprobarlo contra **todos** los fondos, no contra uno — basta con que falle sobre la tarjeta menta para que alguien se pierda justo ahí. → cambiado a un token propio `--focus` (el verde de la marca: 5,1:1 de día, 7,01:1 de noche) y comprobado sobre los nueve fondos en los dos temas. Corolario de método, que es lo que me llevo: **una medición que sale bien no cierra el área, la reencuadra**. El peso estaba perfecto, y seguir mirando en la misma dirección —qué vive un padre en un móvil de madrugada— llevó al fallo real, que no era de bytes.
- **L51 — La lección se aplicó a un alfabeto y no al otro.** Norma nueva del operador (7-sep-2026): *«siempre mira las preguntas para hacer mejoras»*. Aplicada a las 128 consultas de la base, 12 estaban sin responder bien; once eran correctas al revisarlas una a una (cinco `asked_age` donde el padre **no** había dicho la edad, dos `clarify` genuinamente ambiguas, un correo comercial, una francesa ya arreglada) y la doceava era el Dalsy, arreglado esa mañana. Pero probar el detector de preguntas de vacunas **en los ocho idiomas** —que es lo que la norma empuja a hacer— destapó lo que ninguna consulta real había tocado todavía: **en árabe no llegaba**. Las raíces árabes vivían dentro de un grupo `\b(...)\b` y `\b` se define sobre `\w`; en «اللقاحات» la raíz لقاح lleva el artículo ال delante y el plural ات detrás, ambos caracteres de palabra, así que **la frontera no existe** y el patrón no casa nunca. Lo revelador: **en el mismo fichero, el devanagari ya estaba fuera del grupo por esta misma razón**. Alguien aprendió la lección para el hindi y no la llevó al árabe — el clon podrido, esta vez entre escrituras. → al arreglar algo específico de una escritura no latina, **repasar todas**; y anclar la causa, no solo los casos (el candado comprueba que ni el árabe ni el devanagari vuelvan dentro del grupo, porque si vuelven ningún ejemplo suelto explicaría por qué). Corolario: sacar una raíz del grupo la vuelve una subcadena, y eso puede pescar de más — «حبوب اللقاح» es el **polen**, así que una pregunta por la alergia habría acabado en el calendario de vacunación; la guarda son dos lookbehind encadenados, porque `re` exige anchura fija en cada uno y «حبوب » y «حبوب ال» no la comparten.
- **L52 — Tres de los ocho idiomas no llegaban nunca a la calculadora de dosis.** La jugada que acababa de funcionar con las vacunas —probar el enrutador **en los ocho idiomas**, no esperar a que llegue una consulta— aplicada al de dosis, que es la herramienta determinista insignia: da los mililitros exactos de una tabla publicada, sin modelo y sin coste. Los cinco idiomas latinos funcionaban; **ruso, árabe e hindi devolvían `None` siempre**. Cuatro causas encadenadas, y cada una bastaba sola: (1) los kilos —el patrón conocía «kg» y sus variantes latinas, ni кг ni كيلو ni किलो—; (2) las cifras —un teclado árabe escribe ١٢ y uno hindi १२—; (3) las palabras —el respaldo que busca la marca usaba `[^\W\d_]`, apoyado en `\w`, y **las vocales del devanagari son marcas combinantes, no alfanuméricas**, así que «पैरासिटामोल» se rompía en trozos de una letra y no quedaba ningún token; se arregla partiendo por espacios y puntuación, que es agnóstico a la escritura—; y (4) el catálogo —`resolve()` comparaba con el genérico en **inglés y español**, dos de los ocho que la ficha guarda, y además exigía coincidencia exacta cuando **el ruso declina** («сколько парацетамол**а**»)—. → dos reglas que se repiten y conviene tener juntas: **`\w` y `\b` no sirven fuera del alfabeto latino** (el proyecto ya lo sabía para `\b`; `\w` es el mismo problema con otra cara), y **cuando una función acepta un idioma, probarla en los ocho el mismo día** — las tres averías llevaban meses y ninguna consulta real las había tocado todavía, así que esperar a que apareciera una habría sido esperar a que un padre ruso se quedara sin su mililitro.
- **L53 — Las reglas nuevas no heredaron el trabajo de idiomas que las viejas ya tenían.** Enumerados los cinco enrutadores deterministas y probados los ocho idiomas en cada uno, `detect_lang` y la lectura del país salieron limpios (los ocho alfabetos, y «Portugal» se escribe igual en cinco lenguas, así que cuatro formas bastan). El triaje no. Medida la cobertura por **alfabeto** de las 32 reglas de alarma —una regla sin un solo patrón en devanagari **no puede saltar jamás** para un padre que escriba en hindi, y eso se sabe sin probar ni un caso—: 29 cubrían cirílico, árabe y devanagari, y las tres que no eran **las tres últimas que se añadieron**. `headache_warning_signs` (urgente) solo tenía los cuatro idiomas latinos; `eating_disorder_signs` no tenía hindi; y `neuro_deficit`, que es de **emergencia**, no tenía ni francés ni hindi: quien escribiera «le bras ne bouge plus» o «हाथ नहीं हिला रहा» no recibía ninguna alarma. Y el fichero de candados que la L35 dejó —21 urgencias reescritas como las diría un padre asustado— **no tenía ni una línea en cirílico, árabe o devanagari**: se midió la cobertura en los idiomas latinos y se dio por medida la del resto. → el candado que queda no es una lista de casos sino **estructural**: toda regla tiene que tener patrones en las tres escrituras no latinas, comprobado sobre el propio fichero de reglas. Comprobado además que caza el estado de esta mañana (10 pruebas caen con las reglas de antes) y que las 32 siguen sin ensancharse: el conjunto dorado se mantiene en 1.0 y un resfriado sigue siendo un resfriado en los cinco idiomas probados. Corolario menor del mismo repaso: un patrón ruso llevaba `(магazин)?`, medio cirílico y medio latino — una palabra rota en algún copiado, inofensiva por estar en un grupo opcional y sin significado alguno.
- **L54 — Un guardia solo falla del lado seguro si primero VE lo que vigila.** Terminados los enrutadores, tocaba lo que de verdad protege: `looks_like_medication_dose`, el guardia de la L21, que rechaza una respuesta con miligramos —o con mililitros que el contexto no explique como líquido— si entre las fuentes no hay una tabla de dosis autorizada. Está escrito para fallar del lado seguro («un 5 ml sin explicar cuenta como dosis»), y esa propiedad **es inútil si la cifra ni se detecta**: el patrón era `\b\d+([.,]\d+)?\s*(mg|ml)\b`, o sea latino. Medido: «дайте 250 мг парацетамола», «أعطه 250 ملغ» y «250 मिग्रा पैरासिटामोल» devolvían **False** — el único guardia contra una dosis inventada no miraba en tres de los ocho idiomas. Y las palabras de contexto (las de medicamento y las de líquido) también eran solo latinas, así que aunque la cifra hubiera casado, el contexto tampoco. → al ensanchar el guardia hubo que ensanchar **las dos** listas a la vez: sin las palabras de líquido en cirílico, árabe y devanagari, los volúmenes de suero oral de las hojas del SEUP habrían empezado a contarse como dosis y el ruso habría perdido las respuestas de gastroenteritis — arreglar la mitad de un guardia lo rompe por el otro lado. Corolario del mismo repaso: el detector de fiebre no conocía «жар», que es como se dice en ruso corriente, y de él depende la regla de fiebre en un lactante de menos de tres meses (L36). **La regla general de estas tres lecciones seguidas: cada vez que algo se escribe con una expresión regular, preguntar en qué alfabetos está escrita esa expresión** — el proyecto habla ocho idiomas en tres escrituras, y todo lo que se probó a mano se probó en la latina.
- **L55 — El barrido que cierra la familia, y tres rondas de falsos positivos míos para escribirlo.** Aplicada la regla de la L54 a todo el código: 55 expresiones regulares con letras, **39 solo latinas**. Casi todas con razón —rutas, HTML, agentes de usuario, limpieza de PDF en español—, pero tres leían el texto de un padre. La gorda: `_TOKEN`, el tokenizador que construye los términos de búsqueda, era `[\wáéíóúñü]+`, y `\w` son los caracteres **alfanuméricos**, mientras las vocales del devanagari (las matras) son marcas combinantes. «बुखार» (fiebre) salía como «ब»+«ख»+«र», y con el filtro de tres caracteres que viene después **una consulta en hindi producía cero términos de búsqueda**. Lo honesto es medir el daño y no exagerarlo: el hindi encontraba igualmente los pasajes correctos, porque las tablas cruzadas de sinónimos traducen la consulta al español y al inglés — pero eso significaba que **toda** la búsqueda en hindi colgaba de 176 entradas escritas a mano, mientras que en ruso o árabe la palabra cruda al menos entra en la consulta. Las otras dos: el impulso a las preguntas de dosis, y **una segunda copia** del barrido de palabras latino que arreglé por la mañana en `dose_intent` (el gemelo decidía si ofrecer el enlace a la calculadora). → el candado que queda es un barrido con AST, y su unidad es **el detector con nombre, no la expresión suelta**: los patrones de edad en devanagari son entradas *aparte* dentro de `_AGE_PATTERNS`, con su motivo escrito, así que mirarlas una a una daría por incompleto un diseño que está bien. Y lo que no se puede automatizar se **declara** con su motivo, con dos reglas que hacen que la declaración no sea una excusa: una declaración que ya no apunta a ningún detector falla (cazó una mía a los diez minutos de escribirla), y **toda exención lleva su prueba de comportamiento** — `_TOKEN` está exento del barrido de caracteres y tiene, aparte, una prueba de que parte bien una palabra hindi. Corolario incómodo y por eso anotado: escribir este barrido costó **tres rondas de falsos positivos míos** (una regex por línea en vez de por detector; cadenas SQL tomadas por patrones; una exención caducada), y el patrón se repite todo el día — **un detector nuevo miente antes de acertar, así que la primera lista que produce se mira una a una, no se cree**.
- **L56 — Veintiocho patrones escritos con cuidado en ocho lenguas, y ni uno solo podía saltar.** La regla del lactante con fiebre —la 5 de CLAUDE.md, la más importante que hay— tiene dos caminos hacia la alarma: `requires: [age_under_3_months, fever]`, que exige **leer una edad**, y sus patrones, que reconocen **la palabra**. `assess()` hacía `continue` en cuanto una regla traía `requires`, así que el segundo camino no se recorría nunca. Lo que se colaba era justo lo que el `requires` no sabe leer: «mi lactante tiene fiebre», «Säugling hat Fieber», «у младенца температура», «رضيعي عنده حرارة» — cinco de las ocho lenguas, en rutina. Y el candado estructural que exige patrones en los tres alfabetos (L47 otra vez) los contaba tan contento: **comprobaba que estuvieran escritos, no que sirvieran**. → cuando una regla tenga dos maneras de dispararse, probar **las dos por separado**; un patrón que nunca se evalúa se lee exactamente igual que uno que funciona. El candado nuevo no mira frases: exige que los patrones de toda regla con `requires` casen con la frase que los motivó. Corolario del mismo cambio: al encender la ruta de patrones apareció el reverso —«10 दिन का बुखार» son *diez días de fiebre* y «10 दिन का बच्चा» un *bebé de diez días*, la misma construcción para las dos cosas— y un niño de cinco años con fiebre larga recibía el aviso del lactante con ese motivo escrito en el banner. Una alarma con el motivo equivocado enseña a desconfiar de todas.
- **L57 — El aviso decía «no dar» y debajo venían los mililitros.** La calculadora marcaba `refer` para un bebé de dos meses y a renglón seguido escribía 50 mg de ibuprofeno y la tabla bote a bote — de un fármaco que su propia ficha del catálogo excluye por debajo de tres meses y de cinco kilos. En la web era peor: los 50 mg en tipografía grande arriba del todo y el aviso **debajo** de la tabla, redactado además con los identificadores internos del código («under_3_months_refer, below_min_age») en los ocho idiomas, teniendo las ocho traducciones ya escritas a dos ficheros de distancia. A las tres de la madrugada se leen los números, no el renglón de al lado. → decisión del operador (8-sep-2026): cuando el fármaco no es para ese niño, **no se dice cuánto**; se dice qué es, por qué no, y de dónde sale la norma. Y la regla general: un aviso que no cambia lo que se enseña no es un aviso, es una nota al pie.
- **L58 — Las palabras que ponemos nosotros se traducen; las que pone el fabricante, no.** La lista de botes salía en castellano en los ocho idiomas —«jarabe 120 mg/5 ml», «gotas 100 mg/ml»— en la herramienta determinista insignia y en la única línea de una respuesta que es una instrucción. El comprobador de fugas de idioma no la veía y no era culpa suya: mira las páginas construidas, y esa lista la pinta el navegador con lo que responde el API. → la línea que separa las dos cosas es de quién es la palabra: «jarabe» y «gotas» las escribimos nosotros y se traducen; «infant», «six plus» o «baby drops» es lo que pone en la caja que el padre tiene en la mano, y traducirlo le quitaría la forma de encontrar su bote en la lista. Corolario: dos fugas más del mismo día vivían fuera de Astro, que es donde no llega ningún candado — la página de `/a/{token}` estaba escrita `"…" if lang != "es" else "…"` (seis idiomas con envoltorio inglés) y sin dirección de escritura, así que una respuesta árabe compartida se maquetaba al revés.
- **L59 — El juez de fidelidad, ejecutado por fin, y el sistema está construido para suspenderlo.** Primera medición real desde que existe la métrica (8-sep-2026, 99 respuestas juzgadas): **fidelidad 0,788** — 17 infieles y 4 con reparos. Y no están repartidos: **17 de los 21 son alarmas** (11 emergencia, 5 urgente, 1 salud mental), o sea el 31 % de las respuestas con alarma frente al 12 % de las de rutina. El patrón es siempre el mismo: la respuesta escribe **nuestra** orden de urgencia —«llame ahora», «hay que verlo hoy», «tumbe al niño de lado»— y le cuelga una cita de un pasaje que no dice eso. La causa no es el modelo portándose mal: es una contradicción escrita en nuestras propias reglas. La 2 exige cita en toda afirmación clínica y la 3 exige nombrar al organismo en la primera frase, con el verificador tirando la respuesta si falta cualquiera de las dos; la 10 dice que si ninguna fuente lo respalda se escriba **sin cita**. Las tres no pueden cumplirse a la vez, y el modelo resuelve el empate por donde no le echan la respuesta atrás: inventando la atribución. Mitigarlo con `_inject_rule_sources` (25-ago) redujo el problema y no lo cerró, porque el trozo inyectado enumera signos de alarma y no contiene la orden. → esto no se arregla retocando el prompt a ojo: hay que decidir **de quién es** la orden de urgencia —del banner, que es nuestro y no necesita fuente, o del cuerpo, y entonces marcada como propia— y volver a medir. Ya hay línea base, que es lo que faltaba desde el 26-ago.
- **L60 — El examinador tampoco examinaba el producto.** `eval._engine()` construía el motor **sin `drugs`, sin `vaccines` y sin `guides`**: tres de los cinco enrutadores deterministas fuera. El de vacunas no podía dispararse nunca durante una evaluación. Y el conjunto dorado no tenía **ni un solo caso** que esperase `vaccine_schedule`, así que el `routing: 1.0` que llevábamos semanas leyendo se calculaba sobre diez casos de 111 con esa ruta entera fuera del examen — por eso una pregunta de vacunas en francés aparecía en la evaluación con modelo como una respuesta imposible de fundamentar, cuando en producción la contesta una tabla. Es la L47 aplicada al propio examinador, y la variante más incómoda: no es que el candado no comprobara nada, es que comprobaba **otro programa**. → cuando haya más de una forma de construir el objeto que se evalúa, que el evaluador use la de producción; y en cuanto se añade una ruta al producto, un caso que la espere. Al hacerlo saltó a la primera un fallo real: «in the UK» y «in the US» no se leían como país —estaban «united kingdom» y «england», no «UK»— en el mercado primero del producto.
- **L61 — Arreglé la contradicción del prompt, la medí, y salió peor. Se queda el resultado negativo.** La L59 dejaba el diagnóstico: las reglas 2 y 3 (cita y organismo obligatorios, con el verificador tirando la respuesta) contradicen la 10 (sin cita si nada lo respalda), y el modelo resolvía inventando la atribución. Escribí `answer_v5` haciendo la excepción explícita —«la orden de urgencia es NUESTRA: sin marcador y sin organismo»— más una regla nueva contra endurecer lo que la fuente dice. Sobre los **mismos 99 casos juzgados**: fidelidad **0,788 → 0,747**, validez de citas 0,990 → 0,971, regeneradas 12 → 17. Ocho respuestas empeoraron y cuatro mejoraron — y las cuatro que mejoraron (g35, g48, g87, g90) son justo las que motivaron el cambio, o sea que la regla nueva **hace lo que se le pidió** y aun así el conjunto sale peor: autorizar una frase clínica sin marcador aflojó el hábito de citar en todas las demás. → dos cosas. Una, el problema no se arregla dándole al modelo permiso para no citar; hay que **sacar la orden de urgencia del cuerpo** (ya vive en el banner, que es nuestro y no necesita fuente) o darle una fuente que de verdad la contenga, y las dos son decisiones de producto. Y dos, la más útil: **una regla que hace exactamente lo que se le pidió puede empeorar el conjunto**, porque un prompt no es una lista de reglas independientes sino un tono, y aflojar una afloja las de al lado. Por eso se mide antes de desplegar y por eso el fichero descartado se queda en el repositorio con su tabla: volver a averiguarlo cuesta 0,07 $ y media hora.
- **L62 — La prueba que encontró los cuatro últimos fallos no fue un test: fue mandar la misma pregunta ocho veces.** Después de desplegar, la misma pregunta corriente —«mi hija de 3 años tiene 38,5 de fiebre»— contra producción en los ocho idiomas. Siete contestaron y **el alemán preguntó la edad**, que estaba escrita en la frase: es la única de las ocho lenguas que pega el número a la unidad («3-jährige», «2-monatiges»), y con eso se caía también la regla del lactante en su redacción más normal. Repetida la jugada en local con seis situaciones × ocho idiomas (48 combinaciones, gratis con proveedor falso), aparecieron tres más, y en el peor sitio: **costarle respirar no era emergencia en alemán, portugués ni hindi** — en portugués porque el patrón exigía la palabra «grave», que en castellano es opcional. → el barrido «una situación × todos los idiomas» ha encontrado hoy fallos que 1.400 tests no veían, y cuesta un fichero de treinta líneas. Los tests comprueban lo que ya sabemos que existe; el barrido compara las lenguas **entre sí**, y las averías de este proyecto viven casi siempre en la diferencia.
- **L63 — El hindi conjuga por género y solo estaba escrito el masculino: una hija que dice que quiere morir no disparaba la regla.** `मरना चाहता` (un hijo) saltaba y `मरना चाहती` (una hija) no, en `suicidal_ideation`, que es la regla que enseña el teléfono 024. Lo mismo en `जीना नहीं चाहता`. No es un idioma «a medias»: es un idioma donde **la mitad de los pacientes** —las niñas— quedaba fuera de la regla más delicada del producto, y ninguna de las comprobaciones lo veía porque todas preguntan «¿hay patrones en devanagari?» y los había. → cuando una lengua marque género, persona o número en el verbo, escribir **las dos formas**; y al revisar una lengua que no se domina, probar la frase con un sujeto femenino y con uno masculino. Es una pregunta de treinta segundos que aquí valía la mitad de los casos.
- **L64 — Veinte agujeros, y todos eran la misma frase dicha de otra manera.** Barrido de doce situaciones × ocho idiomas. Ninguno por falta de regla: las 32 estaban escritas y cada lengua había recibido una red más estrecha que el original. Las familias, porque se repiten: **el verbo frente al sustantivo** (la anafilaxia tenía «labios hinchados» y no «se le están hinchando los labios», que es como se cuenta lo que está pasando ahora mismo — faltaba en cinco lenguas); **la palabra que falta en la lista** (la lejía, la intoxicación doméstica más común, solo nombrada en castellano, inglés y francés); **el orden de la frase** (el alemán pone el producto delante del verbo, «Bleichmittel getrunken», y el patrón esperaba lo contrario); **el cualificador obligatorio** (portugués exigía «dificuldade *grave*» donde el castellano lo tiene opcional); y **la unidad de tiempo** («lleva doce horas sin mojar el pañal» no casaba en ninguna de las ocho, teniendo todas el pañal seco como sustantivo). → traducir una regla no es traducir sus palabras: es volver a preguntarse cómo se cuenta eso en esa lengua. Y el barrido que lo encuentra cuesta un fichero de treinta líneas y cero euros.
- **L65 — La lección se aplicó a la lectura de la edad y no a las reglas, que es la otra mitad de la misma casa.** El 7-sep se normalizaron los guiones en `parse_age_months` con un comentario que explicaba por qué se hacía en un solo sitio: «no en cada expresión, así lo heredan los ocho idiomas». Las reglas de `red_flags.yaml` se evaluaban sobre el texto crudo, así que «my 5 days old refuses to feed» daba urgente y «my 5-day-old refuses to feed» daba rutina — la misma regla y la misma frase. → cuando se arregle algo «en un sitio para que lo hereden todos», preguntar **cuántos sitios leen lo que escribe el padre**. Aquí eran dos y se tocó uno.
- **L66 — Una regla puede implementar dos de los cinco signos de su propia fuente.** `headache_warning_signs` cita la hoja de la cefalea del SEUP, cuyo trozo marcado como alarma lista cinco motivos de consulta urgente; la regla tenía patrones para dos. El primero de la lista —«fiebre alta, dolor de cabeza intenso y vomita varias veces», que es la meningitis contada como la cuenta un padre— no tenía ningún patrón, en ningún idioma. Y la rigidez de nuca, que sí tiene hoja propia de MedlinePlus en el corpus («get medical care right away»), no estaba en ninguna de las 32 reglas. → revisar cada regla **contra el texto de su `source`, bullet por bullet**: el fichero de reglas se lee entero y parece completo, y la comprobación que falta es la que compara con el documento del que salió.
- **L67 — El falso positivo que enseña más que los diecinueve fallos del mismo barrido.** «She has a rash that **fades** when I press it» daba **emergencia**. Es el resultado tranquilizador de la prueba del vaso: el padre ha hecho exactamente lo que la hoja del SEUP le pide, ha comprobado que la mancha desaparece, y lo cuenta. El patrón era `(rash|spots).{0,50}(press|glass|tumbler)` — sarpullido más la palabra «apretar», sin ninguna negación — mientras que los otros dos patrones de la regla sí exigían el «no desaparece». Ese es el detalle: **la regla estaba bien escrita dos veces y mal la tercera**, y la mala se llevaba por delante a las buenas, porque a la alarma le basta con que dispare un patrón. → al añadir un patrón «por si acaso» a una regla que ya funciona, mirar si el nuevo es más ancho que los que había: en una alarma, el más ancho manda sobre todos los demás. Y buscar siempre el caso en que el padre cuenta el resultado BUENO de una comprobación, porque está redactado con las mismas palabras que el malo.
- **L68 — Dos formas nuevas de la red estrecha: el orden de la frase y el participio.** En `blood_in_stool`, el castellano y el inglés tenían escritos los **dos** órdenes («heces … sangre» y «sangre … en las heces») y las otras cinco lenguas heredaron uno solo, así que «il y a du sang dans ses selles», «er hat Blut im Stuhl», «кровь в стуле», «يوجد دم في البراز» y «tem sangue nas fezes» —o sea, la forma natural en las cinco— no saltaban. Y en `head_injury_loss_consciousness` el patrón castellano pedía «perdió el conocimiento» y un padre escribe «**ha perdido** el conocimiento»: un golpe en la cabeza con pérdida de conciencia se quedaba en rutina **en el idioma de las fuentes**, que es donde uno menos lo busca. → al traducir una regla, escribir la frase en los dos órdenes y en los dos tiempos, porque el que falte es justo el que va a escribir alguien. Corolario medido el mismo día: `eating_disorder_signs` tenía seis patrones en castellano, cinco en inglés y **uno** en francés, alemán, árabe y portugués — contar los patrones por idioma dentro de cada regla habría señalado eso en un segundo.
- **L69 — Presencia no es cobertura, y contar patrones por escritura encuentra en un segundo lo que el barrido a mano tarda una hora en destapar.** El candado que había preguntaba «¿esta regla tiene al menos un patrón en devanagari?». Con eso pasaban `eating_disorder_signs` con **un** patrón en ruso frente a veintiséis latinos, y `neuro_deficit` —que es **emergencia**— con treinta latinos y **dos** en cirílico y dos en árabe: catorce signos distintos en las lenguas latinas (boca torcida, pérdida de fuerza, habla arrastrada, visión doble de repente, marcha inestable, desorientación) y dos en ruso. La medida justa es el latino **dividido entre cinco**, que son las lenguas que comparten ese alfabeto, comparado con lo que tiene cada una de las otras tres. Señaló cuatro reglas y las cuatro tenían agujeros de verdad: 39 fallos de 96 combinaciones probadas. → un candado que comprueba **presencia** se aprueba solo; uno que comprueba **proporción** sigue examinando. Y la medida barata dirige el trabajo caro: el barrido a mano vale para confirmar y para lo corriente, no para buscar.
- **L70 — El segundo falso positivo del día, y el más caro de todos porque estaba en castellano.** «Está aprendiendo a andar y se cae mucho, ¿es normal?» daba **emergencia**: el patrón de `neuro_deficit` aceptaba «anda … se cae». Es la pregunta más corriente que existe entre los doce y los dieciocho meses. La lección, que es la misma que la del sarpullido que sí se va al apretar pero por el otro lado: **un signo neurológico de la marcha es un CAMBIO** —antes andaba bien y ahora no—, no un estado. Un patrón que describe un estado normal del desarrollo dispara con el desarrollo normal. Ahora se exige inestabilidad («se tambalea») o que sea de repente. Corolario doble del mismo lote, y las dos mías: «mole» (portugués, *flojito*) casaba dentro de «**MOLE**sta» en castellano, porque puse la frontera de palabra delante del paréntesis y no por alternativa; y un patrón nuevo con un guion dentro («acordá-lo») no casaba con nada, porque en esta misma sesión hice que `assess` convierta los guiones en espacios antes de mirar. **Un arreglo de hoy es una regla nueva para el resto del día.**
- **L71 — Un error de comillas en un fichero de datos estaba devolviendo un 500 en producción, en inglés y en una de las preguntas más naturales que existen.** `emergency: [urgencias, 112]`. Sin comillas, el cargador de YAML lee `112` como **entero**, el motor hace `" ".join(términos)` para clasificar el tema, y salta un TypeError que sube hasta el API: «when should I take my child to the emergency department?» → *Internal Server Error*. En el idioma principal del producto. No lo encontró ningún test, y no podían: los 1.800 que había ejercitaban el motor con ficheros de prueba o con preguntas que no llevaban esa palabra. Lo encontró **medir la cobertura de sinónimos por idioma** —un trabajo que iba de otra cosa— y tropezar con el tipo del dato. → dos candados, porque el dato y el código fallan por separado: que el fichero no tenga números sueltos, y que aunque los tuviera, el motor siga respondiendo. Y la regla general: **un fichero de datos es código**, y el suyo no lo comprueba nadie salvo que se le pida.
- **L72 — Doce disparadores del buscador que no podían casar nunca, y entre ellos el recién nacido en dos idiomas.** Un disparador con guion dentro —«nouveau-né», «recém-nascido», «pronto-socorro», «magen-darm»— no cuenta como frase (no lleva espacio), así que se busca por prefijo contra los tokens… y el tokenizador parte justo por el guion. La tercera aparición del mismo guion en un día: se arregló en la lectura de la edad, luego en las reglas del triaje, y aquí estaba el **tercer** sitio que lee lo que escribe el padre. Ahora `expand` importa el conversor del triaje en vez de copiarlo. → cuando la respuesta a «¿cuántos sitios leen lo que escribe el padre?» sea «dos», contar otra vez.
- **L73 — El francés era la única de las ocho lenguas sin tabla hacia el castellano, y el corpus está en castellano.** Medido: una pregunta francesa sobre fiebre y vómitos recuperaba documentos ingleses sobre norovirus y **cero** fuentes españolas; las otras cinco lenguas no latinas llegaban a las hojas del SEUP. El francés fue el primer idioma nuevo (fase francesa, 2-sep) y se construyó antes de que existiera el patrón `X_es`/`X_en` que heredaron los demás. La tabla no se escribió a mano: la lista española se **copió** de las tablas que ya existían, buscando cada concepto por su lista de términos ingleses; lo único aportado fue el disparador francés, comprobado contra las 60 guías francesas del sitio —si la palabra no aparece en lo que publicamos en francés, no es la que usa un lector francés— y el término español contra el índice. De 56 fragmentos y 0 españoles a 68 y 17, con cinco preguntas ganando fuente y ninguna perdiéndola. → cuando se añade una lengua, la pregunta no es «¿tiene sus textos?» sino «¿tiene todo lo que tienen las demás?», y la lista de lo que tienen las demás se puede sacar del propio fichero.
- **L74 — La puerta del «fuente o silencio» contaba «tos» dentro de «esTOS».** El filtro de relevancia miraba si el término estaba en el texto con `t in texto`, o sea por subcadena. Medido sobre los 6.548 fragmentos: «tos» aparecía en **2.558** por subcadena y en **259** por palabra —diez veces más—; «pis» en 359 frente a 29; «asma» dentro de «plasma» y de «espasmo». Y esa cuenta no es un adorno: es la puerta que decide si hay fuente o se calla, y estaba abierta de par en par justo para los síntomas que más se preguntan en castellano. → cuando una comprobación mira si una palabra «está» en un texto, preguntarse **está cómo**; en un buscador multilingüe la subcadena es casi siempre el error, y se ve midiendo, no leyendo el código.
- **L75 — Lo que sobra estorba más que lo que falta.** Al arreglar lo anterior salieron dos primos hermanos. Uno: la lista de palabras vacías estaba escrita en castellano y algo de inglés, así que la misma pregunta daba **un** término en castellano y **doce** en alemán —mein, kind, hat, fieber, und, ich, weiß, nicht…—, y esos términos entran en la consulta FTS: una pregunta alemana sobre fiebre casaba con las fichas del RKI que contienen «ich» y «und» (poliomielitis, estreptococo) por delante de las hojas de la fiebre. El otro, en la detección de idioma: « que » y « para » se escriben igual en castellano, francés y portugués y contaban como marcador **del castellano**, así que le regalaban un punto en cada pregunta de las otras dos y ganaba los empates. Medido: el portugués se detectaba bien **3 veces de 10** —escrito sin acentos, que es como se teclea en un móvil— y «Qu'est-ce que la rougeole ?» se contestaba en castellano. → **un marcador que no separa no es un marcador**, y una lista de palabras vacías escrita en una lengua es una lista de ruido en las otras siete. De 15 fallos de 81 a cero.
- **L76 — La taxonomía no conocía ninguna enfermedad exantemática, y el índice sí.** Sarampión, varicela, escarlatina, rubéola y paperas devolvían `None` como tema, y sin tema la puerta del «fuente o silencio» pasa de exigir un término a exigir tres: «Qu'est-ce que la rougeole ?» se quedaba sin ninguna fuente. Lo llamativo es que **el corpus ya tenía esos documentos clasificados como `piel`** — el lado del documento sabía lo que el lado de la pregunta ignoraba. → cuando dos partes del sistema clasifican lo mismo, comprobar que coinciden; y la lista de lo que le falta a una se saca de la otra, sin inventar nada.
- **L77 — Repetí la medición sin cambiar nada y salió 0,663 donde antes 0,788. Todo lo que había decidido con ese número estaba mal fundado.** La fidelidad del conjunto dorado se mide con un juez que lee lo que el modelo redacta, y el modelo **redacta distinto cada vez**: entre dos tiradas del mismo caso el parecido medio del texto es **0,48**, y 26 de 99 casos cambian de veredicto sin tocar una línea. El ruido del método es **0,125**, y las diferencias que yo había interpretado eran de 0,041 (v5) y 0,010 (v6): las dos cabían enteras dentro del azar. → **antes de usar una medición como puerta, medirla dos veces sin cambiar nada.** Es una tirada más, cuesta lo mismo que la primera, y sin ese dato cada decisión de prompt es una moneda al aire con aspecto de método. Corolario que no esperaba: bajar la temperatura a 0 **no** lo arregla —el parecido sube solo a 0,68 y 2 de 20 salen idénticas—, porque la no-determinación es del proveedor, no del parámetro.
- **L78 — Con el ruido medido, se ve cuáles de las métricas sirven, y no es la que da nombre al informe.** El mismo par de tiradas de v4 da amplitud **0,125** en fidelidad, **0,035** en regeneradas y **0,009** en validez de citas. O sea que la fidelidad —la métrica que se mira— no distingue nada por debajo de un octavo, mientras que las otras dos sí distinguen. Por eso v6 se adopta y no por lo que se escribió para arreglar: su fidelidad es indistinguible de la de v4, pero deja las citas en 1,000 (frente a 0,990 y 0,981) y las regeneraciones en 3 de 99 (frente a 12 y 8), las dos **fuera** del ruido. → una métrica ruidosa al lado de dos estables no sirve para decidir, y hay que decidir con las estables aunque no sean las que uno quería mirar.
- **L79 — Un falso positivo en un guardia de seguridad no cuesta seguridad: cuesta la respuesta entera.** Auditando las 483 guías publicadas contra las reglas clínicas del propio proyecto, dos saltaron como si dieran una dosis: «2.6 مليون وفاة» (2,6 **millones** de muertes) y «2–3 из 100 младенцев» (2-3 de cada 100 **lactantes**). En las dos, la unidad —«مل», «мл»— vivía dentro de otra palabra. La tercera vez en el mismo día que aparece esta familia, después de «tos» dentro de «estos» y «mole» dentro de «molesta». Lo que la hace distinta es la consecuencia: `looks_like_medication_dose` es un guardia que **falla del lado seguro**, así que cuando se equivoca no da una dosis mala — manda la respuesta a regenerar y de ahí al «no tengo información fiable». Estaba costando respuestas en ruso y en árabe cada vez que un texto citaba una cifra grande, que en pediatría es justo la que da la magnitud del problema. → «falla del lado seguro» no quiere decir «puede fallar tranquilamente»: quiere decir que el precio se paga en otra moneda, y a esa moneda también hay que ponerle un número. Y el sitio donde mirar son los **datos publicados**, no los tests: el guardia llevaba semanas equivocándose sobre dos textos que estaban en el repositorio, a la vista.
- **L80 — El vigilante miraba nuestra infraestructura y nunca la única pregunta que importa.** El watchdog comprobaba el proceso, el saldo, el disco, las unidades de systemd y el journal: cinco cosas, todas nuestras. Ninguna era «¿funciona una consulta?». Por eso el 500 en inglés de esta mañana pudo durar quién sabe cuánto con `/api/health` en verde — el proceso estaba perfectamente en pie, que es lo que el health dice y lo único que decía. → un vigilante tiene que ejercitar **el camino del usuario**, no el estado del servidor; y se puede hacer gratis si se desconecta lo que cuesta (aquí, el modelo: la expansión, la taxonomía y el índice se recorren sin gastar un céntimo, así que cabe en la vuelta de cada diez minutos). Corolario, y es el que le da valor: la comprobación se probó **rompiendo cosas a propósito** —índice ausente, configuración que no carga, una lengua sin puente al corpus— porque un vigilante que nunca ha detectado nada y un vigilante roto se leen exactamente igual.
- **L81 — Las reglas con consecuencias legales también se rompen en silencio.** «Un documento `excluido` no entra en el índice del bot público» está escrito en CLAUDE.md desde el primer día, y no había nada que lo comprobara: el catálogo declara la licencia, el índice guarda **su propia copia** del dato, y si las dos se separaban ganaba la del índice sin que nadie lo viera. Está bien —3 excluidos, 0 dentro, 0 huérfanos, 0 discrepancias, y ninguna de las 483 guías reproduce una frase literal de un `citar_solo`— pero eso se sabe desde hoy. → el patrón del clon podrido no distingue entre un dato técnico y uno legal, y la comprobación cuesta lo mismo en los dos casos.
- **L82 — Un padre no escribe una pregunta: escribe cinco, y reparte la información entre ellas.** Todos los barridos del día probaban un solo mensaje. Al probar conversaciones de dos turnos —que es como se cuenta algo de verdad: primero lo que se ve, después lo que se ha comprobado— se cayeron tres de seis combinaciones, y la peor es la del meningococo: «le han salido unas manchas rojas» → «no desaparecen cuando aprieto». Eso es exactamente lo que escribe quien acaba de hacer la prueba del vaso, la regla estaba escrita y saltaba con las dos frases juntas… y el filtro entre turnos la tiraba. El filtro existe por una buena razón —repetir un aviso ya dado enseña a ignorarlo— pero preguntaba «¿está en el último mensaje?» cuando la pregunta correcta es «**¿lo ha traído el último mensaje?**»: una regla que ya saltaba con lo anterior no vuelve a avisar, y una que salta al juntarlo todo y antes no saltaba es información nueva. → cuando un componente filtra por «lo nuevo», comprobar qué pasa con lo que **solo existe al combinar**; y probar el producto como se usa, que en un chat son varios turnos y no uno.
- **L83 — Ensanchar una ventana obliga a estrechar lo que hay dentro.** El tercer caso —«le duele la barriga» → «ahora más en el lado derecho»— no lo arreglaba el filtro: entre dos mensajes hay más texto que dentro de uno, y la ventana del patrón de la apendicitis era de 40 caracteres. Al ensancharla a 90 apareció el efecto colateral inmediato: «le duele la barriga y se ha dado un golpe en el brazo derecho» pasaba a dar la alarma, porque la lista aceptaba «derecho» a secas. Las dos cosas van juntas: **más distancia entre las piezas exige piezas más específicas**. Se cambió el adjetivo suelto por la expresión que de verdad localiza («lado derecho», «parte derecha»), y el brazo, el oído y el tobillo derechos volvieron a la rutina.
- **L84 — La distancia entre las dos mitades de una regla es una dimensión de prueba, y no la habíamos usado.** Probar la conversación en castellano destapó tres huecos; probarla en las ocho lenguas destapó **seis más**, y ninguno de familia nueva —orden invertido, verbo en vez de sustantivo, una palabra intercalada, una flexión que falta—. Lo que los saca a la luz no es el idioma: es que **cuando las dos mitades vienen en mensajes distintos, la frase se dice entera**. En un solo mensaje un padre escribe telegráfico («manchas que no desaparecen»); repartido en dos, escribe con verbo, posesivo y adjetivo («le han salido unas manchas rojas en la tripa» … «no desaparecen cuando aprieto»). Los patrones estaban escritos para lo primero. Tres de los seis eran la prueba del vaso —el signo del meningococo— en alemán, ruso y portugués. → probar cada regla **también con sus piezas separadas y la frase completa**, que es como se habla; y recordar que el barrido de un idioma no sustituye al de los ocho ni al revés: aquí hicieron falta los dos, uno detrás del otro.
- **L85 — Cuando falta un dato que cambia el número, el reparto por defecto no puede ser el del grupo mayor.** El suero de rehidratación acepta la edad como opcional, y sin ella caía en la rama del niño de más de un año: «unos 200 ml por cada deposición diarreica», dicho a alguien que no ha contado la edad y podría tener un bebé de dos meses. Peor todavía: sin edad tampoco se enseñaba el aviso de los menores de dos años, así que el grupo más vulnerable perdía **la cantidad correcta y la advertencia a la vez**, y las dos por el mismo `if`. Es el mismo defecto que la calculadora de dosis tenía esta semana con otra cara —allí se daba la cifra de un fármaco que no era para ese niño, aquí la cantidad de una edad que no era la suya— y en los dos casos el código no mentía: elegía por el padre sin decírselo. → la salida correcta cuando falta el dato no es adivinar ni callarse, sino **repartir de forma que el error no pueda ir hacia el más frágil**: aquí, dar las dos indicaciones, que se nombran solas y las coge quien sabe la edad. Y buscar este patrón allí donde un parámetro sea `Optional` y decida una cifra.
- **L86 — La L85 se cumplió sola en dos días, en otro fichero.** La lección de ayer terminaba diciendo «buscar este patrón allí donde un parámetro sea `Optional` y decida una cifra». Al hacerlo, el primer sitio donde se miró fue la propia calculadora de dosis: `if age_months is not None and age_months < drug.min_age_months` — con la edad ausente **la comprobación sencillamente no se hace**, así que el ibuprofeno a 5 kg devolvía la dosis entera y sin un solo aviso. Cinco kilos es un peso de lactante y el ibuprofeno no se da por debajo de tres meses. Y no es un caso rebuscado: el desplegable de la web tiene una opción que dice literalmente **«no lo sé»**. → el patrón a buscar tiene nombre y forma: `if x is not None and <condición peligrosa>`. Esa guarda convierte «no lo sé» en «no pasa nada», que son cosas distintas, y lo hace en silencio y sin que el código mienta en ninguna línea. La otra mitad de la lección es de proporción: el paracetamol no tiene edad mínima y ahí exigirla habría roto el caso corriente sin ganar nada, así que la regla se aplica **solo donde hay una contraindicación que descartar**.
- **L87 — El barrido del patrón, completo: diecinueve guardas, dos con consecuencia.** Buscar `if x is not None and <peligro>` en todo el código dio diecinueve sitios. Diecisiete eran inofensivos y dos no: el suero se había quedado **un escalón por debajo** del arreglo de la misma mañana —sin edad daba las franjas del lactante y del niño mayor, pero no la del menor de un mes, que es la única que dice que a esa edad no se dan sueros— y el informe semanal, si no conseguía leer el saldo, no escribía nada, ni la cifra ni el aviso, de modo que un informe con la consulta rota se lee igual que uno normal (L31). → dos cosas. Una: **cuando se arregla un caso de «falta el dato», mirar el escalón de abajo**, porque los rangos suelen tener tres tramos y es fácil tapar los dos de arriba. Y dos: el barrido de un patrón concreto es barato —un `grep` y media hora de leer— y encontró en un rato lo que un día entero de barridos por idioma no había tocado, porque miraba otra dimensión.
- **L88 — Pedíamos hacer la prueba del meningococo y no escuchábamos la respuesta.** La lectura de fotos ve unas manchas, se queda en «urgente» —correctamente: una imagen no puede saber si la mancha desaparece al apretar— y le pide al padre que haga la prueba del vaso. Pero `/api/photo` guardaba la respuesta en la base y **nunca llamaba a `add_turn`**, así que la foto no existía en la conversación: cuando el padre contestaba «no desaparecen cuando aprieto», ese mensaje llegaba solo, y solo es rutina. El producto pedía una comprobación y luego era incapaz de recibirla. → cuando una respuesta **pide algo al usuario**, comprobar el turno siguiente: la pregunta y la respuesta son una sola cosa y viven en dos peticiones distintas. Y de paso: dos caminos que hacen lo mismo (aquí `/api/ask` y `/api/photo`) tienden a separarse en lo que no se ve — uno registraba turnos y el otro no, y llevaban así desde que existen.
- **L89 — La sospecha equivocada llevó al fallo bueno.** Empecé comparando el nivel que da el mismo signo por texto y por foto, convencido de haber encontrado una incoherencia: «manchas que no desaparecen» escrito da **emergencia** y una foto con petequias da **urgente**. No era un fallo. La diferencia es deliberada y está bien pensada: el texto es un hecho que el padre ya ha comprobado, y la foto es una sospecha que **todavía hay que comprobar**, así que pide la prueba en vez de dar la alarma. Al leer esa respuesta con atención —«haz la prueba del vaso»— apareció la pregunta que sí valía: ¿y qué pasa cuando la hace? → una hipótesis descartada no es tiempo perdido si al descartarla se lee de verdad lo que hace el código; el fallo estaba a una frase de distancia de donde yo miraba.
- **L90 — Nadie había pulsado los botones que ofrecemos nosotros.** Cuando la primera pregunta es vaga, el bot enseña siete opciones para que el padre concrete. De las 56 combinaciones de opción × idioma, **once acababan en «no tengo información fiable sobre esto»** — lo peor que se puede contestar a quien acaba de pulsar exactamente lo que le ofreciste. Y por dos causas distintas, que conviene separar: «Golpe o caída» fallaba en ruso, árabe y portugués porque las tablas de sinónimos tenían el **verbo** («упал», «سقط», «caiu») y el botón dice el **sustantivo** («Падение», «سقوط», «queda») — la familia de la L64, aparecida ahora en los sinónimos en vez de en el triaje. Y «Otra cosa» fallaba en los ocho, pero eso no era vocabulario: es una **meta-opción**, el botón que dice «nada de lo de arriba», y buscarla en el corpus no puede devolver nada; lo que toca es preguntar. → probar **la salida del producto como entrada**: los botones, las opciones y las sugerencias que uno mismo ofrece son texto que alguien va a mandar, y nadie los prueba porque no parecen preguntas de usuario. Aquí eran 56 y ninguna se había probado nunca.
- **L91 — El texto que vive en la función del transporte no se parece a un texto de producto, y por eso nadie lo revisa.** Al traducir `/stop` y `/country` miré `handle_command`, que es donde están los textos «del bot». Tres se habían quedado dentro de `run_polling` —el acuse del 👍, el «no encontrado» y, el que duele, el mensaje de avería: «Something went wrong on our side. **If this is urgent, call your local emergency number**»— en inglés y solo en inglés, dicho a quien había puesto `/lang de`. La frase que manda llamar a urgencias, en un idioma que el padre puede no leer, y precisamente en el momento en que el resto del sistema ha fallado. → cuando se audite el idioma de un producto, la lista de sitios no es «los ficheros de textos»: es **todo lo que sale hacia el usuario**, incluidas las funciones de transporte, los `except` y los acuses de recibo. Los mensajes de error son los que más se escapan porque se escriben una vez, deprisa, y no se vuelven a leer nunca.
- **L92 — Tres fallos distintos con la misma frase, y un ternario con las dos ramas iguales.** El chat contestaba «algo ha fallado por nuestra parte» a los tres casos: la avería, el límite de peticiones (429) y el «ahora no puedo» (503). Y las tres cosas le piden algo distinto al padre — nada, esperar unos minutos, volver luego. Decirle «hemos fallado» cuando lo que pasa es que ha preguntado mucho lo deja **reintentando**, que es exactamente lo que alarga el bloqueo que se le acaba de poner. En la rama de la foto había además `r.status === 503 ? S.err_server : S.err_server`: alguien quiso distinguir el 503, escribió el ternario y no llegó a escribir la otra rama. Un ternario con las dos ramas iguales es una intención a medias que compila, pasa los tests y no se ve al leer por encima. → **los mensajes de error también son producto**: merecen tantos estados como situaciones distintas haya, y la pregunta que los ordena es «¿qué tiene que hacer ahora quien lo lee?». Si dos mensajes contestan lo mismo a esa pregunta, sobra uno; si uno solo contesta a tres situaciones, faltan dos.
- **L93 — «Menor de 3 meses» no es «3 meses», y la frase con la que la regla está escrita no la disparaba.** La lista de urgencias del SEUP enuncia el signo así: «Bebé menor de 3 meses con fiebre (≥ 38 °C)». Escrita tal cual daba **rutina**: el lector de edades veía el cualificador, lo tiraba, se quedaba con el 3, y la regla se dispara con `< 3` — fallaba por un pelo. Y no es una redacción de manual: es como lo dice un padre que no quiere dar la edad exacta («mi bebé tiene menos de tres meses»). Un cualificador **invierte** el número al que acompaña, y un lector que extrae cifras y descarta lo que las rodea no puede verlo. → cuando un número decide algo, mirar **lo que hay pegado a él**: «menos de», «más de», «casi», «unos». Y el hindi lo pospone («3 महीने से कम»), así que hay que mirar a los dos lados; eso no lo vi yo, lo cazó el candado que exige cubrir las cuatro escrituras — un candado bien puesto encuentra cosas que su autor no sabía que buscaba.
- **L94 — Dos listas que dicen lo mismo, escritas por separado, y nadie las había puesto una al lado de la otra.** `er_checklist.yaml` son 34 signos con su nivel, que salen tal cual en la web; `red_flags.yaml` son las reglas que deciden lo mismo en el chat. Cruzarlas dio cuatro huecos, y ninguno se habría visto mirando cada fichero por su cuenta, porque los dos están bien escritos: el fallo está **en el hueco entre los dos**. Salió, además, la sobredosis de paracetamol —que no estaba en la lista de productos del envenenamiento en seis de las ocho lenguas, siendo el fármaco que hay en todas las casas— y la herida que necesita puntos, que no tenía regla ninguna. → buscar en el proyecto los pares de ficheros que **codifican la misma decisión para dos superficies distintas** y compararlos; si difieren, una de las dos está mal y el usuario no tiene forma de saber cuál.
- **L95 — La línea base que faltaba, y lo que enseña sobre qué se puede medir y qué no.** Tres tiradas de la evaluación con juez sobre `answer_v6`: fidelidad **0,767 con un rango de 0,736 a 0,792**. Ése es el número contra el que comparar cualquier cambio de prompt de aquí en adelante, y explica de una vez por qué `answer_v5` se descartó mal: su 0,747 cae **dentro** de ese rango. Pero el mismo experimento enseña la otra mitad, que no esperaba: hay métricas de esa misma tirada que **sí** distinguen, porque su rango no se solapa con el de v4 — la validez de las citas (1,000 en las tres tiradas de v6 frente a 0,981-0,990 en v4) y las regeneraciones (0,057-0,075 frente a 0,085-0,120). O sea que la medición no es «ruidosa» en bloque: **cada métrica tiene su propio ruido**, y hay que medirlo antes de usar ninguna como puerta. Tratar el informe entero como fiable, o como no fiable, es equivocarse de las dos maneras a la vez. → antes de decidir con un número, medir **su** rango repitiendo sin cambiar nada; con dos o tres tiradas basta para saber si puede distinguir lo que se le va a pedir que distinga.
- **L96 — La coma no cortaba la negación, y una negación que iba con otra cosa apagaba el signo de alarma.** Cruzando las 483 guías con el triaje aparecieron dos frases que salían **rutina** y no debían: «Symptome, die es vorher **nicht** hatte, wie **Atemprobleme**» y «температура, которая **не** проходит, или **судороги**». El `nicht` negaba «hatte» y el `не` negaba «проходит», pero la ventana de negación los arrastraba dieciocho caracteres más allá, cruzando una coma, hasta apagar lo que venía después. Un punto ya cortaba el efecto y un «pero» también; una coma no, y una coma cierra oración igual que un punto en las ocho lenguas. Lo que impide pasarse de frenada al arreglarlo es la **enumeración negada** —«no tiene fiebre, tos ni dificultad para respirar»— donde una sola negación se reparte entre varios elementos y la coma no cierra nada: se reconoce porque detrás de la coma va una conjunción. Sin esa salvedad, el padre que dice que su hijo está bien recibe una alarma roja, que es justo lo que la negación se añadió para evitar. → una ventana de contexto **necesita saber dónde termina la oración**, y la lista de lo que la termina es más larga que el punto; el precio de que sea corta se paga en falsos silencios, que es la moneda cara.
- **L97 — Arreglé la forma que el informe me enseñó primero, y la misma forma faltaba en otras seis lenguas.** El cruce entre las guías y el triaje destapó 21 temas donde la misma advertencia era urgencia en una lengua y rutina en otra. Al ir cerrándolos añadí «respira cada vez peor» en castellano —el empeoramiento progresivo, que es lo que separa la urgencia de la emergencia— y seguí adelante. La prueba nueva, que relee las advertencias del fichero publicado, devolvió acto seguido «Respirar cada vez pior» en portugués, «Дыхание становится хуже» en ruso, «Respire de plus en plus mal» en francés y «يتنفس بشكل أسوأ» en árabe. Ninguna era una familia nueva: era **la misma**, y yo había arreglado la que tenía delante. → cuando falte una forma, la pregunta no es cómo arreglarla: es **en qué otras lenguas falta la misma**, y responderla antes de tocar nada cuesta un barrido y ahorra la tanda siguiente. Corolario del método: la prueba tiene que leer el texto **publicado**, nunca uno tecleado en el propio test — así una transcripción equivocada mía sale como fallo y no como aprobado falso, que es como se cazó el nukta de «तकलीफ़» por tercera vez.
- **L98 — Ensanchar un patrón sube cosas de nivel, y eso no lo caza ninguna prueba de «esto se ve».** Al abrir los patrones del color azul y de la respiración, 92 de las 2.576 advertencias de las guías cambiaron de nivel: 92 subieron y ninguna bajó. Leerlas una a una —que es la comprobación entera— sacó tres que se habían pasado: «blassere Haut als normal» (piel más pálida) llegaba a emergencia, «des bleus» en francés son **moratones** y no labios azules, y «respiración más rápida de lo normal» subía de urgente a emergencia, con lo que se quedaba sin escalón el niño que de verdad empeora. Las tres las metí yo en el mismo lote en que arreglaba lo otro, y las tres pasaban el conjunto dorado y las 2.404 pruebas. → después de ensanchar un patrón, **mirar qué se ha movido y hacia dónde**, no solo si lo que faltaba ya se ve; la lista de movimientos es corta, se lee en diez minutos y es el único sitio donde el sobre-triaje aparece. Y en un sistema con niveles, subir de más rompe algo concreto: si el estado normal ya da la alarma máxima, no queda nada que decir cuando llega la de verdad.
- **L99 — La prueba del vaso era ciega en alemán, y llevaba así desde que existe.** Ensanchar el cruce entre las guías y el triaje a los once signos de alarma —hasta entonces sólo se había barrido la respiración— dio esto en la primera pantalla: de las siete advertencias alemanas que describen la prueba del vaso, **las siete** salían rutina. `petechiae_fever` tenía doce patrones alemanes y ninguno llevaba **verblassen**, que es el verbo con el que lo dicen el NHS, el RKI y las siete guías del proyecto; los doce decían «verschwinden» o «weg gehen». Lo mismo en francés («s'estomper») y en hindi («गायब» frente a «मिट», con la negación en «न» y no en «नहीं»). Y la explicación de por qué no se había visto en ningún barrido anterior es incómoda: **los barridos probaban la frase que yo escribía**, y yo escribía «gehen nicht weg», que funcionaba. Es la regla de la sepsis meningocócica, el caso con menos margen de tiempo de todo el sistema. → cuando se barre una regla, las frases tienen que venir de **la fuente y del corpus publicado**, no de la cabeza de quien escribió los patrones: el autor prueba con las palabras que ya tiene en la cabeza, que son justo las que puso. Y el indicador que lo delató no fue un fallo suelto: fue un **7 de 7** en una lengua y 0 de 7 en las otras, que sólo se ve contando por idioma.
- **L100 — Un signo entero sin regla, y el barrido ancho lo enseñó como una fila plana.** «No puede tragar o babea mucho» salía rutina en las ocho lenguas: 5 o 6 advertencias por idioma, todas ciegas. Cuando el cruce falla en **una** lengua es una forma que falta; cuando falla en las ocho a la vez, es que no hay regla. Son dos cuadros de poco margen —la epiglotitis, donde la saliva cae porque no se puede tragar, y la anafilaxia, cuya regla tenía la hinchazón de labios y lengua en las ocho lenguas pero «se cierra la garganta» sólo en dos—. → la tabla de ciegos **por lengua y por signo** distingue dos averías que se parecen en el síntoma y no en la causa, y sólo la fila entera contesta «esto no está implementado». Corolario sobre el diseño de la regla nueva: «le cuesta tragar» a secas es una amigdalitis y hay guías del propio corpus que la nombran como cosa corriente, así que el no poder tragar dispara solo y la dificultad exige ir con la saliva — la mitad de la prueba que dice qué **no** debe alarmar es la que decide si la regla se puede tener.
- **L101 — La misma idea tiene tres órdenes, y arreglar uno no arregla los otros dos.** La anafilaxia no veía la hinchazón de la boca: su lista de partes del cuerpo era labios, lengua, párpados, cara y garganta, y **«boca» no estaba en ninguna de las ocho lenguas**. Pero la avería tenía tres capas, y salieron de una en una, cada vez que creía haber terminado: «los labios se hinchan» (las partes delante del verbo), «hinchazón dentro de la boca» (el sustantivo con preposición, y el patrón pedía «hinchazón DE») y «hinchazón súbita de los labios» (el sustantivo con una palabra en medio, y el patrón las quería pegadas). Los tres salen en guías distintas **de la misma lengua**, así que no es una diferencia de idioma: es que una idea clínica se escribe de tres maneras y los patrones se escribieron mirando una. → cuando una regla nombra una parte del cuerpo y un cambio de estado, hay al menos tres construcciones —sujeto+verbo, sustantivo+preposición, sustantivo+modificador+partes— y hay que escribir las tres o comprobar que una sola las cubre. La comprobación de que se ha terminado no es que la frase que uno probó pase: es que el barrido contra el corpus deje de devolver formas nuevas.
- **L102 — El barrido ancho encontró una regla que no existía y que ninguna lista nuestra pedía.** La mastoiditis —hinchazón o enrojecimiento detrás de la oreja, o la oreja desplazada hacia delante— sale en las guías de otitis de las ocho lenguas y el triaje la leía como rutina. No estaba en `er_checklist.yaml`, ni en el conjunto dorado, ni en ninguna lista de reglas pendientes: **lo único que la reveló fue cruzar contra el contenido publicado**, que se generó desde fuentes que sabían más que nuestras listas. Es la segunda regla que aparece así en dos días, después de la herida que necesita puntos. → el corpus no es sólo lo que el bot cita: es un inventario de signos clínicos escrito por las fuentes, y compararlo con las reglas encuentra lo que falta sin que nadie tenga que acordarse. Y como toda regla nueva, se sostiene por la mitad que dice qué **no** avisa: un dolor de oído a secas es lo más corriente que hay, y ahí la oreja desplazada hacia delante es lo que separa la complicación del catarro.
- **L103 — Teníamos dos reglas para el golpe en la cabeza y nos faltaba la tercera, que es la que rompe el hueso.** `head_injury_loss_consciousness` y `vomiting_after_head_injury` estaban desde el principio. **Sangre o líquido claro por la nariz o los oídos** —el signo de la fractura de base de cráneo— no tenía patrón en ninguna de las ocho lenguas, y sale en las guías de traumatismo craneal de las ocho. Es el mismo hallazgo que la mastoiditis y que la herida que necesita puntos: tres reglas ausentes en dos días, las tres reveladas por el corpus y ninguna por nuestras listas. → cuando un tema tiene **varias reglas**, esa es justamente la señal de que hay que enumerar los signos del tema en la fuente y tacharlos uno a uno: dos reglas escritas dan la sensación de que el tema está cubierto, y es la sensación la que impide mirar. La forma barata de enumerar es el corpus, que ya está escrito desde las fuentes.
- **L104 — El proyecto cazó dos de mis errores él solo, y son los dos candados que más caro costaron.** Al añadir la regla de la fractura de base de cráneo, `test_rule_density.py` la rechazó: catorce patrones latinos y **uno** en árabe. Y el barrido de las ocho lenguas destapó que el ruso pone el complemento delante —«Из носа или ушей выходит кровь»— cuando yo había escrito la sangre primero. Ninguna de las dos cosas la habría visto yo releyendo: las dos las encontró una comprobación escrita hace días para otra ocasión. → los candados que se escriben después de una avería siguen trabajando sobre **código que aún no existe**, y ése es su rendimiento de verdad: no evitar que vuelva el fallo de entonces, sino cazar el de dentro de una semana, escrito por alguien —yo— que ya se sabía la lección y aun así lo repitió.
- **L105 — Las reglas están escritas con verbos y las fuentes escriben nombres. En las ocho lenguas.** Empezó pareciendo un problema del árabe: el barrido lo dejaba muy por detrás de las demás en el signo del sangrado. Lo primero que apareció fue un error mío en la herramienta de análisis —buscaba «دم» por subcadena, y «دم» vive dentro de «عدم» (ausencia de) y «مقدم» (proveedor), que es la L74 repetida por mí tres días después de escribirla—. Debajo estaba lo bueno: el árabe forma estos avisos con «عدم» + nombre verbal, y todos los patrones árabes eran verbales. Al probar la misma construcción en las otras siete lenguas, **26 de 27 ciegos**: «ausencia de respuesta», «incapacidad para tragar», «Bewusstlosigkeit», «отсутствие реакции», «lack of response». No era el árabe: era que todas las reglas se escribieron pensando en un padre que habla («no responde») y no en una hoja clínica que nombra, que es de donde el padre copia cuando busca en Google y pega lo que ha leído. → cuando una lengua salga mucho peor que las otras en un barrido, **mirar qué tiene de particular esa lengua y probar esa particularidad en las demás**: aquí la construcción nominal era visible en árabe porque es obligatoria, y estaba igual de ausente en las siete donde es opcional.
- **L106 — Escribir los patrones con escapes los hace funcionar y los vuelve irrevisables, y el candado lo vio antes que yo.** Escribí la regla de la frialdad con `\uXXXX` para no pelearme con la consola de Windows. Casa perfectamente —el módulo `re` entiende esos escapes— y mis pruebas pasaban. Pero `test_rule_density.py` la rechazó: en el YAML no hay ni una letra cirílica, árabe ni devanagari, porque lo que hay escrito son letras latinas. Tenía razón, y por un motivo que no era el suyo: al reescribirla con caracteres de verdad se vio que **se me había colado una «н» cirílica dentro de «तापमान»**, que es devanagari, y ese patrón no habría casado nunca. → un fichero de configuración clínica lo tiene que poder leer **quien sepa la lengua y no sepa programar**; los escapes lo sacan de sus manos y esconden justo los errores que esa persona vería al primer vistazo. Candado nuevo, de una línea: en `red_flags.yaml` no puede haber un `\u`.
- **L107 — Un signo verdadero en el sitio equivocado hace más daño que un signo ausente.** Metí «manos y pies muy fríos» en `mottled_skin`, que es emergencia, y la comprobación de falsos positivos devolvió ocho de golpe: «va descalzo por casa», «siempre tiene las manos frías», «cold hands in winter». El signo era correcto —la frialdad periférica es ámbar en el semáforo del NICE— y el sitio no: cuenta **con fiebre**, no sola. Un niño descalzo tiene los pies fríos, y esa frase la escribe muchísima más gente que la otra. → antes de colocar un signo en una regla existente, preguntar **con qué frecuencia se dice esa frase sin el cuadro clínico**; si la respuesta es «constantemente», el signo necesita regla propia con las dos mitades dentro del patrón. Y el `requires` del proyecto no sirve para eso: en `assess` es una ruta alternativa, no un Y lógico — lo comprobé poniéndolo y viendo saltar la regla igual.
- **L108 — El tiempo verbal: la regla tenía el pasado y el sustantivo, y no el presente.** «Pierde el conocimiento» salía **rutina en castellano y en inglés**, teniendo el participio («ha perdido el conocimiento») y el sustantivo francés («perte de connaissance»). Cinco ciegos de seis. Y lo interesante es dónde encaja: el proyecto ya había pagado 0,022 de precisión por meter el desmayo en `not_responding`, porque un niño que se desmayó y se recuperó no es un niño que no responde. El presente es justo el caso que la regla sí quiere —está pasando ahora— y el pasado es el que no. La distinción que costó dinero **es la que dice qué tiempo verbal añadir**. → cuando una regla depende de que algo esté ocurriendo, enumerar sus tiempos verbales explícitamente y decidir uno a uno; y si alguna vez se retiró una forma por falsos positivos, releer por qué, porque suele señalar exactamente qué forma sí falta.
- **L109 — Añadí el adjetivo suelto y el que se confundía era el padre.** Al llevar la confusión a las cinco lenguas que no la tenían escribí `confus` y `verwirrt` a secas, y aparecieron dos falsos positivos que resumen el problema entero: «je suis confuse sur la dose à donner» y «ich bin verwirrt, welche Dosis soll ich geben» daban **emergencia por déficit neurológico**. El proyecto ya lo había resuelto y yo lo rompí sin mirar: sus patrones de confusión piden un verbo de observación —«seems confused», «wirkt verwirrt», «semble confus»— o una frase que sólo se dice de otro —«no sabe dónde está», «no reconoce»—, nunca el adjetivo solo. → **antes de añadir una forma a una regla, leer cómo están escritas las que ya funcionan**: si todas comparten una precaución, esa precaución es la respuesta a un fallo que alguien ya sufrió. Y el caso general que enseña: en un chat, el texto describe a dos personas —el niño y quien pregunta— y hay adjetivos que valen para las dos.
- **L110 — 390 de 483 guías colgaban de un solo enlace, y el sustituto de un grupo vacío se lo llevaba todo.** Search Console lo dijo primero, de la guía portuguesa de la meningitis: «Página de referencia: no se ha detectado ninguna». Al contarlo: **390 guías con un único enlace interno entrante —el índice de su idioma, que lista sesenta— y 24 con más de sesenta.** La causa estaba en tres líneas de `relatedTo`: agrupaba por `topic` exacto para dar «guías relacionadas», y cada tema tiene UNA sola guía por idioma, así que el grupo salía **siempre vacío** y entraba el sustituto —«las tres más recientes»—, que es el mismo para las sesenta guías de la lengua. El código no fallaba, la página se veía bien, y los enlaces existían: 1.449 de ellos, todos apuntando a las mismas veinte páginas. → **un `filter` que puede devolver vacío necesita que alguien compruebe con qué frecuencia lo hace**, porque el camino del sustituto se convierte en el camino normal sin que nada lo señale. Y el corolario de método: la señal no estaba en el código ni en la página, estaba en **contar el grafo** — el mismo fichero de pruebas comprobaba desde hacía días que cada enlace apunta a una página que existe, y a nadie se le había ocurrido la pregunta contraria, que cada página reciba algún enlace.
- **L111 — Rellenar con «lo más reciente» concentra; rellenar con un anillo reparte.** Al arreglar lo anterior, la primera versión completaba los huecos con las guías más nuevas y dejaba una cola de páginas con 40-49 enlaces entrantes frente a otras con 3. Para el lector, «la más reciente» y «la siguiente por orden alfabético de tema» son igual de arbitrarias; para el reparto no se parecen en nada. Con un anillo —cada guía enlaza a sus dos sucesoras en un orden estable— cada página **recibe por construcción** tantos enlaces como da, y el resultado pasó de mínimo 1 / máximo 64 a **mínimo 3 / máximo 13 / media 7,1**. La relevancia la pone la categoría; el suelo lo pone el anillo, y hace falta que lo ponga algo, porque una categoría puede tener un solo miembro. → cuando haya que elegir un relleno arbitrario, **elegir el que además equilibre**: cuesta lo mismo escribirlo y es la diferencia entre 390 páginas invisibles y ninguna. Y el orden del anillo se toma de algo que no cambia (el tema), no de la fecha: con la fecha, publicar una guía baraja los enlaces de todas.
- **L112 — La taxonomía no conocía diez temas pediátricos corrientes, y eso no se paga en enlaces sino en silencios.** Al clasificar los 69 temas publicados para poder enlazarlos, diez no casaban con ninguna categoría: meningitis, infección de orina, conjuntivitis, dentición, piojos, lombrices, picaduras, enuresis, dolores de crecimiento y salud mental del adolescente. La consecuencia importante no son los enlaces: la taxonomía le pone tema a la pregunta del padre, y **sin tema la puerta del «fuente o silencio» pasa de exigir un término a exigir tres**. Hay guía publicada de los diez, y el chat las alcanzaba peor que las de fiebre sin ninguna razón clínica. Es la L76 exacta —«la taxonomía no conocía ninguna enfermedad exantemática y el índice sí»— repetida trece días después con otra lista de temas. → cuando una lista cerrada clasifica lo que el usuario escribe, **derivar de lo publicado qué no clasifica** y comprobarlo en cada compilación; la primera vez se arregló a mano y volvió a pasar, porque arreglar una lista no es lo mismo que ponerle un candado.
- **L113 — Medí mi propio cambio de ayer y encontré tres falsos amigos que había metido yo.** Ampliar la taxonomía lo justifiqué diciendo que sin tema la puerta del «fuente o silencio» exige tres términos en vez de uno. La afirmación era correcta —`min_matched = 1 if topic else 3`— pero el conjunto dorado quedándose en 1,0 sólo dice que no rompí sus 118 casos, **no que haya mejorado nada**. Medido de verdad: de trece preguntas sobre los diez temas nuevos, **diez pasan de 0 fuentes a 6** —meningitis en castellano y en inglés, infección de orina, conjuntivitis, dentición— y ninguna empeora. Pero la mitad de la medición que no había planeado —«¿y las preguntas que el corpus NO cubre siguen callándose?»— destapó que las claves que acababa de añadir casaban por prefijo palabras ajenas: `uti` cogía «utilizar» y «utilisez», `wee` cogía «week» y «weeks», `dent` cogía «dentro». → **medir un cambio incluye medir la dirección en la que podría haber empeorado**, no sólo aquella en la que se espera que mejore; y la lista de esas direcciones se escribe antes de mirar los números, no después.
- **L114 — «early» y «infantil»: dos falsos amigos que llevaban meses clasificando mal, escondidos entre flexiones legítimas.** La misma auditoría, extendida a toda la taxonomía contra el vocabulario de las 483 guías, sacó `ear` → «early» (85 apariciones) e `infant` → «infantil» (62). No son casos raros: «early» es de las palabras más corrientes del inglés e «infantil» un adjetivo que un padre español usa a todas horas —«salud infantil», «silla infantil»—, y caían en `orl` y en `lactante`. Un tema equivocado hace tres cosas y ninguna se ve: multiplica por 1,5 los fragmentos de ese tema, por 0,7 todos los demás, y baja la puerta de tres términos a uno. Lo que los escondía es que el 90 % de lo que la auditoría lista **son flexiones correctas** —«vacuna»→«vacunación», «vomit»→«vomiting»—, así que la señal está enterrada en ruido legítimo y sólo aparece si se ordena por frecuencia y se lee. → una lista de palabras clave que casa por prefijo necesita **un inventario periódico contra el vocabulario real**, no una revisión al escribirla: los falsos amigos no se ven al añadir la clave, se ven al ponerla al lado del corpus. Y la solución no es quitar el prefijo, que hace falta: es poder decir «esta palabra entera» —una clave acabada en `$`— y usarlo sólo donde el inventario lo pida.
- **L115 — La misma palabra es dos cosas en dos idiomas, y en un idioma es dos cosas a la vez.** «Tableta» disparaba el sinónimo `tablet` → «screen time», así que **«mi hijo se ha tomado una tableta de paracetamol» —una pregunta de dosis— llevaba «screen time» a la consulta** y recibía tema de pantallas. En castellano se arregla con la palabra entera: el aparato es «tablet» y la pastilla «tableta». En inglés no se puede, porque «tablet» es las dos cosas —«two tablets of paracetamol»—, y ahí hace falta la frase: el aparato lleva artículo y complemento («on the tablet», «tablet time») y la pastilla lleva número. Y al escribir la prueba apareció el hueco simétrico: **la tabla inglesa no tenía ningún disparador del aparato**, así que un padre inglés que preguntaba por «the tablet» no llegaba al material de pantallas y uno español sí. → cuando una clave sea ambigua, mirar **si lo es en todos los idiomas o sólo en uno**: la palabra entera resuelve la ambigüedad entre lenguas y la frase resuelve la de dentro de una. Y escribir la prueba en las dos direcciones encuentra el hueco que el arreglo no tocaba.
- **L116 — «No he podido comprobarlo» no es «está roto», y la puerta del despliegue decía lo segundo.** La comprobación final de `deploy.sh` se murió en seco en la máquina del operador —un choque de OpenSSL de Windows, ajeno al proyecto— y el despliegue imprimió «!! el sitio responde mal a algo». El sitio estaba perfecto: salud en verde, las ocho lenguas a 200, la portada a 200. La línea era `smoke.py || echo "!! el sitio responde mal"`, y `||` mete en el mismo saco «he mirado y está mal» y «no he podido mirar», que piden cosas distintas: arreglar el sitio, o arreglar la comprobación **y saber que se ha desplegado a ciegas**. → un aviso que a veces miente se acaba ignorando, y entonces no sirve la vez que acierta; una comprobación automática necesita **tres resultados, no dos**.
- **L117 — Un código de salida no sirve para decir «me he muerto», porque el que se muere no escribe.** El primer arreglo fue hacer que `smoke.py` saliera con 2 cuando no pudiera comprobar. No valía: el choque mata el proceso **antes** de que corra ningún `except`, y el sistema devuelve 1 — justo el código de «el sitio está mal». La señal no puede ser algo que el programa tenga que escribir al fallar: tiene que ser algo que sólo escribe **al llegar al final**, y entonces su ausencia es la prueba, y es imposible de falsificar. Una firma de tres palabras en la última línea, y el guion busca la firma en vez de mirar el código. → cuando haya que distinguir «ha terminado mal» de «no ha terminado», la marca va en el camino del éxito, nunca en el del fallo. Es la L31 —un informe con la consulta rota se lee igual que uno normal— con la misma forma y otro disfraz, y el caso que más engaña ni siquiera es el choque: es un proceso que muere devolviendo **cero**.
- **L118 — Un antivirus apagó todo el TLS de Python en la máquina del operador, y la avería se veía como cualquier otra cosa.** El síntoma era `OPENSSL_Uplink: no OPENSSL_Applink` y un proceso muerto sin traza: se caía la comprobación del despliegue, se caía la inspección de URLs que llevaba dos horas corriendo, y `httpx` moría hasta en un `import`. La causa era una variable de entorno que no había puesto nadie del proyecto: **`SSLKEYLOGFILE`, apuntada por AVG a una tubería suya**. OpenSSL la abre al crear cualquier conexión, y en Windows abrir un fichero desde otra DLL necesita `OPENSSL_Applink`, que el Python de `uv` no trae. Lo que costó encontrarlo fue la forma del fallo: como muere el proceso entero, no hay excepción, no hay traza, y el mismo error sale con `import ssl` funcionando perfectamente. Se encontró listando el entorno, que es lo último que se mira. → cuando un fallo **no deje traza y afecte a programas que no comparten código**, el sospechoso es el entorno, no el código; y `env | grep` cuesta cinco segundos. Corolario que sí toca al proyecto: `SSLKEYLOGFILE` escribe las claves de sesión TLS en un fichero y **no tiene ningún papel legítimo en un despliegue ni en una comprobación de salud**, así que se quita en los dos sitios — no es tapar el problema, es que esa variable no debería estar puesta mientras se despliega.
- **L119 — El marcado decía que el paracetamol infantil es mercancía, y el tipo era el correcto según su nombre.** Search Console avisó en `/es/dose`: «Debe especificarse "offers", "review" o "aggregateRating"». El JSON-LD no tenía ningún error de sintaxis y el tipo parecía inmejorable: `about: { '@type': 'Drug', … }` en una página de dosis. Lo que no se ve leyendo el nombre es que **`Drug` tiene dos líneas de herencia en schema.org** —`Thing > MedicalEntity > Substance > Drug` y también `Thing > Product > Drug`—, y Google clasifica por la segunda: el validador de fragmentos de producto lo reclama como mercancía y le exige el precio o la valoración media de un jarabe para niños. Iban **168 páginas construidas** con ese tipo y Search Console sólo había rastreado una, así que el informe enseñaba el 0,6 % del problema. Y la corrección que sugiere el propio mensaje —añadir `offers` o `aggregateRating`— es exactamente lo que este proyecto tiene prohibido: inventarse la valoración de un medicamento infantil. La salida era `Substance`, que dice lo mismo, admite `activeIngredient` igual y no pasa por `Product`. → **un tipo de datos estructurados se elige mirando su cadena de herencia completa, no su nombre**: el nombre describe lo que significa para una persona y la herencia decide qué validador lo reclama. Y cuando un aviso de Search Console nombra una URL, lo primero es contar **cuántas páginas comparten esa plantilla**, porque el informe crece al ritmo del rastreo y no al del fallo.
- **L120 — El detector de fugas de idioma mira los titulares, y un dato estructurado no tiene titular.** En la misma línea del fallo anterior vivía otro que llevaba desde que existen las páginas de dosis: el índice `/dose` declaraba `name: "Paracetamol, ibuprofen"` **en inglés, idéntico en los ocho idiomas**, mientras el `<h1>` de la página española decía «paracetamol e ibuprofeno». `check_lang_leak.py` existe justo para eso y no podía verlo: se escribió para cazar páginas clonadas sin traducir y por eso lee título, `h1`, `h2`, eyebrow y lede — el texto que un humano ve. El JSON-LD no está en ninguno de esos sitios. Y de propina, una sola entidad decía ser dos medicamentos, con lo cual ni siquiera era cierto en inglés. Lo que lo mantuvo vivo es que **nadie lo lee nunca**: la página se veía bien en las ocho lenguas, la traducción existía en `drugs.yaml` desde el principio, y el único lector del dato estaba en Mountain View. → un comprobador definido por **dónde mira** («los titulares») deja fuera todo lo demás para siempre; conviene enunciarlo por lo que garantiza («ningún texto que salga de esta página está en otro idioma») y entonces la lista de sitios donde mirar se revisa sola. Corolario: el texto que sólo leen las máquinas no tiene quien se queje, así que necesita candado propio — es la única categoría de contenido donde un fallo puede vivir meses sin que nadie lo note.
- **L121 — El sitemap decía que 296 páginas habían cambiado, todos los días, y ninguna había cambiado.** `astro.config.mjs` daba a toda página que no fuera una guía la fecha **de la construcción** — el comentario del código lo decía con todas las letras, «when it was last generated»— y el sitio se reconstruye cada día para publicar las guías. Así que cada mañana el sitemap anunciaba 296 de 779 URLs como modificadas. Se paga dos veces: `lastmod` sólo sirve mientras es creíble, y **`ops/indexnow.py` decide qué mandar a Bing, Yandex, Seznam y Naver leyendo ese mismo campo**, así que llevaba semanas enviando exactamente las mismas 296 URLs cada día — justo lo que la documentación de IndexNow pide no hacer. El registro del servicio lo enseñaba desde el principio, con la misma línea repetida: «296 URLs nuevas o cambiadas», día tras día, con el mismo número. → **«cuándo se generó» y «cuándo cambió» son cosas distintas**, y en un sitio estático que se reconstruye por costumbre son opuestas. Y el corolario de método: cuando un proceso automático imprima siempre el mismo número, ese número es la avería, no el informe.
- **L122 — La fecha tiene que salir de algo que sobreviva al despliegue, y los ficheros generados no.** El arreglo obvio era tomar la fecha de modificación del fichero que alimenta cada página, y para las dosis eso parecía `src/data/drugs.json`. No vale: ese fichero **se regenera en el servidor en cada despliegue**, así que su fecha es la del despliegue — la misma mentira con otra cara. Se ve comparando los dos lados: `i18n.ts` tenía la misma fecha en el PC y en el VPS porque viaja en el tar, y `drugs.json` tenía la de hoy. Las fechas se toman ahora de `config/drugs.yaml` y `config/vaccines.yaml`, que son la fuente de verdad y viajan. → antes de apoyar nada en la fecha de un fichero, **preguntar quién lo escribe y cuándo**; en un despliegue conviven ficheros que viajan y ficheros que se fabrican al llegar, y sólo los primeros conservan una fecha que signifique algo. Comprobarlo cuesta un `ls` en cada lado.
- **L123 — El 90 % de lo que parecía Googlebot no lo era, y estuve a punto de decírselo al operador.** Contando robots en el registro de Caddy salieron 12.415 visitas de Googlebot en siete días, que para 779 páginas es dieciséis pasadas por página. La cifra era falsa: **11.116 de esas peticiones pedían `/config/database.yml`, `/.ssh/authorized_keys`, `/laravel/.env` o `/var/run/secrets/kubernetes.io/serviceaccount/token`**. Son rastreadores de credenciales poniéndose el nombre de Googlebot, que es gratis: la cadena de agente la escribe quien llama. Lo mismo pasaba con los motores de respuesta — GPTBot y ClaudeBot figuraban con 83 y 48 visitas y **ninguna de las dos había pedido jamás una página que existe**. Al contar sólo las peticiones con 200 el mapa cambia entero, y aparece lo que de verdad importa: Googlebot 1.270 desde 11 IPs, **bingbot 13, y ninguna de ellas a una página** (sólo robots.txt y el sitemap). → una cadena de agente es una **afirmación del visitante**, no un dato; para contar rastreadores hay que exigir además que la petición tenga sentido — un 200 a una ruta que existe — o verificar la IP. Y el aviso para mí: di la cifra alta en voz alta antes de mirar qué pedían, que es exactamente el error que este proyecto no se puede permitir.
- **L124 — El panel contaba 3.227 visitantes donde había 201, y el aviso estaba escrito encima del contador.** Lo notó el operador por el sitio correcto: demasiadas visitas para tan pocas consultas. Medido sobre catorce días: **6.258 vistas y 3.227 visitantes**, de los cuales **2.729 pedían una página y desaparecían** y sólo **211 llegaban a pedir un fichero de la propia página** —su hoja de estilo, su JavaScript, un tipo de letra—, que es lo que hace un navegador solo al abrir algo y lo que no hace nunca quien sólo quiere el texto. Lo que más duele: el código lo sabía. Tenía escrito justo encima del contador que «uno que pide una página y se va es un rastreador, diga lo que diga su agente», con el número medido al lado, y **nunca lo aplicaba**: la variable que lo contaba servía sólo para saber quién volvía. Dos coladeros al mirar quiénes eran los que más pedían: **Google**, cuyas direcciones `66.249.79.x` se llevaban 897 páginas con un agente de Chrome corriente —es su renderizador, que carga la página entera como un navegador y no dice «bot» en ninguna parte—, y agentes como `ContactScraper/DomainWorkers` o `Lightpanda`, que pasaban limpios porque el filtro buscaba bot|crawl|spider. → **un comentario que describe un fallo no lo arregla**, y es peor que no tenerlo: quien lee el fichero da por hecho que alguien se ocupó. Si se mide algo y no se va a actuar, la frase correcta es «esto NO se filtra», no la descripción del filtro que no existe. Y para contar humanos, la prueba no es lo que el visitante dice ser: es lo que hace que sólo hace un navegador.
- **L125 — Borrarlo del repo no lo borra del servidor: el despliegue añade y sobrescribe, nunca quita.** Retirados los dos ficheros de una insignia que ya no se usaba, el sitio los seguía sirviendo con 200. `deploy.sh` manda el código en un tar y lo desempaqueta encima, que es justo lo que hace falta para no perder lo que el servidor genera —las guías viven ahí— y justo lo que hace que un fichero retirado sobreviva para siempre. Estaba escrito en el propio guion, en un comentario sobre `web/content`, y no se me ocurrió que valiera también para lo que yo acababa de borrar. → **quitar algo del sitio son dos operaciones**, y la segunda no la hace el despliegue; comprobarlo cuesta un `curl` a la URL que debería dar 404, y sin ese `curl` uno cree haber retirado algo que sigue publicado.
- **L126 — El plan de temas se agotó y publicar «a diario» habría sido publicar nada.** Buscando por qué Bluesky llevaba una semana callado salió que la última guía era del 5-sep, y la primera explicación —no hay ningún timer que publique— era cierta pero superficial. Debajo estaba la buena: **`pending_topics` devolvía cero en las ocho lenguas**. El timer que iba a crear habría corrido cada mañana, no habría escrito nada y no lo habría dicho. Y al mirar el plan se vio de qué estaba hecho: fiebre, otitis, dentición, piojos, pantallas — pediatría española y británica. No tenía desnutrición, ahogamientos, tuberculosis, malaria, hepatitis ni poliomielitis, **que son los temas que matan justo donde el proyecto quiere llegar**, y cuyas fichas de la OMS llevaban indexadas en cinco lenguas desde el 3 de septiembre: documentos que nadie leía porque ninguna guía los escribía. → antes de automatizar que algo se repita, **comprobar que queda materia**; una cola vacía y un proceso roto se leen igual desde fuera, que es la L31 otra vez. Y el corolario que vale más: **el catálogo de lo que se publica dice a quién se está hablando**, y el nuestro decía «Europa» mientras la web decía ocho idiomas.
- **L127 — Conté códigos de salida y los llamé guías publicadas.** Mi lanzador diario invocaba al generador como subproceso y sumaba una guía por cada `returncode == 0`. Dijo `escritas=2` dos veces seguidas y **no había escrito ni una**: el subproceso arrancaba con otro entorno, se quedaba sin la clave del modelo y volvía con cero. Lo destapó contar los ficheros del servidor, no leer mi propio informe. Es exactamente la L116 —«no he podido mirar» contado como un resultado— cometida por mí dos días después de escribirla, y con el agravante de que mi informe era el único sitio donde se miraba. → **un contador cuenta la cosa, no la señal de que la cosa quizá ocurrió**: se cuentan ficheros antes y después, no códigos de salida. Y el segundo agujero del mismo lanzador: una guía escrita en disco **no está publicada** —el sitio es estático y hay que rehacerlo—, así que el proceso tiene que decir también si reconstruyó, y ese número también se mide.
- **L128 — Un PDF en hindi con capa de texto, y la capa no es hindi.** El manual de ASHA sobre cuidados del niño pequeño existe en hindi, 116 páginas, publicado por el NHSRC con licencia abierta: exactamente lo que llevaba semanas faltando. Se descarga, `pymupdf` extrae **196.056 caracteres** sin un solo error… y **cero de ellos son devanagari**. Está compuesto con una fuente heredada tipo Krutidev, donde «स्वास्थ्य» se guarda como `LokLF;` y sólo *parece* hindi al pintarlo con esa fuente concreta. La versión inglesa, misma maquetación y mismo número de páginas, sale limpia. → **que la extracción no falle no significa que el texto sea texto**: en lenguas de escritura no latina hay que contar caracteres del alfabeto esperado antes de indexar nada, porque el fallo no se anuncia y lo que entra al corpus es basura **que además figuraría en el catálogo como contenido en hindi**, que es peor que no tenerlo. Comprobar cuesta una línea: `len(re.findall(r'[ऀ-ॿ]', texto))`.
- **L129 — Rompí la guarda de arranque del CLI y no se notó durante horas, porque producción no la usa.** Al recolocar un comando que había quedado detrás de `if __name__ == "__main__":`, mi script asumió que la guarda tenía dos líneas y tenía tres: se llevó por delante la llamada `app()` y la dejó suelta a media altura del fichero. Desde entonces `python -m pedibot.cli <lo que sea>` **salía con código 0 sin hacer nada** —ni siquiera `--help` imprimía— y los servicios del VPS seguían funcionando perfectamente, porque systemd llama al ejecutable instalado y ése usa `app` directamente. Lo destapó una ingesta que dijo haber ido bien y dejó el índice igual, que es la L127 otra vez y en menos de un día. → **un script que corta y pega trozos de un fichero por número de línea tiene que verificar lo que ha quitado**, no sólo lo que ha puesto; y cuando algo se ejecuta por dos caminos distintos —consola y servicio—, arreglar o romper uno no dice nada del otro. La comprobación barata es `--help`: si no imprime, no hay programa.
- **L130 — Di una alarma clínica y el fallo era mi forma de medir.** Probando el triaje contra producción escribí las preguntas **literalmente en la línea de comandos**, en castellano y en hindi. Git Bash en Windows destroza el UTF-8 antes de que la petición salga, así que la API recibía basura y contestaba **HTTP 400**, que es lo correcto. Yo no miraba el código de estado: leía el campo `level` del cuerpo de la respuesta, que en un error viene vacío, y lo conté como «el triaje no clasifica». Con eso escribí en `STATE.md` que un recién nacido que no mama no disparaba la alarma en dos idiomas, y **se lo dije al operador como lo más grave del día**. Construyendo el mismo JSON con Python, las tres lenguas dan urgente con banner, y tres preguntas hindi de signos de alarma dan urgente, urgente y emergencia, con fuentes. → dos reglas, y la segunda es la que importa. Una: **para probar un producto multilingüe, la petición se construye en código**, nunca escribiendo el texto en el shell, y **se mira el código de estado antes que el cuerpo** — un 400 estaba ahí desde la primera prueba. Y dos: el proyecto ya exige releer toda cifra que salga fuera; **una alarma es una cifra que sale fuera, y una alarma clínica falsa gasta la confianza justo donde no se puede gastar**. Antes de escalar algo así, reproducirlo por dos caminos distintos, que aquí habría costado un minuto.
- **L131 — El índice nunca olvida: cuatro documentos citables y sin licencia registrada.** Al ampliar el corpus de la OMS, la ingesta avisó de un fichero «no está en el catálogo», y tirando del hilo salieron **cuatro documentos en el índice sin entrada de catálogo**: dos de los CDC y las dos de vacunación infantil de MedlinePlus. No era un fallo del día: eran **sobras de un renombrado**. El mismo contenido vive hoy bajo otro identificador —`mlp_en_childhoodvaccines`— y las piezas viejas seguían ahí porque la ingesta sólo añade, nunca retira. Lo que lo hace grave es dónde vive el campo `usage` (`publico` / `citar_solo` / `excluido`): **sin entrada de catálogo un documento no tiene licencia registrada, y aun así el buscador lo recupera y el bot lo cita**. Es el agujero que la regla de licencias existe para cerrar, abierto por el lado por el que nadie mira; una auditoría del 8-sep había dado «0 huérfanos», así que se coló después y en silencio. → **un almacén que sólo añade necesita que alguien pregunte periódicamente qué sobra**, y la pregunta correcta no es «¿está todo lo del catálogo?» sino la contraria, «¿hay algo indexado que el catálogo no conozca?». Candado `test_index_has_no_orphans.py`, en las dos direcciones. Y el corolario que costó cuatro tests rotos: al retirar un documento hay que **repuntar lo que lo citaba** — tres temas del plan de guías seguían anclados en los identificadores muertos.
- **L132 — Indexar un documento no es alcanzarlo, y desde fuera las dos cosas se leen igual.** Traídas 115 fichas de la OMS, el índice pasó de 291 a 405 documentos y parecía hecho. Medido: **20 de 35 preguntas no llegaban a su propia ficha**. Dos causas, las dos con lección previa. Una: **sin categoría en la taxonomía, la puerta del «fuente o silencio» exige tres términos en vez de uno** (L76, L112 otra vez, con otra lista de temas) — «my child has scabies» casa una sola palabra y se quedaba fuera *teniendo la ficha delante*. Dos: **el hindi no tiene ni un documento propio**, así que toda pregunta hindi tiene que puentear, y los puentes no conocían estas enfermedades. Arreglado: 35 de 35. → **la métrica de un corpus no es cuántos documentos tiene sino cuántos se alcanzan**, y hay que medirla con preguntas escritas como las escribe un padre, en cada idioma. Un documento indexado e inalcanzable es peor que no tenerlo: ocupa sitio en el catálogo y da la sensación de estar cubierto.
- **L133 — Decir la edad hacía peor la respuesta, en seis de los ocho idiomas.** La misma pregunta árabe sobre malaria sacaba la ficha de malaria la primera; **añadiendo «عمره ٤ سنوات» —«tiene 4 años»— desaparecía y entraba la de hepatitis B**. Las palabras de la edad entraban en la consulta FTS como si fueran un síntoma. Medido en las ocho lenguas: sólo el castellano y el inglés las tiraban; francés, alemán, ruso, árabe, portugués e hindi las metían. Es el patrón de siempre aquí —se construyó en dos idiomas y los otros seis heredaron media versión— y ya tenía lección con las palabras vacías alemanas. Lo que más pesa es la forma del daño: **un padre que da MÁS información recibía una respuesta PEOR por haberla dado**, y eso es exactamente lo contrario de lo que cualquiera espera. → cuando un dato se analiza aparte —la edad decide triaje, dosis y calendario— hay que **quitarlo también de la búsqueda**, y comprobarlo en todos los idiomas: la lista de palabras vacías es el sitio donde los idiomas nuevos se quedan a medias sin que nada falle.
- **L134 — La página que presume de ocho idiomas los describía en inglés.** La banda de organismos de la portada dice qué es cada fuente —«Servicio Nacional de Salud, Inglaterra», «Biblioteca Nacional de Medicina de EE. UU.»— y esas descripciones sólo existían en inglés, castellano y francés. Resultado medido: en las portadas **alemana, rusa, árabe, portuguesa e hindi, cinco de las ocho casillas salían en inglés**. Lo que lo vuelve especialmente malo es dónde estaba: en el bloque que existe para dar confianza, dentro de la página que más presume de hablar ocho lenguas, y justo cuando se acababa de hacer la cifra visible para que ese bloque se mirara más. Ningún candado lo veía: `check_lang_leak.py` lee titulares y esto son pies de casilla. → **cuando una tabla de traducciones se escribe con «los idiomas que hay ahora», los que llegan después heredan el respaldo y nadie lo nota**, porque un respaldo no falla, sólo queda mal. La comprobación barata es comparar la página traducida con la inglesa y exigir que difieran: si son idénticas, no hay traducción, hay respaldo. Candado `test_org_blurbs_are_translated.py`.
- **L135 — Un menú que se abre vacío promete algo y no lo cumple.** Tres guías del sitio existen **sólo en inglés y a propósito** —llevan el sufijo `_en` porque en las demás lenguas serían un duplicado de una que ya hay, y el generador las excluye de esos idiomas—. Eso está bien. Lo que estaba mal era lo que veía el lector: en esas tres páginas el selector de idioma **se abría para ofrecerse a sí mismo**. Pulsabas «EN ▾» y dentro sólo estaba «English». Tres páginas de 792, y aun así importa por dónde estaba: el argumento central del sitio es que habla ocho idiomas, y el único sitio donde eso se toca con el dedo es ese menú. → cuando un control se dibuja a partir de una lista, **hay que dibujar también el caso de la lista vacía**, y casi siempre la respuesta correcta no es un contenedor vacío sino no dibujar el control. El fallo no se ve revisando la página normal, porque la lista vacía es justo la que no aparece en la que uno abre para comprobar.
- **L136 — El corpus ya hablaba de dengue y de rabia; la capa que decide si hay que correr, no.** Traídas las fichas de la OMS de malaria, dengue, mordedura de serpiente, rabia y tétanos, el sitio publicaba ya sus guías y el buscador las alcanzaba. Medido lo único que importa de verdad —si el triaje reconoce **sus** urgencias—: **17 de 25 preguntas salían como rutina**. Tres categorías no tenían **ninguna** regla: mordedura de serpiente, mordedura de mamífero (que en la India es rabia, y la profilaxis se cuenta en horas) y sangrado con fiebre (el signo de dengue grave que la OMS enumera). Y una a medias: el trismo del tétanos saltaba en castellano, árabe y portugués y no en inglés ni en hindi. Al escribir el candado apareció además una cuarta grieta, en una regla vieja: `severe_abdominal_pain` —el **primer** signo de alarma de dengue grave— pedía en castellano «muy fuerte», «insoportable» o «empeora», y no conocía la palabra que usa un padre que acaba de traducir la ficha, «intenso»; fallaba también en francés y en ruso. Ahora 25 de 25. → **ampliar el corpus no amplía el triaje**, y las dos cosas se leen igual desde fuera: hay documento, hay guía, hay respuesta — y no hay banner. Cada vez que entren enfermedades nuevas hay que preguntarse **qué signo de alarma trae cada una** y medirlo en las ocho lenguas; la capa de seguridad se escribió desde la pediatría europea y no se actualiza sola por tener más papel detrás.
- **L137 — Una regla citaba un documento que no existe, y las 2.873 pruebas pasaron.** Cada regla de alarma lleva un `source`: el documento del que sale ese criterio, que es lo que separa «ve a urgencias» de una opinión. Las cuatro reglas nuevas citaban `who_en_snakebite-envenoming` y `who_en_dengue-and-severe-dengue`, con guiones; los documentos reales del catálogo son los mismos **con guiones bajos**. Nada lo vio: el suite entero pasó en verde con dos avisos clínicos apuntando al vacío. Es la regla de la casa —fuente o silencio— sin poner justo en la capa de seguridad, que es donde más falta hace. Lo destapó no fiarse: comprobar a mano, después de que todo estuviera verde, que las cuatro fuentes existían. → **un identificador escrito a mano contra un catálogo es una referencia, y toda referencia necesita quien la resuelva**; si nadie la resuelve en una prueba, el error no se nota nunca porque el fichero es YAML válido y el programa arranca. Candado `test_red_flag_sources_exist.py`, que además exige que ninguna regla se quede sin fuente. Segunda grieta del mismo día y la misma forma: al insertar las reglas con dos espacios de sangría se colaron **dentro de la lista de patrones de la regla anterior** — seguía siendo YAML válido, seguía habiendo 40 reglas, y las 39 pruebas nuevas fallaban sin decir por qué. La sangría de un fichero de configuración es código.
- **L138 — El árabe no llegaba a los documentos árabes, y la causa era una letra pegada.** El índice tiene 38 fichas de la OMS en árabe. Medidas diez preguntas escritas como las escribe un padre: **dos** llegaban a un documento en árabe y **cuatro no devolvían absolutamente nada** —«عض كلب ابني», «un perro ha mordido a mi hijo», daba cero resultados con `who_ar_rabies` indexado—. No faltaba corpus: falta morfología. En árabe el artículo y las preposiciones **se pegan** a la palabra siguiente, y el índice casa por prefijo. En la ficha de malaria, «الملاريا» aparece 55 veces, «بالملاريا» 19 y «للملاريا» 16, y la forma desnuda que escribe el padre, «ملاريا», **una sola vez**: el 32 % de las palabras árabes del corpus empiezan por «ال». Lo que más enseña es dónde estaba ya resuelto: **la tabla de sinónimos SÍ quitaba el clítico** desde hacía días, con su comentario explicándolo. El buscador no, la puerta del «fuente o silencio» no, y la taxonomía tampoco —y sin tema, esa puerta sube de un término a tres, así que el mismo fallo se cobraba dos veces—. → **una idea correcta metida en una sola capa no protege al producto**: cuando algo se arregla por una vía, hay que preguntar por cuántas otras pasa el mismo dato. Aquí eran tres, y las tres estaban a la vista. Arreglado en las tres: **9 de 10**. El hindi, que no tiene ni un documento propio y depende entero del puente, iba 7 de 10 por la razón gemela —lo que no está en la tabla no existe—: ahora 10 de 10.
- **L139 — El sufijo de marca se comía la parte que convence, en 166 de 800 páginas.** Un resultado de búsqueda enseña unos 60 caracteres de título, y el sitio ponía «— PediBot» al final de casi todos: diez caracteres que no dicen nada que el lector no vea ya en el dominio, empujando fuera del corte lo único que le haría pulsar. Los calendarios vacunales llegaban a **86 caracteres**. Y un detalle del propio recuento que casi me cuesta una cifra falsa: medido sobre el HTML crudo salían 170, porque `&#39;` ocupa cinco caracteres y el apóstrofo que representa ocupa uno — **hay que medir el título decodificado, que es el que ve el buscador**. La solución no fue acortar 166 títulos a mano: si no cabe, **primero se cae la marca**, y si aún no cabe se corta por una pausa del propio título —dos puntos, raya, interrogación—, que casi siempre deja un título mejor que el original («Portugal — Programa Nacional de Vacinação (PNV 2025)», 52 caracteres, frente a 86). Sólo 12 páginas de 804 necesitan puntos suspensivos. El `<h1>` y la tarjeta social siguen llevando el título entero: se acorta **sólo lo que enseña el buscador**. → cuando un defecto se repite en cientos de páginas, casi nunca hay que arreglar cientos de páginas: hay que encontrar la plantilla por la que pasan todas. Y el orden de lo que se cae al recortar es una decisión de producto, no del navegador.
- **L140 — El timer publicó su primer tema nuevo y llegó al sitio a medias, sin que nada fallara.** La guía de ahogamientos se escribió, se construyó la página, se subió y quedó viva — y **sin categoría de taxonomía**, porque esa clasificación la produce `export_catalog.py`, que hasta hoy corría a mano desde el PC. Sin categoría, la guía enlaza mal con las demás y se busca peor; y nada en el proceso lo dice, porque la página se construye igual de bien. Lo destapó un candado que ya existía (`test_internal_links.py`), no el proceso que lo causó, y apareció con **el primer tema nuevo de los dieciséis que acababa de añadir al plan**: los quince siguientes habrían salido igual. → **un proceso que produce contenido tiene que correr todos los pasos que ese contenido necesita, no sólo el que hace aparecer la página.** El olor característico es un guion que un humano recuerda ejecutar: mientras alguien lo recuerde funciona, y falla el día en que el trabajo lo hace una máquina a las 06:30. Ahora `publish_daily.py` reexporta antes de reconstruir.
- **L141 — El sitio publicaba `/dose/panadol` y el asistente no sabía qué era «panadol».** En el catálogo la marca está como «Panadol Children», y el emparejador trata un nombre con espacios como una frase: tenía que aparecer entera. Nadie escribe eso. Lo mismo con «Nurofen for Children» y «Motrin Children's». Medido el 11-sep-2026 sobre diez marcas árabes de uso corriente: el buscador reconocía **una**, y era la escrita en árabe — y Panadol es **el** antitérmico infantil del Golfo. Debajo había un segundo agujero de la misma familia: la pregunta árabe natural, «طفلي وزنه 14 كيلو، كم أعطيه من بنادول؟», **tampoco daba dosis quitando la marca del problema**, porque el detector parte la frase por una lista de signos **latinos** y el último token no era «بنادول» sino «بنادول؟», con la interrogación árabe pegada — otro punto de código. El hindi tenía lo mismo con el danda. → dos reglas. Una: **si el sitio publica una página de algo, el asistente tiene que entender ese algo**, y por el nombre a secas; publicar la página y contestar «no tengo información fiable» es peor que no publicarla, y la comprobación es automática porque las dos cosas salen del mismo catálogo. Dos: la puntuación es **parte de la lengua**. Ya llevo tres fallos del mismo molde —el borde de palabra en devanagari, el artículo pegado en árabe y ahora los signos— y el síntoma siempre es el mismo: no falla nada, sólo se deja de encontrar, y sólo en el mercado que no es el tuyo.
- **L142 — El padre indio no podía elegir el bote que tenía en la mano.** Las concentraciones vivían en dos sitios: `config/drugs.yaml`, que es lo que la web publica, y una tupla escrita a mano en `bot/dose.py` con un comentario que decía «todas las del catálogo» — verdad el 7 de septiembre y mentira desde que alguien tocó uno de los dos. Al ampliar el catálogo a India y al mundo árabe salió lo que faltaba: **125 mg/5 ml**, que es la presentación estándar del jarabe de paracetamol infantil en India (Crocin, Dolo, Metacin, Pyrigesic) y en Egipto (Cetal). O sea que el producto cuyo argumento es «te digo cuántos ml darle» no ofrecía el bote más vendido del país al que quiere ir — y la línea de al lado, 120 mg/5 ml, se le parece lo justo para cogerla por error. → **el clon podrido no avisa: no falla, sólo deja al usuario fuera.** Cuando un dato vive en dos ficheros, el candado que los obliga a decir lo mismo **en los dos sentidos** vale más que cualquier comentario que afirme que ya coinciden; un comentario así es una fecha de caducidad sin fecha.
- **L143 — Las páginas que más se buscan no tenían ni un encabezado.** Leído Search Console de los últimos 28 días en vez de suponer: de las veinte consultas que traen impresiones al sitio, **nueve son de marca con dosis** —«calculadora apiretal», «apiretal bebe 10 kilos», «dosis dalsy 40 calculadora», «calculo apiretal»—. Es, con diferencia, lo que la gente busca de aquí. Y esas páginas eran un título, una calculadora y una tabla de 36 filas: **ni un solo `<h2>`**, y la pregunta tal y como la escribe un padre no aparecía en ningún sitio de la página. Los números estaban todos; la pregunta, no. → **la página que responde una consulta tiene que contener la consulta**, y la forma barata de saber cuál es no es imaginarla sino leer el panel. Añadidas cuatro preguntas por página con las cifras sacadas de la misma tabla —ni un número escrito a mano— y **sin marcado `FAQPage`**, que Google reserva desde 2023 a sitios oficiales de salud: habría sido una queja más en Search Console a cambio de nada, como ya pasó con `Drug`.
- **L144 — Dos marcas del mismo fármaco se parecen porque SON lo mismo, y rellenarlas es mentir de otra manera.** Medido el solapamiento entre las 32 páginas de marca con 5-gramas sobre el texto visible (no con `quick_ratio`, que ya me engañó una vez): **28 parejas por encima del 70 %**, con Cetal ↔ Metacin al 96 %. La reacción refleja es escribir texto distinto en cada una para que no se parezcan; eso es paja, y en un sitio de salud la paja es ruido entre el padre y la cifra que busca. Lo que sí había que hacer era preguntarse **qué es verdad y sí cambia entre las dos**: dónde se vende cada nombre. Y resulta que eso responde la duda real —«me han dado Dolo y en casa tengo Crocin, ¿es lo mismo?»—, sale de un dato que ya estaba en el catálogo y no hay que inventarlo. El parecido bajó de 97 % a 92,6 %, que **sigue siendo alto y está bien**: el candado que escribí no fija un umbral de parecido, fija que cada página nombre su marca, responda con sus propios botes y diga de qué país habla. → cuando dos cosas se parecen porque son iguales, **el arreglo no es diferenciarlas sino añadir lo único que de verdad las distingue**; y si no hay nada, lo honesto es dejarlas parecidas.
- **L145 — «Lo arreglé» y no arreglé nada, y el candado dio verde porque no miraba donde dolía.** El aviso de PyMuPDF —«the `fitz` API is deprecated»— salía como **primera línea** de `pedibot search` y de `pedibot ingest`, tapando justo la que el operador mira. Llevaba toda la sesión filtrándolo a mano en cada medición en lugar de quitarlo. Lo «arreglé» con `warnings.filterwarnings(...)` en la cabecera del CLI, escribí un candado con tres comandos, dio verde, y **seguía saliendo**: dos cosas iban mal a la vez. Una, PyMuPDF **imprime en stderr**, no lanza un `warnings.warn`, así que no hay filtro que lo calle — lo destapó `python -W error -c "import fitz"`, que no reventó. Y dos, los tres comandos del candado —`dose`, `triage`, `flagged`— **no importan PyMuPDF**, así que pasaban antes y después de tocar nada. → dos reglas. Una: **antes de filtrar un aviso, averiguar cómo se emite**; si viene de un `print` a stderr, el arreglo es otro — aquí, migrar a `import pymupdf`, que es el nombre bueno desde la 1.24. Y dos, la que más me va a servir: **un candado que pasa antes del arreglo no es un candado**, es decoración; hay que verlo fallar primero, y si pasa a la primera es que está mirando el sitio equivocado. Bonus de la migración: el módulo nuevo trae tipos y mypy sacó **dos errores reales** en la extracción de PDF que llevaban meses invisibles.
- **L146 — Una revisión que nunca ha fallado no está probada.** Escribí `pedibot doctor` para que un timer pueda colgarse de `$?`, con seis comprobaciones y su `DOCTOR-FIN`. Todos los tests miraban la instalación sana: que existiera, que fuera rápida, que mirase lo que dice mirar, que no imprimiese la clave. Ninguno le rompía nada. Una orden cuyo único motivo de existir es **salir con código 1 cuando algo está mal** hay que verla salir con 1: se le apunta el índice a una ruta inexistente y se comprueba que sale la línea de fallo **y** el código. Al hacerlo salió además un detalle de medición que me habría engañado: `comando | head -6; echo $?` devuelve el código de `head`, no el del programa. → **la prueba de un detector es el caso que tiene que detectar**, no el caso bueno; y un código de salida se lee sin tubería detrás.
- **L147 — Una fuente que el padre no puede leer no es una fuente.** El argumento entero de este producto es que la respuesta **se puede comprobar**: cada frase lleva el número de su pasaje y el pasaje está a un clic. Si el pasaje está en un idioma que el lector no lee, la comprobación no existe y la cita es decoración. Medido sobre quince preguntas hindi corrientes: **el 47 % de los pasajes citados estaba en castellano**, y cinco de las quince se respondían entera y exclusivamente con hojas de la SEUP. El hindi no tiene ni un documento propio, así que **puentear está bien** — lo que no da igual es a qué lengua: en la India el inglés es lengua oficial y el segundo idioma de casi cualquier padre alfabetizado, y el castellano no lo lee nadie. Arreglado con un empujón a la lengua puente, nunca con un castigo a las demás (castigar se midió en agosto y rompió la dirección inglés→castellano de la que vive el corpus): hindi **53 → 69 % legible**, árabe **69 → 81 %**, y las citas en castellano al hindi de 47 a 31 %. Probé 1,7 en vez de 1,4 y lo descarté porque **le quitaba al árabe sus propias fuentes** para meter inglesas, que es peor. → **el idioma de una cita es parte de la cita.** Un corpus multilingüe no se mide por cuántas lenguas tiene sino por si el lector de cada una puede abrir lo que se le enseña; y cuando no hay nada en su lengua, la pregunta correcta no es «¿a qué idioma puenteo?» sino «¿qué idioma lee esta persona?», que depende de dónde vive y no de cuántos documentos tengo yo.
- **L148 — Tres mediciones seguidas y las tres mentían por el mismo sitio: el arnés.** Midiendo el chatbot, en media hora: (1) mandé `age_months` en la petición y conté cinco casos de «pide la edad teniéndola» — **`AskIn` no tiene ese campo**, así que el bot hacía lo correcto y mi JSON se ignoraba en silencio; (2) leí `sources` de catorce respuestas y concluí que once no citaban nada en seis idiomas — **eran mis propios 429**, porque la API limita a veinte preguntas por diez minutos y yo no miraba el código de estado; (3) comparé lo que recuperaba un `Retriever` construido a mano contra lo que citaba el motor de producción y vi un desajuste enorme — **el mío no llevaba modelo**, así que no expandía la consulta y estaba comparando dos búsquedas distintas. Ninguna de las tres era un fallo del producto. → la L130 ya decía «mira el código de estado antes que el cuerpo» y la repetí igual. Le añado lo que faltaba: **un arnés que no reproduce producción produce hallazgos que no existen**, y las tres formas de que eso pase son las mismas de hoy — un campo que el servidor ignora, un límite que responde otra cosa, y una pieza construida a mano que no es la que corre. Antes de escribir un número en un informe, comprobar que el camino que lo produjo es el camino de verdad.
- **L149 — Buscar y contar usaban alfabetos distintos, y la puerta tiraba los documentos buenos.** De las 345 respuestas de producción, seis acabaron en «no tengo información fiable», **las seis en castellano**. Una era «le duele el oido desde ayer», con cinco fichas de oído en el corpus. Mirando qué devolvía el índice **antes** de la puerta del «fuente o silencio»: `mlp_es_earinfections` y cuatro trozos de `seup_otitis`, todos con **`matched=0`**. El índice FTS está creado con `remove_diacritics 2` y guarda «oído» como «oido», por eso los encontró; el recuento que decide si un pasaje vale se hacía en Python sobre el texto crudo, con la tilde puesta, y `"oído".startswith("oido")` es falso. **El buscador encontraba y el contador tiraba.** Al arreglarlo hubo que preguntarle al índice qué funde de verdad, escritura por escritura, en vez de suponerlo: «oído»=«oido» (47 pasajes las dos), «ребёнок»=0 contra «ребенок»=8 —también funde la ё—, «детей»=125 contra «детеи»=0 —**no** funde la й, que es una letra— y «الحمى»=20 contra «الحمي»=1 —no funde la ى—. Mi primera versión quitaba toda marca combinante detrás de letra cirílica y convertía «сейчас» en «сеичас»: lo pilló el candado. → **cuando dos capas comparan texto, tienen que normalizar igual, y la forma de saberlo es preguntárselo al almacén, no leer su documentación.** Y el corolario que casi rompo: en árabe y devanagari las marcas no son tildes, son la palabra.
- **L150 — Probé una idea razonable, la medí y era peor; fuera.** Para que la lengua del lector mandara sobre la lengua puente, reordené los resultados poniendo delante los pasajes en el idioma del padre que aguantaran el 60 % de la puntuación del primero. Suena bien y estaba mal: `source_hit` bajó de **0,972 a 0,962**, rompió un caso inglés que funcionaba y **ni siquiera arregló el francés** que quería arreglar —la ficha francesa no estaba entre los candidatos, así que no había nada que promover—. Revertido. El A/B limpio del empujón a la lengua puente dice lo que hay: con 1,0 fallan tres casos del golden set y con 1,4 fallan otros tres —cambia el portugués por el francés—, empatados en 0,972, y a cambio la legibilidad para el lector hindi sube de 53 a 69 % y la del árabe de 69 a 81 %. → **una idea que suena bien se mide antes de quedársela**, y cuando el número baja se tira aunque duela; y el que no arregla lo que dice arreglar hay que mirarlo dos veces, porque muchas veces no toca el camino que creías.
- **L151 — Una fuente se citaba con el título «This page has been removed».** Tirando del hilo de los tres temas hindi que seguían citando hojas españolas aparecieron dos cosas que no eran de ranking sino de integridad del corpus. La primera: `nhs_en_breath_holding_in_babies_and_children` tenía **578 palabras de contenido bueno** y por título el aviso de redirección que el recolector se trajo por error, así que un padre preguntando por espasmos del sollozo habría leído debajo de la respuesta `NHS — "This page has been removed"`. **El título no es metadato: es la mitad visible de la cita**, y en un producto cuyo argumento es que la respuesta se puede comprobar, una cita que se presenta como página muerta vale menos que ninguna. La segunda: dos «fuentes» del NHS eran **índices de navegación** — `nhs_en_ibuprofen_for_children`, 59 palabras cuyo texto entero son los nombres de las pestañas («About ibuprofen / Who can and cannot take it / How and when to give it»), **ni una dosis**, y ya citada a alguien según el registro. → al recolectar web hay que comprobar **dos cosas distintas**: que el texto diga algo (un suelo de palabras separa el resumen breve del índice de enlaces: 49 y 59 contra 69 del más corto de MedlinePlus, que sí informa) y que el título sea el del documento y no el del andamio de la página. Las dos se miran en un minuto y ninguna se mira sola.
- **L152 — Quitar una fuente del catálogo no es una línea de YAML.** Marqué los dos índices de navegación como `excluido`, que parecía lo obvio, y **cayeron siete candados a la vez**: el índice seguía teniéndolos, las licencias dejaban de cuadrar y —lo que importa— **hay guías publicadas ancladas en ellos**, así que sacarles la fuente de debajo las deja huérfanas. Revertido. → **una fuente tiene cosas colgando aguas abajo** —índice, licencias, anclas de guías ya publicadas— y retirarla es una operación, no una edición. Y aquí el arreglo bueno tampoco era retirarla: era **traerse el contenido de verdad**, porque las páginas de medicamentos del NHS reparten el texto en pestañas y el recolector sólo se trajo la portada. Cuando la reacción refleja (borrar) rompe siete cosas, casi siempre es que el problema estaba un paso antes.
- **L153 — El panel decía «sin fuente: 6» y ese número no se puede arreglar.** Es el contador de las veces que un padre preguntó y se llevó «no tengo información fiable sobre esto». Llevaba ahí desde el principio, con su aviso en rojo cuando pasa de cero, y **no decía cuáles**. Para saberlo hubo que abrir la base de operaciones a mano, y al hacerlo: de las seis, **tres eran fallos arreglables** —«le duele el oido desde ayer» con cinco fichas de oído en el corpus, «le sangro la nariz un momento y ya ha parado» con la del NHS indexada— y tres eran negativas correctas, incluida «mi perro se ha comido una tableta de chocolate». Puesta la lista en el panel, aparecieron **dos más que no había visto**: un recién nacido hindi que no mama y está decaído, y una pregunta francesa por el calendario vacunal a los 3 meses. Las dos responden ya, y eso es exactamente el argumento: **el número las tapaba**. → un contador de fallos **sin la lista de fallos es una alarma sin dirección**: dice que algo va mal y no deja actuar, así que se acaba mirando como decoración. Y la distinción que el número borra es justo la que importa: cada línea es un hueco del corpus o un fallo del buscador, y son dos arreglos distintos. La regla general: **si un panel enseña un número que el operador querría reducir, tiene que enseñar también las filas que lo componen**.
- **L154 — El hindi llevaba desde siempre con cero documentos propios, y la puerta estaba abierta por otro lado.** Lo dado por bloqueado el 11-sep era «no hay texto pediátrico hindi con licencia abierta»: el único candidato, el manual de ASHA, estaba compuesto en Krutidev y extraía 196.056 caracteres **sin un solo devanagari** (L128). La conclusión correcta de aquel día era «ese documento no sirve»; la que me llevé, sin decirlo, fue «no hay material hindi», y con ella el hindi se quedó un día más dependiendo entero del puente a otras lenguas. La puerta estaba en un sitio que no había mirado: **las traducciones de los Vaccine Information Statements del CDC**, obligatorias por ley federal en EE. UU. y traducidas a decenas de idiomas — diez vacunas en hindi y nueve en árabe, comprobadas una por una antes de catalogar como manda la L128: **entre 77 y 89 % del texto en su escritura**, de 3.270 a 5.120 caracteres cada una. Hindi 0 → 10 documentos, árabe 38 → 47. → **«no hay fuentes en esa lengua» casi nunca es verdad; lo que suele ser verdad es «no hay fuentes donde he mirado»**, y la diferencia entre las dos frases es un mercado entero. Cuando una vía se cierra —una licencia, una codificación—, el cierre es de esa vía, y conviene escribirlo así para no cerrar de paso la pregunta.
- **L155 — Saqué el título del propio PDF para que estuviera en el idioma del padre, y dos salieron rotos.** La idea era buena y el mismo día tenía la lección al lado (L151: el título es la mitad visible de la cita, y tiene que estar en la lengua del lector). Así que lo extraje de la primera línea de cada PDF… y dos de diecinueve dieron «एमएमआर वै(सीन (खसरा, गलसुआ और 4बेला)» — la maquetación del PDF rompe ligaduras del devanagari al extraer. Lo pilló un candado que existía desde antes y que comprueba algo aparentemente menor: **paréntesis sin cerrar en los campos del catálogo**. Un título con un paréntesis abierto es la firma de una extracción rota. → **el texto sacado de un PDF no es texto de fiar aunque esté en la escritura correcta**, y menos en devanagari o árabe, donde las ligaduras y el orden RTL se rompen sin avisar. Para algo que se enseña al lector, más vale una cabecera canónica escrita a mano —la misma para las diecinueve, sacada de las que sí salieron limpias— que diecinueve extracciones de las que dos mienten.
- **L156 — Un arreglo a mano en un fichero generado es una cuenta atrás.** Por la mañana corregí en `config/fuentes_web.yaml` el título «This page has been removed» de una ficha del NHS con 578 palabras de contenido bueno (L151). Unas horas después, al traerme siete fichas nuevas, `fetch_web_sources.py` **regeneró el fichero entero y revirtió la corrección sin decir nada** — y sólo me enteré porque se me ocurrió comprobarlo después de ejecutarlo. El arreglo tenía que vivir en el generador, no en su salida: ahora hay un `TITULOS_CORREGIDOS` con el motivo escrito al lado. → **antes de editar a mano un fichero de configuración, preguntarse quién más lo escribe.** Si lo escribe un guion, la edición dura hasta la siguiente ejecución, y el momento en que se pierde no coincide con el momento en que se nota. La pista está siempre a la vista: un fichero que empieza diciendo cuántas entradas tiene y de qué fecha es un fichero generado.
- **L157 — Fui a añadir interactividad y lo primero fue descubrir que la que había no funcionaba.** Leí `Chat.astro` línea a línea para ver dónde meter botones, y salieron tres cosas rotas que nadie había tocado: las **respuestas rápidas nunca han funcionado** —se pintan con `class="fb opt"` y el manejador de clics sólo distingue compartir / niño / escuchar, así que cualquier otro `.fb` cae al voto, manda `answer_id=NaN` y desactiva los botones con un «✓»; el padre toca «¿fiebre o tos?» y se le agradece un voto que no ha dado—; en un **503 el padre ve la palabra «undefined»**, porque la frase existe en las ocho lenguas y no viajaba al cliente; y lo mismo en el 429 de la ruta de la foto. Ninguno de los tres lo veía prueba alguna: el chat se probaba por su API, y la API estaba bien. → **un botón es una promesa, y una promesa se comprueba pulsándola**, no leyendo que existe. La regla que dejo es la de la última prueba: todo `S.x` que el cliente pinta tiene que estar en lo que el servidor le manda, y el candado ahora compara las dos listas. Y la de fondo: antes de añadir una función interactiva, pulsar las que ya hay.

- **L158 — Una pregunta que ofrecemos nosotros tiene que tener fuente, y medirlo enseñó dos cosas que el golden no veía.** Escribí 244 preguntas siguientes en ocho lenguas —las que un padre hace después de «tiene fiebre»— y antes de pintarlas les puse una prueba: cada una, en su lengua, tiene que encontrar pasajes. **19 no encontraban nada**, y las 19 por la misma puerta: sin asunto en la taxonomía el «fuente o silencio» exige tres términos, y una pregunta de padre corta tiene uno o dos. Faltaban palabras de padre —«atmet», «picor», «зуд», «ударился», «ओआरएस», «الإماهة»— que el golden (escrito por mí, con mi vocabulario) no usa. Añadirlas subió el golden de 0,972 a 0,981 sin tocar un caso. Y una pregunta, «no quiere comer», no tenía fuente en **ningún** idioma: el corpus no cubre al niño de dos años que rechaza la comida, que es de lo más común que se pregunta. → **Las preguntas que el producto ofrece son un conjunto de evaluación gratis**, escrito desde el otro lado —lo que el padre diría, no lo que yo buscaría— y en ocho lenguas. Cuando falla una, o falta vocabulario (se arregla) o falta el documento (se anota, y la pregunta no se ofrece hasta que esté). Lo que no se hace es ofrecerla y que acabe en «no tengo fuente»: eso es peor que ninguna.
- **L159 — Una pregunta de seguridad hecha antes de responder es un muro.** «Para responder con seguridad necesito la edad» era una frase correcta que dejaba al padre sin nada si no contestaba. *(Corregido el 13-sep: la primera versión decía «el registro dice cuántos no lo cruzan: diez de once». Eran sondas mías; ver L160.)* El error no estaba en la regla (fiebre en menor de tres meses es urgente y sin edad no se sabe) sino en el orden: pedir antes de dar. Lo mismo se consigue respondiendo —la regla del lactante en la primera frase, sin dosis concretas— y pidiendo la edad al final para afinar, con botones. → **Lo que se pide al padre se pide después de haberle dado algo**, y toda pregunta que el producto hace se mide por cuántos la contestan, no por lo razonable que suena. Y la segunda: una prueba que documenta un fallo como esperado («un año y medio» → 12) lo protege; si se sabe que está mal, la prueba dice lo que debería ser y falla hasta que se arregle.
- **L160 — Medí «tráfico real» con el filtro equivocado y le vendí al operador mis propias sondas como padres.** Para decidir el cambio de la edad leí la base de producción con `source != 'test'` y salieron «137 respuestas reales» y «10 de 11 padres no volvieron». El proyecto ya tenía la definición correcta —`REAL_ONLY`, web/telegram/agent— y el panel la usa; mis sondas iban sin cabecera y quedaban como `unknown`, que no es un padre. Cuando el operador preguntó «¿eran consultas o eras tú?», el log de uvicorn contestó en un minuto: 343 de 344 desde mis IPs. → **Antes de citar tráfico, se cruza con el log por IP**, y se filtra con la definición que ya existe, no con una escrita al vuelo. Y toda sonda contra lo vivo lleva `x-pedibot-client: test`, sin excepción: una respuesta de verdad a una pregunta de prueba se cuela en el panel como `web` si la sonda imita al chat, que es lo que hice con el botón `tel:`.
- **L161 — Una palabra que ayuda a encontrar algo no demuestra que encuentre lo correcto: «बच्चा → baby» llevaba desde el 5-sep inclinando las preguntas de niños de cualquier edad hacia las fichas del lactante.** En hindi, «बच्चा» es la palabra con que un padre dice «mi hijo», y alguien la tradujo por «bebé / lactante». Subía el número de términos casados en casi cualquier pregunta, así que la búsqueda parecía funcionar mejor, y ninguna prueba medía a QUÉ ficha llegaba: «मेरा बच्चा मोबाइल बहुत देखता है» («mira mucho el móvil») llegaba a los cólicos del lactante con dos términos casados. Al quitarla, una pregunta («moja la cama») se quedó sin fuente, y eso también fue información: se sostenía sólo por la palabra equivocada. → **Una batería de búsqueda comprueba la ficha que sale, no que salga alguna**; y un sinónimo genérico («niño», «hijo», «child») no se expande nunca a una etapa concreta, porque arrastra todas las preguntas hacia ella. Y del mismo lote, en el triaje: un prefijo en árabe es más peligroso que en latín, porque la raíz de tres letras («حرق», quemar) es también la de «حرقة», escozor; ahí la regla necesita la exclusión escrita, no confianza en el contexto.
- **L162 — Una orden al modelo se prueba con una pregunta que NO la necesita.** Escribí «abre con la regla del lactante febril» para las respuestas con fiebre y sin edad, lo probé con «mi hijo tiene fiebre», salió bien y lo desplegué. La condición estaba mal —«sin edad», no «sin edad y con fiebre»— y ninguna prueba podía verlo: el modelo falso de la suite devuelve un texto fijo, así que la orden nunca se ejecuta en local. Un día entero después, cinco preguntas en vivo sobre queroseno o pantallas abrían hablando de fiebre. → **Toda orden condicional en el prompt lleva dos pruebas: el caso que la dispara y uno parecido que no**, y la segunda se escribe sobre la función que arma el prompt (`_age_context`), que sí se puede probar sin modelo. Y verificar en vivo con preguntas de otro asunto que el del cambio, porque ahí es donde se ve lo que el cambio toca sin querer.
- **L163 — «Excluir al operador» no es excluir un navegador: es excluir a una persona que usa varios aparatos, varias redes y días distintos.** El filtro que había era correcto y estrecho: el navegador exacto que abrió /admin. Medido contra el registro real, dejaba pasar el móvil del operador en su wifi, su Chrome de casa los días que no abrió el panel, y todo lo que preguntaba desde el chat, que se presenta como lector por construcción. Y cada filtro tiene su límite legal propio: las visitas pueden ir por IP porque el registro del servidor ya la tiene, las consultas no, porque /legal promete guardarlas sin ella — ahí la identidad tiene que viajar en el navegador. → **Un filtro de «lo nuestro» se valida sobre los datos reales contando lo que se cuela, no sobre casos inventados**: la primera ventana (un día) pasaba todas las pruebas y dejaba 80 páginas fuera. Y cuando una prueba de privacidad choca con un cambio, se precisa lo que protege (lo que el sitio escribe en el navegador de un lector), no se afloja.
- **L164 — Una expresión regular escrita para una escritura se rompe en silencio en las otras, y el troceador era la más escondida.** El separador de frases cortaba delante de `[A-ZÁÉÍÓÚÑ¿¡•-]`: en cirílico no reconocía la mayúscula, el árabe no tiene y el devanagari termina con «।». Nadie lo vio desde que se escribió el troceador (24-ago) porque nada fallaba: la búsqueda devolvía algo, el modelo respondía, el golden (casi todo latino) no cambiaba. Salió al meter una página de la OMS en cinco lenguas y ver que la francesa daba siete pasajes y la rusa uno. → **Cuando la misma fuente existe en varias lenguas, se compara cómo queda en cada una**: es la prueba más barata de que un paso del proceso no depende de la escritura. Y la segunda, del mismo lote: antes de decir qué tabla usa un país, leer la fuente oficial — tres de los once no usan la de la OMS y una página que lo diera por hecho mentiría justo en el número que el padre compara con su cartilla.
- **L165 — «No aparezco en la búsqueda» no prueba nada si la búsqueda te excluye a ti mismo, y la di por prueba.** Revisando por qué el agente ACP llevaba dieciocho días sin trabajos, busqué «PediBot» con su propia CLI, no salió, y lo conté como síntoma. Luego leí el SDK: `browseAgents` manda `walletAddressToExclude` con la cartera de quien busca. El hallazgo real era otro y sí estaba medido —`lastActiveAt: None` hasta abrir el socket de `events listen`—, pero la frase «no lo encuentra nadie» era una inferencia sobre una prueba inválida. → **Antes de usar una ausencia como evidencia, comprobar que el instrumento podía ver la presencia**: buscar algo que sé que existe con la misma herramienta, o buscar desde otro lado. Y del mismo lote, una de seguridad: una copia temporal de un llavero se limpia con `trap ... EXIT`, nunca con un `rm` al final de un script con `set -e`, porque el primer fallo la deja en `/tmp` — me pasó, y se borró al minuto.

## L166 · Una guía arreglada a mano vuelve sola si se despliega como siempre (16-sep-2026)

`ops/deploy.sh` **se trae `web/content` del servidor antes de subir nada**, porque el servidor
publica guías solo y su copia manda. Consecuencia que costó dos veces el mismo arreglo: corregí
a mano el encabezado castellano de una guía portuguesa, desplegué —y el despliegue restauró la
versión del servidor encima—; el `git add -A` siguiente committeó la reversión, y la prueba de
idiomas volvió a fallar en la tanda siguiente como si no hubiera hecho nada.

Dos reglas de esto:

1. Un arreglo a mano en `web/content` se despliega con **`--no-pull`**, que existe justo para eso,
   y se comprueba en vivo después.
2. Lo que se arregla a mano vuelve porque lo escribe una máquina: el arreglo de verdad es la
   comprobación en el publicador. `detect_lang` sobre el artículo entero no ve una línea en otra
   lengua, así que ahora el título y los encabezados pasan por los mismos marcadores que revisan
   el sitio construido (`pedibot.lang_markers`), y una guía mezclada no se escribe.

## L167 · Una guía escrita para un lector que no puede abrir sus fuentes (16-sep-2026)

`gather_hits(index, topic)` elegía las fuentes **sin saber en qué lengua se iba a escribir**. Las
anclas de cada tema son españolas porque el corpus empezó en castellano, así que la guía hindi de
la fiebre salía con cinco fuentes y las cinco eran la misma hoja del SEUP. Medido sobre lo
publicado: **20 de 62 guías en hindi, 20 de 62 en árabe, y 19-20 en ruso, alemán y francés**
citaban únicamente material que ese lector no puede abrir.

Tres cosas que salieron de arreglarlo:

1. **La consulta manda sobre el reparto.** Veintiséis temas buscaban sus fuentes con una frase
   sólo en castellano («fiebre niño qué hacer cuándo consultar»), así que en el saco de candidatos
   no entraba **ni un pasaje inglés**: reordenar no podía arreglar nada. Los temas nuevos ya
   escribían la consulta en los dos idiomas; ahora lo hacen los veintiséis viejos.
2. **Buscar más hondo cuando hace falta material legible.** Con `top_k=40`, de la ficha del NHS
   sobre la fiebre casaba UN pasaje. Con 90, tres. El corpus los tenía; la ventana no.
3. **Renombrar una guía está bien; matar su dirección, no.** El publicador renombra al regenerar
   (así se arreglaron slugs mal transliterados), y eso se conserva — pero ahora cada renombrado
   deja su redirección en `web/content/_redirects.json`, que el sitio lee al construirse. La
   dirección es lo único de una guía que no se puede rehacer.

## L168 · Un dato de un país no se corrige con el instinto de otro (17-sep-2026)
Arabia Saudí reporta la BCG a los **6 meses** y Kuwait a los **3**. Cualquiera que conozca el
calendario europeo lo lee y piensa «esto está mal, la BCG va al nacer». Estuve a punto de tirar
esas dos filas por sospechosas.

Lo que las salvó no fue una opinión sino una serie: la OMS publica todos los años desde 1995, y
Arabia Saudí dice «al nacer» hasta 2018 y «6 meses» de 2019 en adelante, siete años seguidos.
Kuwait lleva más de diez con los 3 meses. Un error de tecleo no se repite siete veces; un cambio
de programa, sí.

**La regla**: antes de corregir un dato raro de un país, mírale la historia en la propia fuente.
Si es estable, es su política y va tal cual, con una nota que lo diga — que es lo que un padre
saudí necesita leer, porque él tampoco se lo espera.

## L169 · Una edad puede repetirse si una de las dos no es una cita (17-sep-2026)
La prueba que vigila los calendarios prohibía edades repetidas, y con razón: una edad dos veces
es casi siempre la misma visita escrita dos veces. Pero en el Golfo, a los 6 meses tocan la
hexavalente **y** empieza la campaña anual de gripe, y son cosas distintas: la herramienta
arrastra las casillas anuales a todas las edades posteriores y las fijas no. Fundirlas le habría
dicho a un padre de un niño de cinco años que le toca la hexavalente.

La comprobación se hace ahora dentro de cada grupo. **Una regla que obliga a falsear el dato para
cumplirla está mal escrita, no mal el dato.**

## L170 · Un hueco encontrado a mano quiere decir que hay más (17-sep-2026)
El operador buscó «mi hijo cojea y tiene fiebre» y salía rutina. Lo arreglé, y ahí podía haber
terminado. Lo que hice en su lugar fue preguntarme **cómo había entrado ese hueco** y buscar a los
demás con el mismo método: sacar del índice los pasajes que ENUMERAN motivos de consulta, partir
cada lista en frases y pasárselas al triaje como si las escribiera un padre. De 5.123 frases, 153
sonaban graves y salían rutina; cinco eran huecos reales, uno de ellos a seis horas de perder un
testículo.

**La regla**: cuando alguien encuentra un fallo usando el producto, el fallo no es uno — es el
primero de su clase que alguien vio. La pregunta no es «¿lo he arreglado?» sino «¿con qué medida
habría salido solo, y qué más sale con esa misma medida?».

## L171 · El aviso sin la explicación deja al padre a medias (17-sep-2026)
Las reglas nuevas de la fontanela y del testículo saltaban perfectamente: banner rojo, «llama
ahora». Y el texto debajo decía «no tengo información fiable sobre esto», teniendo el capítulo
«Escroto agudo en la infancia» indexado desde agosto.

El triaje y la búsqueda son dos sistemas distintos y se arreglan por separado: uno reconoce la
frase del padre, el otro encuentra el documento. **Arreglar sólo el primero produce una alarma
muda**, que asusta sin explicar y manda a urgencias sin decir a por qué. Desde hoy, cada regla
nueva se prueba dos veces: que salte, y que la respuesta traiga algo detrás.

## L172 · Que el patrón esté escrito no quiere decir que salte (17-sep-2026)
Ya había un candado que exigía a cada regla de alarma patrones en los tres alfabetos, y las 51 lo
pasaban. Parecía cobertura y no lo era: mide que estén ESCRITOS. La medida buena es otra —**una
frase por regla y por idioma, escrita como la teclea un padre**— y con ella fallaban **72 de 408**,
uno de cada seis.

No eran reglas menores. «Tiene 41 de fiebre» no saltaba en seis idiomas porque todos los patrones
pedían el símbolo de grados. Las autolesiones fallaban en seis porque cada lengua usa otro verbo.
El golpe de calor fallaba en los ocho porque la regla esperaba oír «golpe de calor» y un padre
describe la escena. Y la regla del lactante con fiebre —la más importante que hay— no funcionaba
en ruso porque «двухмесячный» es una palabra sola y el lector de edades esperaba una cifra.

**La regla**: una comprobación estructural (¿hay patrones? ¿en los tres alfabetos?) vale para que
nadie se deje una lengua entera, y para nada más. Lo que decide si el aviso llega es si la frase
que escribe un padre casa, y eso sólo se sabe escribiendo la frase. Vale igual fuera del triaje:
presencia no es cobertura en ninguna parte.

## L173 · La negación puede SER la señal (17-sep-2026)
El triaje anula una alarma cuando ve una negación justo delante: «sin fiebre» no es fiebre, y esa
regla arregló un fallo real en septiembre. Pero hay señales que **son** una negación: «sin pis
desde ayer», «не может дышать», «no responde». Ahí el guardián apagaba justo lo que había que oír.

El mecanismo ya tenía la salvedad —si la coincidencia empieza por una negación, cuenta— y por eso
«no responde» funcionaba. Lo que fallaba era el otro lado: el patrón estaba escrito sin la
negación («pis», «дышать»), así que la coincidencia empezaba después de ella y el guardián la
comía. **Cuando la negación es parte de la señal, tiene que estar dentro del patrón.**

## L174 · Una manera de decirlo no es cobertura; tres empiezan a serlo (17-sep-2026)
Medido en el mismo día, con las mismas 51 reglas y las mismas ocho lenguas:

    una frase por regla        72 huecos de 408   (18 %)
    la misma, tecleada deprisa 23 de 174          (13 %) — 17 de ellos árabes
    dicha de otra manera      121 de 408          (30 %)
    el mensaje corto del móvil  7 de 80           ( 9 %)

La tercera medida es la que más encontró, y se hizo cuando las reglas ya estaban «cubiertas en
los ocho idiomas». Lo que faltaba no eran lenguas: eran MANERAS. «Está doblado del dolor» no
estaba en ninguna de las ocho, y es como se cuenta un abdomen agudo en cualquier casa.

**La regla**: una batería con una frase por caso mide que el camino existe, no que esté abierto.
Para creerse una cobertura hacen falta varias maneras de decir lo mismo — y la caída del 30 % al
9 % entre la tercera medida y la cuarta es la única señal fiable de que se está cerrando.

## L175 · Después de ensanchar, medir por dónde se sale (17-sep-2026)
En un día metí 863 patrones nuevos en el triaje, todos buscando avisos que faltaban. La medida
que faltaba era la contraria, y encontró ocho falsos positivos en treinta y ocho frases escritas
a propósito para engañar a las reglas nuevas. Seis eran mías de ese mismo día.

Los dos más instructivos no eran de sentido sino de **frontera de palabra**: «a **bit** of shampoo
in his eye» disparaba una mordedura de animal, y «the **bat**h» aportaba el murciélago; y al
arreglarlo, «a bit of **the** biscuit fell in the bath» disparó un casi ahogamiento, porque «the»
contiene «he» y eso bastaba para dar por hecho que quien se caía era el niño.

**La regla**: un patrón nuevo se prueba dos veces, con la frase que debe cazar y con la frase que
se le parece. Y en inglés, cualquier alternancia de palabras cortas —he, bit, bat, us, uk— sin
`\b` es una trampa esperando: esas letras viven dentro de palabras corrientísimas.

Y la segunda mitad de la lección: **un aviso que salta de más hace dos daños**. Manda a urgencias
a quien no lo necesita, y enseña al padre a ignorar el rojo — que es el que algún día será de
verdad. Por eso cada regla nueva entra con sus controles negativos escritos a la vez.

## L176 · La señal no basta: hay que leer el marco (17-sep-2026)
Doce medidas del triaje preguntaban por la señal —¿reconoce «convulsión» en ocho lenguas, escrito
de cuatro maneras?— y ninguna preguntaba por el marco. La misma señal significa cosas contrarias
según el tiempo y el modo:

    «está convulsionando»                 emergencia
    «tuvo una convulsión hace dos años»   un antecedente que el padre cuenta de paso
    «¿qué hago si le da una convulsión?»  una pregunta que se hace cuando NO está pasando

De 31 frases de ese tipo, 20 salían mal. El condicional disparaba el aviso rojo en las nueve
lenguas probadas: un padre que pregunta «¿qué hago si se atraganta?» y recibe un «llama al 112
ahora» aprende en un segundo que el rojo de esta web no significa nada.

**La regla**: un detector de palabras no entiende cuándo pasó algo ni quién lo cuenta, y hay que
dárselo escrito. Los guardianes —negación, prevención, información, condicional, pasado— son tan
parte del triaje como las reglas, y necesitan sus propias pruebas en los dos sentidos: que callen
lo que no está pasando y que NO callen lo que sí.

Y el corolario caro: **cuando falla un guardián, el fallo es un silencio**. Dos de los míos
callaron avisos de verdad por una frontera de palabra —«il y a du sang dANS son vomi» parecía «il
y a dos años», «no puede bEBEr» parecía «de bebé»— y un silencio no se ve en ninguna pantalla.

## L177 · Un nombre de país es una palabra de otro idioma (18-sep-2026)
Para que un padre pueda preguntar «¿qué vacunas le tocan en Nigeria?», el bot lee el nombre del
país dentro de la frase. Con trece países eso era una lista de subcadenas y funcionaba. Con
sesenta y uno —África entera— la lista se convirtió en una trampa, porque **el nombre de un país
en un idioma es una palabra corriente en otro**:

    «Gana»   es Ghana en portugués… y el verbo de «mi bebé no gana peso», que es la frase más
             repetida de este proyecto. Un padre español preguntando por el peso de su hijo
             habría recibido el calendario vacunal de Ghana.
    «того»   es Togo en ruso y también el genitivo de «тот»: «вместо того чтобы…».
    «чад»    es Chad en ruso y también el humo que se respira en un incendio: «ребёнок вдохнул
             чад» es una consulta de urgencias de verdad.
    «mali»   está dentro de «maligno», «maligne» y «malignant».
    «niger»  está dentro de «Nigeria».
    «guinea» está delante de «pig»: el conejillo de Indias.
    «гана»   está dentro de «органа», genitivo de «орган».

La lista de subcadenas no distingue nada de eso. Tres arreglos distintos para tres problemas
distintos, y conviene no confundirlos: los que viven **dentro** de otra palabra se arreglan con
frontera de palabra (`\bmali\b` no casa en «maligno»); los que son **la misma palabra** no se
arreglan con nada y hay que quitarlos («gana», «того»); y los que dependen de lo que viene detrás
se arreglan mirando detrás (`\bguinea\b(?!\s*pig)`).

**La regla**: antes de meter un nombre propio en un buscador de subcadenas, pregúntate qué
significa esa secuencia de letras en los otros siete idiomas del sitio. Y la prueba que lo sujeta
no es «el país está en la tabla», que es lo que comprobaba la vieja, sino **«el país contesta a
cada uno de sus nombres y no contesta al de otro»**: 61 países por todos sus nombres, y Guinea
Ecuatorial no puede leerse como Guinea.

## L178 · Publicar un hueco es publicar un dato (18-sep-2026)
La prueba decía: todo país con calendario tiene que tener número de emergencias, porque publicar
un calendario es una promesa de estar ahí. En Europa esa regla no tenía grietas. En África sí:
en la RD del Congo, el Congo, Gambia, Guinea, las Comoras, Liberia y Sudán del Sur **la fuente
dice con todas las letras que no existe un número nacional**, y en Zambia no hemos podido
verificar ninguno.

Tres salidas, y dos son malas. Callar esos ocho países sería fingir que no existen, justo los
ocho donde un padre tiene menos a mano un pediatra. Ponerles un 112 de relleno sería mandarlo a
esperar una ambulancia que no va a venir. La tercera es publicar el hueco **con su motivo y con
la frase de la fuente**, y distinguir «no lo hay» de «no lo sabemos», que no son lo mismo: el
padre que lee «no hay número» sale hacia el hospital, y el que lee «no lo hemos podido
verificar» sabe que le toca preguntar.

**La regla**: cuando el dato no existe, el dato es que no existe — y entonces la prueba se hace
más dura, no más blanda. Un país sin número tiene que traer *por qué*, o sigue siendo un hueco.

## L179 · Una ficha que existe no es un dato que exista (18-sep-2026)
Repasando lo de África con las lecciones viejas en la mano apareció el peor fallo del día, y no
estaba en los datos nuevos sino en el código que los lee. Ocho países tienen ficha de emergencias
y no tienen número: `emergency` es `None`. Las plantillas del aviso rojo meten esa casilla en una
f-string sin preguntar, y `f"{None}"` es «None»:

    💛 This matters and you are not alone. Call None. If your child has already done something
       to harm themselves, go to the emergency department now.

Eso leía un padre de Kinshasa que acababa de escribir que su hijo quiere morirse. Tres caminos lo
hacían —el aviso de emergencia, el de salud mental y la lectura de una foto, que además pasaba
por `str()` y por eso ni siquiera podía fallar—.

**La regla**: al añadir un estado nuevo a un dato —«este país no tiene número»— hay que ir a
buscar a todos los que lo leen, no sólo a los que lo escriben. La ficha existía, el diccionario
era «verdadero», la comprobación `if found:` pasaba, y el agujero estaba una capa más abajo, en
una interpolación que no pregunta nada. Se busca con `grep` por el nombre del campo, uno por uno,
y cada sitio decide qué escribe cuando no hay dato.

Y el corolario: **lo que se escribe cuando no hay dato no puede ser el silencio**. Un aviso que
se calla por prudencia deja al padre igual de solo. Donde no hay número se escribe la única
instrucción que sirve: ve al hospital o centro de salud más cercano, ahora.

## L180 · El nombre de un país dentro de una palabra de todos los días (18-sep-2026)
L177 se escribió esta misma mañana por «Gana», que es Ghana en portugués y el verbo de «mi bebé no
gana peso». Al aplicar esa lección hacia atrás —a lo que ya estaba puesto— salieron cuatro que
llevaban meses en producción:

    «catar»  dentro de «catarro» y de «se acatarra»
    «inde»   dentro de «Windeln», que es «pañales» en alemán
    «usa»    dentro de «causa», «usar» y «no usa el orinal»
    «riad»   dentro de «resfriado»

El golden tiene una frase de deshidratación —«sie macht kaum Windeln nass», apenas moja pañales—
que se leía como si dijera India. «Mi hija no usa el orinal» daba Estados Unidos. «Mi hijo tiene
catarro» daba Catar.

Tres arreglos distintos para tres problemas distintos, y conviene no confundirlos. Lo que vive
**dentro** de otra palabra se acota con frontera de palabra. Lo que **es** otra palabra —«usa» en
español— no se arregla con ninguna frontera: se distingue por las mayúsculas, y para eso hay que
dejar de bajar el texto a minúsculas antes de mirarlo. Y lo que depende de lo que viene detrás
—«guinea pig»— se mira detrás.

**La regla, y esta es la que importa**: una lección nueva se aplica hacia atrás el mismo día. La
escribí por 48 países nuevos y el fallo llevaba meses en los trece viejos. Y la señal es
mecánica, no hace falta adivinarla: si el nombre casa con una letra pegada delante o detrás, no
se ha leído un país. Eso ahora es una prueba, y la primera versión de esa prueba **pasaba con el
fallo puesto** porque el corpus no contenía la palabra «catarro» — una revisión que nunca ha
fallado no está probada (L146).

## L181 · La cuenta que hace una madre con un reloj (18-sep-2026)
Fase 2 de África. Medido antes de escribir nada: de 41 frases con las que un padre africano
cuenta lo que mata niños en su continente, **29 salían mal**. La palidez palmar —el signo de
anemia grave del IMCI, que se mira en la palma porque ahí se ve sin depender del color de la
piel— no existía en ninguna de las ocho lenguas. «Diarrea como agua de arroz» tampoco. Y el
paludismo con un niño somnoliento se quedaba en urgente.

Lo que enseñó esta tanda no es que faltaran reglas, sino **de qué clase era lo que faltaba**:

Contar las respiraciones de un niño durante un minuto es la herramienta del IMCI donde no hay
radiografía ni pediatra, y **no se puede escribir como un patrón**, porque lo que decide no es el
número sino el número contra la edad: 60 en un recién nacido es normal y 45 en un niño de tres
años no lo es. Eso es una cuenta, y va en Python como va la dosis de paracetamol. Un triaje
hecho sólo de expresiones regulares no puede leer lo que un padre sabe medir.

Y la segunda mitad, la de siempre: al medir por dónde se salía, **catorce de treinta y cuatro
trampas saltaban de más**, y la peor era «le di agua de arroz para la diarrea» — que es un padre
haciendo exactamente lo que la OMS recomienda, recibiendo una alarma de cólera. Lo que separa el
síntoma del remedio es una palabra: «COMO». La caca *parece* agua de arroz; el agua de arroz se
*da*. Sin esa palabra en la regla, estábamos mandando a urgencias a quien lo estaba haciendo bien.

**La regla**: antes de escribir una regla nueva, pregúntate si lo que vas a reconocer es una
palabra o una medida. Y después de escribirla, pregúntate qué hace un padre que lo está haciendo
bien y usa esas mismas palabras.

## L182 · Una palabra tecleada con el alfabeto equivocado no falla: deja de encontrar (18-sep-2026)
Dentro de la regla del sarampión se me coló esto:

    ...|boca|mouth|bouche|mund|рот|фم|फम|مुँह|मुँह|مुंह)

«فم» es «boca» en árabe, y ahí estaba escrito dos veces mal: una con letras cirílicas y otra con
devanagari. Ninguna de las dos es una palabra de ninguna lengua. Y el mejor ejemplo apareció
después: `मल`, que parecía el «heces» hindi y era **devanagari MA + árabe LAM**, invisible a
simple vista incluso sabiendo que había algo raro.

Una alternativa así no rompe nada. La regla carga, el YAML es válido, las pruebas pasan y el
patrón entero sigue funcionando para las demás lenguas. Sólo hay un padre, en un idioma, que deja
de recibir su aviso — y eso no se ve en ninguna pantalla.

**La regla**: una alternativa no puede mezclar dos alfabetos. Es mecánico, se comprueba solo, y
ahora lo comprueba una prueba. Misma familia que L164 y que el `\b` que no existe en devanagari:
el código da por hecha la forma de una lengua que no es la suya, no falla, y sólo deja de
encontrar.

## L183 · Una lengua entra por la capa de seguridad, no por la web (18-sep-2026)
Fase 3 de África: el suajili, que hablan más de doscientos millones de personas en Kenia,
Tanzania, Uganda y el este del Congo. La pregunta no era «¿lo traducimos?» sino **por dónde
empieza una lengua nueva**, y la respuesta ya estaba escrita en el propio detector de idioma
desde que existe:

> «A language only joins here once it has its own triage patterns: guessing the language of a
> message the safety layer cannot read is worse than defaulting to English.»

Así que primero las 83 reglas del triaje, después el detector, y sólo entonces lo demás. Medido
antes: de diez frases de urgencia en suajili, **cero** disparaban nada.

Y al llegar arriba apareció la decisión de verdad. Poner el suajili en `SUPPORTED_LANGS` hizo
saltar **45 candados**: la web en suajili, las guías en suajili, el golden, los nombres de los
fármacos, las preguntas de arranque. El proyecto estaba diciendo, correctamente, lo que cuesta
una lengua completa. Pero el corpus no tiene **ni un documento en suajili** con licencia abierta,
así que una respuesta «completa» en suajili habría sido una respuesta sin fuentes que citar, que
es justo lo que este proyecto no hace (L147, L167).

La salida no fue ni traducirlo todo ni dejarlo fuera, sino **partir el idioma en dos**: el del
aviso y el de la respuesta. El triaje lee suajili y el aviso rojo se escribe en suajili —que es
la parte que dice qué hacer y la que no puede llegar tarde—, y la explicación larga sale en
inglés, con fuentes que el lector puede abrir, hasta que haya material que citar.

**La regla**: cuando una lengua nueva no cabe entera, lo que entra primero es lo que salva vidas
y lo que se queda fuera se escribe en el código con su motivo. Y el candado que se interponga no
se silencia: se le enseña la categoría nueva, para que siga cazando al que se olvide de un bloque
sin pelearse con una decisión tomada a propósito.

## L184 · En suajili lo que cambia es el principio de la palabra, y el posesivo se mete en medio (18-sep-2026)
El suajili entró ayer con una frase por regla, que es exactamente lo que L174 llama insuficiente.
Al escribir la segunda forma de decir lo mismo saltaron **catorce huecos de 83**, y la causa se
repetía en casi todos:

    «mwili unatetemeka»          el patrón · el cuerpo tiembla
    «mwili WAKE unatetemeka»     lo que escribe una madre · su cuerpo tiembla
    «ana homa, miguu baridi»     el patrón
    «ana homa lakini miguu NI baridi»   lo que escribe una madre

Dos cosas que ninguna de las otras ocho lenguas hace igual:

1. **El posesivo va detrás del sustantivo y parte la pareja**: «uso wake umevimba», «kiganja
   chake kimepauka». Un patrón que pide las dos palabras pegadas no casa nunca.
2. **El tiempo verbal vive en el PRINCIPIO del verbo**, no en el final: `ame-`gonga (ha
   golpeado), `aka-`gonga (y golpeó), `ali-`gonga (golpeó), `ka-`meza (se lo tragó). Escribir
   «amegonga» cubre un tiempo de cuatro, y la narración de un accidente —que es como se cuenta
   un golpe en la cabeza— usa justo los otros.

**La regla**: al abrir una lengua, lo primero que hay que preguntarle no es su vocabulario sino
**por dónde flexiona**. En castellano y en inglés cambia el final y se cubre con `\w*`; en árabe
se pega el artículo delante (L138); en devanagari la vocal cuelga y rompe `\b` (L164); y en
suajili cambia el prefijo del verbo y se cuela el posesivo. Cada familia rompe los patrones por
un sitio distinto, y el sitio se sabe antes de escribir el primer patrón.

## L185 · El aviso en la lengua que no es deja media urgencia sin resolver (18-sep-2026)
Verificando el suajili en vivo apareció esto: «paka amemuuma mkononi» —le ha mordido el gato—
disparaba la alarma correcta **y la escribía en inglés**. La regla funcionaba; el detector de
idioma no reconocía la frase. Media urgencia bien resuelta no sirve de nada a las tres de la
mañana.

Al medirlo en las nueve lenguas se vio que no era cosa del suajili: **120 de 1.408 frases salían
con el idioma equivocado, y el portugués al 31 %**. «O recém-nascido parou de mamar e está
rígido» recibía el aviso en castellano.

Dos cosas que enseñó el arreglo:

1. **Las marcas de idioma se calculan, no se inventan.** Para cada lengua se buscan las palabras
   que aparecen en SUS frases mal detectadas y en las de ninguna otra: eso es una marca buena por
   construcción, porque si sólo existe en portugués no puede robarle una frase al francés. Tres
   vueltas de ese cálculo llevaron de 120 a 21.
2. **Pero el cálculo no ve lo que el corpus no tiene.** «Pile» salió como marca francesa
   excelente y es también una palabra inglesa; «dolor» es igual en castellano y en portugués.
   Esas se quitan a mano, y por eso el método es medir **y luego mirar**, no medir y confiar.

Y la trampa de fondo, que es la misma de siempre: **una prueba que mira una muestra pasa con el
fallo dentro**. La del detector suajili miraba veinte frases de 186 y estaba verde con 21 sin
reconocer. Se mide todo o no se mide.

**La regla**: una lengua no está soportada cuando sus reglas saltan, sino cuando el aviso llega
escrito en ella. Y el candado que lo sujeta no exige cero —hay frases cortas que el portugués y
el castellano comparten enteras— sino **no empeorar**, con el número de hoy escrito al lado.

## L186 · Un prefijo de pasado no es un pasado remoto (18-sep-2026)
Los guardianes del triaje —negación, prevención, información, condicional, pasado— estaban
escritos en las ocho lenguas y en suajili no había ninguno. Medido: de 26 frases de lo que NO
está pasando, **7 daban alarma**, y cinco eran el aviso rojo de convulsión. Un padre que pregunta
«degedege la homa ni nini» —qué es una convulsión febril— recibía «llama ya».

Al escribirlos aparecieron dos cosas que ninguna de las otras ocho lenguas hace:

**El marco va al final.** «Degedege la homa NI NINI», «dalili za meningitis NI ZIPI». Todos los
guardianes miran la ventana ANTERIOR a la señal, porque en castellano, inglés, francés, alemán,
ruso, árabe, portugués e hindi el «cómo evitar» y el «cuáles son» van delante. En suajili no, y
por eso ahí no veían nada.

**Y el error que costó caro**: metí el prefijo del pasado «ali-» en el guardián del pasado
remoto, por analogía con el «hace dos años» castellano. Está mal. **«Ali-» no marca distancia**:
es el pasado de cualquier cosa que ya ocurrió, incluido lo de hace cinco minutos. Con él dentro,
«ALIanguka akagonga kichwa na akapoteza fahamu» —se cayó, se golpeó la cabeza y perdió el
conocimiento— dejó de dar alarma, y «ALIkuwa kwenye moto na anakohoa» también. Dos emergencias
silenciadas por un guardián de más, y las cazó la batería que ya existía, no yo.

**La regla**: un guardián nuevo se mide en los dos sentidos **el mismo día**. Lo que calla de
más no se ve en ninguna pantalla —cuando falla un guardián el fallo es un silencio (L176)— y la
única defensa es que la batería de lo que SÍ tiene que saltar se ejecute justo después. Y la
regla de fondo: lo que en una lengua marca distancia en el tiempo puede no marcarla en otra;
antes de traducir un guardián hay que preguntarse qué significa de verdad la pieza gramatical
que se está copiando.

## L187 · La negación de cada lengua va en un sitio distinto, y el guardián no lo sabe (18-sep-2026)
Midiendo las reglas africanas en las cuatro lenguas que faltaban apareció, de rebote, esto:

    er kann nicht atmen        →  RUTINA

«No puede respirar», en alemán, la frase más urgente que un padre puede escribir. Y con ella «er
kann nicht atmen und wird blau».

La causa es la misma de L173 vista por el otro lado. El guardián de la negación tiene una
excepción escrita a propósito: **no cuenta la negación que forma parte de la propia coincidencia**
—«no puede respirar», «cannot breathe», «ne peut pas respirer» empiezan por ella y siguen
saltando—. Pero eso sólo funciona si el patrón la lleva dentro, y en alemán el verbo se va al
final: el patrón casaba «atmen», la negación quedaba fuera, delante, y el guardián la callaba.

Al barrer esa familia en las cuatro lenguas que colocan la negación de otra manera salieron tres
más: «sie trinkt nichts mehr», «لا يستيقظ» (no se despierta) y «الدم لا يتوقف» (la sangre no
para). Cuatro emergencias mudas, en cuatro lenguas, y ninguna se veía en ninguna pantalla.

**La regla**: cuando una regla necesita la negación para significar lo que significa, el patrón
tiene que llevarla DENTRO, en cada lengua y con el orden de esa lengua. Y hay que ir a buscarlo a
propósito: las cuatro salieron de un barrido de una tarde, no de un informe.

Y el corolario que costó dos idas y venidas: **al escribir esos patrones se ensancha una regla, y
el candado de densidad avisa de que las otras escrituras se han quedado cortas**. Hacerle caso es
el trabajo, no el obstáculo: al escribir el ruso y el hindi del «no toma nada» apareció que «खाना
छोड़ दिया» —ha dejado de comer— es el trastorno alimentario de una adolescente y no el signo de
peligro de un lactante. Dos alarmas distintas en la misma frase, y sólo se ve escribiéndola.

## L188 · El apóstrofo se cae al escribir deprisa, y el francés entero lo daba por seguro (18-sep-2026)
Verificando contra la web lo que acababa de arreglar, escribí la frase francesa **sin apóstrofo**
—«la plaie ne sarrete pas de saigner»— porque es como se teclea en un móvil. No saltó nada. Ni
eso ni «il setouffe», que es «se está ahogando».

Es la misma familia que la hamza árabe que `aplana` normaliza desde el 17-sep (L138) y que el
nuqta devanagari: **lo que se cae al escribir deprisa**. En francés se cae el apóstrofo de la
elisión, que está en casi todas sus frases de urgencia: «s'étouffe», «n'arrive pas», «ne
s'arrête pas», «l'os».

Y no se podía arreglar donde se arregló el árabe. `aplana` se aplica al texto **y a los
patrones**, y quitarle el apóstrofo a un patrón inglés como `can(?:'?t| ?not)` lo convierte en
`can(?:?t| ?not)`, que es una expresión regular inválida. Se arregla en el otro sitio: haciéndolo
opcional —`s'?`— en los 81 patrones que lo llevaban obligatorio.

**La regla**: cada escritura tiene su carácter que se cae, y hay que ir a buscarlo a propósito.
El árabe pierde la hamza, el devanagari el nuqta, el castellano y el francés las tildes, el
francés además el apóstrofo, y el alemán convierte la diéresis en dos letras. Lo que se cae nunca
está en la frase de ejemplo que uno escribe: aparece cuando se prueba **escribiendo como escribe
un padre a las tres de la mañana**, sin teclado cómodo y con una mano.

## L189 · Un desplegable sin opción vacía elige por el lector, y eligió Emiratos (19-sep-2026)
Repasando lo desplegado el día en que el proyecto se presenta en MetaDAO, miré el selector de
país de la portada:

    <select id="country"><option value="AE">AE</option><option value="AO">AO</option>…

Dos averías en la misma línea. La que se ve: los códigos ISO pelados, de manera que para elegir
España había que saberse la sigla. La que no se ve y es la grave: **sin opción vacía, un
`<select>` viene con la primera elegida de fábrica**, y esa era AE por orden alfabético del
código. Ese valor viajaba en cada pregunta de quien no lo tocaba, que es casi todo el mundo.

Medido contra producción, en castellano, con «mi bebé de 6 meses tiene los labios azules y no
responde»:

    país AE (el de fábrica) → «🚨 Llama ahora al 998 / 999»   ← Emiratos
    sin país                → «llama al número de tu país (112 en la UE, 911 en América)»
    país ES                 → «🚨 Llama ahora al 112»

Un padre en Madrid recibía un teléfono del Golfo, en rojo y en grande. Y el proyecto llevaba
semanas cuidando de que el número fuera exacto en 88 países: el fallo no estaba en el dato, sino
en **quién decidía a qué país mirar**.

**La regla**: en este proyecto, un valor que el lector no ha elegido no es un valor. El
desplegable abre vacío, la frase general vale en cualquier sitio, y lo que se deduce del
navegador se enseña **como lo que es**, con la manera de corregirlo al lado. Lo mismo valía para
la tarjeta de «Tu país» de la portada, que presentaba una suposición guardada en el navegador con
la misma cara de certeza que una elección: el operador entró y leyó que su país era Colombia.

## L190 · Una regla de CSS dentro de otra no da error: sólo borra el estilo (19-sep-2026)
En el generador de las páginas de emergencias había esto, desde el día que se escribió:

    .ncard b {
    .ncard b.sin { color: var(--ink-3); font-weight: 600; }
      font-family: 'JetBrains Mono', ui-monospace, monospace; color: var(--coral);
    }

El sitio construye sin una queja, porque el minificador lo entiende como CSS anidado y escribe
`& .ncard b.sin`, un selector que no casa con nada. Lo que se perdía: los ocho países cuya fuente
dice que **no hay número nacional** enseñaban su raya en el mismo coral y la misma tipografía que
un teléfono de verdad, o sea, lo contrario de lo que esa clase existía para decir.

No se ve leyendo el código —la llave descuadrada no descuadra nada, la regla intrusa está
completa— y no se ve mirando la página, porque hay que saber que ocho países de ochenta y ocho
tenían que verse distintos.

**La regla**: aquí no se anida CSS. Cualquier regla dentro de otra que no sea una arroba
(`@media`, `@supports`, `@keyframes`) es este fallo otra vez, y lo comprueba
`test_no_style_block_is_left_open.py` en los 161 bloques `<style>` del sitio. Antes de darla por
buena, la prueba se ejecutó contra el fallo reintroducido a propósito: si no falla con el fallo
puesto, no vale.

## L191 · Una prueba que comparte la suposición del código no comprueba nada (19-sep-2026)
Construyendo la curva de crecimiento de cada hijo hizo falta un extremo nuevo, `/api/growth/bands`,
que devuelve las cinco bandas de percentiles de la OMS para poder dibujarlas. Se escribió con su
prueba, y la prueba decía esto:

    for meses, p50 in zip(datos["ages"], datos["bands"]["p50"]):
        _, m, _ = tablas.lms("wfa_f", meses)     ← la misma tabla, con la misma unidad
        assert p50 == pytest.approx(m)

Pasaba. Y estaba mal: **las tablas de la OMS de 0 a 5 años están indexadas en DÍAS**, no en
meses —de eso se encarga `assess`, que multiplica por 30,4375 antes de buscar—, y el extremo
nuevo les pasaba meses. El P50 a los 18 meses salía **3,72 kg**, que es el peso de un bebé de
dieciocho DÍAS. La prueba no lo vio porque preguntaba a la misma tabla con la misma unidad
equivocada: comparaba el error consigo mismo.

Tampoco lo vio la curva dibujada, y eso es lo más instructivo: como el gráfico reescala el eje
vertical a lo que recibe, una curva que iba de 3,23 a 3,95 kg en cinco años **se veía
perfectamente normal**. Lo cacé leyendo la cifra suelta en la consola después de desplegar.

**La regla**: cuando lo que se comprueba es una conversión —de unidad, de escala, de formato—, la
prueba tiene que traer el valor **de fuera**. Ahora compara contra las medianas publicadas por la
OMS (una niña pesa 8,9 kg al año, un niño mide 87,1 cm a los dos), que cualquiera puede verificar
sin abrir este repositorio, más un candado tonto que dice que el peso a los cinco años tiene que
ser al menos cuatro veces el del nacimiento. Las dos habrían fallado con el fallo puesto.

## L192 · Un despliegue que termina en «done» no quiere decir que haya desplegado (19-sep-2026)
Al añadir un paso previo al build del sitio —copiar los datos que la web guarda para funcionar
sin cobertura—, el despliegue imprimió esto en medio de sus veinte líneas:

    Error: Cannot find module '/opt/pedibot/web/site/scripts/publish-offline-data.mjs'
    SMOKE-FIN fallos=0
    DOCTOR-FIN problemas=0
    == done: https://pedibot.xyz

Dos fallos encadenados, y el segundo es el que enseña algo. El primero, tonto: la carpeta nueva
no estaba en la lista de lo que el `tar` sube al servidor. El segundo: la orden que construye el
sitio acababa en `| grep -E "page(s)|rror"`, **así que el código de salida era el del grep**, no
el del build. El servidor se quedó con el sitio de antes, la prueba de humo pasó —porque el
sitio viejo funciona perfectamente— y el despliegue llegó hasta «done» tan contento.

Lo peor no es que fallara: es que **fallar y no fallar se veían igual**. La única diferencia era
una línea de error entre otras veinte, y el despliegue de un proyecto que se despliega cinco
veces al día no se lee línea a línea.

**La regla**, que es la L33 otra vez por otro lado: cuando una orden importante acaba en una
tubería, el código de salida es el del último tramo. O `set -o pipefail`, o el fallo es mudo. Y
cuando el fallo significa «lo que hay desplegado sigue siendo lo de antes», hay que decirlo con
esas palabras y parar, no seguir hasta el «done».

## L193 · Un campo de menos de 16 px amplía la página entera en un iPhone (19-sep-2026)
Puliendo para el móvil la pantalla de la cuenta, recién escrita, salió un fallo que estaba en
todo el sitio y que no se ve desde un ordenador: **Safari en iOS hace zoom sobre toda la página
cuando enfocas un `input`, `select` o `textarea` cuyo texto mide menos de 16 px**. Es su manera
de decir «esto no se lee». Lo que nota quien escribe es que la página se agranda sola, se
descoloca, y al salir del campo se queda así.

Medido antes de tocar nada, había once por debajo, y todos son campos que se tocan con el dedo:

    13,4 px  el selector de país de la portada
    14,4 px  la herramienta de vacunas
    13,8 px  el buscador de guías, en las ocho lenguas
    13,6 px  la ficha de los hijos, escrita ese mismo día

Ninguno estaba puesto a mano: todos heredaban de su etiqueta, que es pequeña a propósito
—`font-size: .85rem` en el contenedor y `font: inherit` en el campo—, que es justo el patrón que
uno escribe sin pensar.

**La regla**: el tamaño de un campo no se hereda de su etiqueta. Se arregla una vez, en el CSS
global y bajo `@media (pointer: coarse)`, que es el dedo: con ratón el diseño no cambia. Y como
un componente nuevo puede fijarle a su campo un tamaño propio y saltarse la regla general, la
prueba vuelve a medir los bloques `<style>` de los 161 componentes en vez de mirar sólo que la
regla exista.

## L194 · El CSS de un componente no alcanza lo que pinta JavaScript (19-sep-2026)
El operador mandó pantallazos de la ficha de su hijo y se veía tosca: las etiquetas pegadas a los
campos, las medidas sin rejilla, las dos curvas ocupando media pantalla. Yo lo leí como una queja
de tamaño —«las curvas podrían ser más pequeñas»— y el tamaño era lo de menos.

**Astro limita el CSS de cada componente al HTML que escribe él**: pone un `data-astro-cid-…` en
cada etiqueta de la plantilla y reescribe los selectores para que sólo casen con eso. Las fichas
de los hijos las pinta el navegador con `innerHTML`, así que nacen sin ese atributo. Medido en lo
construido: **cero reglas** para `.kid`, `.medidas`, `.vacunas`, `.curva`, `.rejilla` y `.f`. La
pantalla no estaba mal diseñada; estaba sin diseñar.

Lo que más escuece: ya estaba escrito en este repositorio. `Chat.astro` usa `:global(...)` para
las burbujas y lleva su comentario explicando por qué, de cuando pasó lo mismo con la tarjeta de
temporada. Lo tenía delante y escribí el componente nuevo sin acordarme.

**La regla**: si la etiqueta se crea en el `<script>`, su estilo va en `:global(...)`; si está en
la plantilla, no. Y como esto no da ningún error —se ve mal y ya está—, lo comprueba
`test_the_styles_reach_what_javascript_draws.py`, que por cada clase que sólo existe dentro de un
`<script>` exige una regla en el CSS construido.

## L195 · Lo que el operador no entiende de su propia web, un lector no lo pregunta (19-sep-2026)
Leyendo el pie de su sitio: «¿qué es eso de llms.txt?». Es un mapa del proyecto escrito para los
asistentes que contestan preguntas de salud, y llevaba semanas en el pie de las 2.600 páginas,
entre «Bluesky» y «Fuentes», con su nombre de fichero por toda explicación.

Si lo pregunta quien paga el servidor, un padre no lo pregunta: lo lee, no entiende nada y sigue.
Y cada línea que no se entiende gasta un poco de la confianza que la página necesita para que
alguien se crea lo demás.

No se borró, porque el candado que lo protege existe por un motivo medido —estuvo huérfano
treinta días y ningún rastreador lo visitó, porque el rastreo sigue los enlaces—. Se mudó a
`/sources`, que es la página de «de dónde sale esto», con una frase delante que dice lo que es.
El candado se reescribió para defender **que el enlace exista**, no dónde está: una prueba que
fija el sitio exacto impide justamente esta clase de arreglo.

## L196 · Una cifra contada del fichero parecido está tecleada, no contada (19-sep-2026)

El memo de una página se escribió con la regla de siempre: ningún número a mano, todos contados
al construir de los ficheros de los que vive el sitio. Salió con tres mal a la vez.

Las reglas de alarma las contaba en `checklist.json`, que es otra cosa y tiene cinco claves: el
memo anunciaba **5 reglas** donde hay 83. Los documentos los contaba en el catálogo interno del
sitio, que lleva tres que no se pueden redistribuir: **499** donde todo lo demás dice 496, tres
que nadie podría ir a comprobar. Y «48 African countries» estaba escrito a mano, que era la única
cifra tecleada de todas y por eso la única que se había quedado vieja: son 49.

Contar no es leer un fichero con el nombre adecuado. Es leer **el mismo fichero del que lo lee
quien lo afirma fuera**, y si hay dos copias parecidas, decidir cuál es la que se cita y atarlas
con una prueba. Aquí el catálogo público y su copia en `public/` se comparan ahora en un test,
porque el memo cuenta de una y la respuesta de financiación cita la otra.

## L197 · Un despliegue que dice «manda lo mío» resucita lo que el servidor ya había enterrado (19-sep-2026)

El publicador hace lo correcto: al regenerar una guía con mejor título, redirige la dirección
vieja y borra el fichero viejo. En el servidor. Y `deploy.sh --no-pull` significa «la copia local
manda», así que en cada despliegue volvían a subir los ficheros que el servidor había retirado
semanas antes. Uno detrás de otro, hasta **61**.

No se vio nunca porque la redirección gana: quien abría la dirección vieja llegaba bien a la
nueva. Lo que salió torcido fue el recuento, que no lo mira nadie hasta que se usa fuera. La web
decía 568 guías y las que un lector podía abrir eran 507, y esa cifra ya estaba escrita en una
solicitud de financiación.

Lo cazó el memo: como cuenta del directorio del servidor al construirse allí, dijo 568 donde el
texto decía 502, y al ir a cuadrarlos apareció lo otro. Una cifra que se calcula sola en dos
sitios distintos es un careo permanente; una escrita a mano no discute con nadie.

La regla queda en el despliegue y no sólo en un test: un fichero de guía cuya dirección está
redirigida está muerto por definición y se retira **antes de subir**, porque el test mira esta
copia y lo que importa es lo que sale hacia el servidor.

## L198 · Enseñar una cifra cierta de forma que parezca que escondes el resto (19-sep-2026)

La solicitud decía, y es verdad, «las cifras de uso están publicadas en /api/stats». Quien abría
esa dirección veía `{"days":7,"answers":2}`: dos respuestas del chat en siete días, justo encima
de otra respuesta que hablaba de 337 visitantes.

Las dos cifras eran ciertas. El chat es una herramienta de siete, y lo que la gente abre son los
calendarios, las urgencias y las curvas, donde no hay nada que preguntar. Pero el enlace se daba
como prueba, y lo que probaba era lo contrario de lo que decía el texto.

Un enlace de «compruébalo tú mismo» que enseña la peor mitad de la verdad cuesta más que no
enseñar nada: el lector no concluye «esto es una parte», concluye «me han contado lo bueno». Se
arregló por el lado bueno, que es que el contador enseñe también las visitas, en vez de por el
cómodo, que era cambiar la frase.

## L199 · El nombre de un país vive dentro de una palabra que un padre dice llorando (20-sep-2026)

Al añadir el norte de África, «sudan» entró en la tabla de países que se reconocen por
subcadena, que es donde ya vivían «egipto» y «marruecos» sin dar problemas. El candado saltó en
el acto: **«sudan» casa dentro de «sudando»**, y esa palabra está en una regla de alarma de
diabetes, «sudoroso, sudando, con sed». Un padre contando que su hijo suda se leía como si
hubiera dicho Sudán, y se le habría contestado con el calendario de vacunas sudanés.

«oran», por Orán, vivía dentro de «llorando», de «piorando» y del «malodorant» francés.

Es la familia del «ni» suajili y del «catar» dentro de «catarro», con una diferencia que vale la
pena anotar: **aquel salió a producción y éste no salió de la máquina**. La prueba genérica que
compara cada nombre contra el corpus entero ya existía, y lo que hizo fue exactamente su trabajo.

Lo que se aprende no es «cuidado con Sudán». Es que **una tabla que funciona para veinte países
no está validada para el veintiuno**, porque lo que decide no es la tabla, es cómo suena ese
nombre en las otras siete lenguas del sitio. Cada nombre nuevo se mide contra el corpus antes de
entrar, y el que no pasa baja a la tabla de frontera de palabra. Nunca se quita el país.

## L200 · Un dato importado trae el idioma de quien lo publicó, no el de quien lo lee (20-sep-2026)

58 de los 66 calendarios de vacunas salen del almacén público de la OMS, que los da en inglés.
Durante días, un padre marroquí preguntando en árabe recibía su calendario correcto, de su país,
con su fuente oficial… y dentro, «Polio, oral (OPV)» y «Vitamin A (a supplement, not a vaccine)».
Todo bien menos lo único que iba a leer.

No falló nada. Ése es el punto: **importar un dato es importar también el idioma en que está
escrito**, y eso no da error, no rompe ninguna prueba y no se ve desde el fichero de
configuración, porque ahí el inglés parece tan neutro como una fecha.

Tres decisiones al arreglarlo, y las tres se pueden discutir:

1. **La sigla no desaparece, pero sí se escribe como la imprime ese país.** El inglés dice IPV,
   España VPI, Portugal VIP y Rusia ИПВ. Son la misma vacuna vista desde la cartilla de papel que
   la madre tiene en la mano, y ese papel manda sobre cualquier criterio de traducción.
2. **Lo que no está en la tabla sale intacto.** Los ocho calendarios transcritos a mano del
   documento nacional usan las palabras del propio ministerio, y no se tocan.
3. **La traducción vive en `Vaccines.schedule()`**, por donde pasan el chat, la cartilla del
   hijo, el `.ics` y el JSON del sitio. Traducir en cada pantalla es tener cuatro sitios donde se
   olvida; y el sitio, que lee el JSON crudo, recibe una tabla de consulta calculada en Python en
   vez de una segunda implementación en JavaScript.

Y la coma. En árabe es «،», no «,». No impide entender nada y dice, en cada línea, que el texto
no se escribió para quien lo está leyendo.

## L201 · El texto negaba el número que el aviso estaba dando (20-sep-2026)

Probando el sitio vivo como un padre en Nigeria, con un niño atragantado. Lo que llegó a la
pantalla, entero y en este orden:

    🚨 Call 112 now or go to the emergency department.
       Reason: Choking with breathing difficulty

    I can't give you an emergency number — that depends on the country you are in, and my
    sources only mention the number for Spain.

Nada había fallado. El aviso es nuestro, determinista, y sacó bien el 112 de Nigeria. Y el modelo
estaba **obedeciendo** la regla 9 —no mandes al lector a un servicio que sólo existe donde se
escribió la fuente— sólo que, en vez de callarse sobre números, la explicó en voz alta.

Dos cosas que aprender, y la segunda es la que vale:

1. Una regla escrita para el modelo se puede cumplir *hablando de ella*. «No des un número
   extranjero» y «no digas que no puedes dar un número» son dos reglas, no una, y sólo la
   primera estaba escrita.
2. **Las dos mitades de una respuesta se escriben en sitios distintos y nadie las lee juntas.**
   El aviso lo pinta Python desde una tabla; el texto lo escribe el modelo desde unos pasajes.
   Cada mitad es correcta por separado y la pantalla es una contradicción. Lo único que lo
   encuentra es abrirla como la abre un padre, que es como han salido los siete fallos de estos
   dos días.

El prompt lo prohíbe desde hoy, pero eso es una petición. El candado es un verificador: si el
texto niega tener un número, la respuesta se rechaza y se vuelve a escribir, como ya se hacía con
los servicios extranjeros y con las dosis inventadas.

## L202 · Teníamos el dato de 90 países y la pregunta se iba al corpus (20-sep-2026)

«What is the emergency number here?», con Nigeria elegido. Respuesta del chat: *«no tengo
información fiable sobre esto en mis fuentes»*. Mientras tanto, el aviso de arriba —el nuestro,
el determinista— llevaba el 112 escrito, sacado de la tabla que costó semanas.

El corpus son fichas de sociedades pediátricas sobre fiebre, vómitos o bronquiolitis. Ninguna
dice cuál es el número de urgencias de Nigeria, y no tiene por qué: eso está **en una tabla
nuestra**, no en un documento clínico. La pregunta más básica de todo el sitio estaba pasando
por el camino de las preguntas clínicas.

Lo que hay detrás: **el reflejo de mandarlo todo al modelo**. Las vacunas y las dosis ya tenían
su atajo —si la pregunta es lo que contesta una tabla, contesta la tabla— y a las urgencias
nadie se lo puso, porque el aviso ya daba el número y parecía cubierto. No lo estaba: el aviso
sólo aparece cuando el triaje dispara, y un padre que pregunta con calma no dispara nada.

La condición que hace esto seguro, y que es la mitad interesante: **sólo con `routine`**. Si el
niño se está atragantando, «¿cuál es el número?» no es una consulta de datos. El aviso ya manda
llamar, y lo que el texto tiene que decir es qué hacer mientras llega la ayuda. Leer la ficha de
teléfonos ahí sería contestar a la letra de la pregunta en vez de a lo que está pasando.

De regalo, un problema que llevaba escondido desde el principio: Python no sabía decir
«Marruecos». `locale` depende de lo que tenga instalado el servidor y una dependencia más no se
sostenía. Node sí lo sabe, con `Intl`, y es **la misma fuente con la que la web pinta sus
desplegables**: ahora los dos lados dicen el mismo nombre por construcción, generado y no
escrito a mano, que son noventa países por nueve lenguas.

## L203 · Un padre no dice «percentil». Dice «¿está bien?» (20-sep-2026)

Probando el sitio vivo con Kenia elegido:

    my son is 18 months and weighs 8 kg, is that ok?
    → «I can't tell from your son's weight alone whether it's okay…»

Ocho kilos a los dieciocho meses está **por debajo del percentil 3**, y la tabla de la OMS que lo
dice estaba en el mismo servidor, en el mismo proceso. Lo mismo en hindi con una niña de ocho
meses y seis kilos, y en árabe con una de un año y siete. Tres madres de tres continentes
preguntando lo mismo y recibiendo las tres un «no puedo saberlo».

Lo que fallaba **no era el lector**: sacaba el sexo y el peso de las tres frases, en tres
alfabetos. Fallaba la PUERTA, que pedía la palabra «percentil» o las dos medidas en el mismo
mensaje. Y la puerta se escribió mirando cómo pregunta alguien que ya sabe lo que quiere.

La regla, que vale para todas las herramientas: **una condición de entrada escrita desde dentro
sólo deja pasar a quien ya habla como el sistema.** Las dos medidas juntas son una forma de
preguntar; la otra, la que usa todo el mundo, es un número y «¿está bien?».

Y detrás de la puerta apareció el segundo agujero, que sólo se ve cuando la abres: el lector
conocía los sustantivos —hija, daughter, बेटी, ابنتي— y no los pronombres. «She weighs 6 kg»
entraba y se quedaba sin sexo, o sea sin curva. El pronombre se mira ahora en último lugar y
nunca discute con un sustantivo: un «ella» puede ser la madre, y mientras haya una palabra mejor
no tiene por qué mandar.

Queda escrito lo que no se arregló: el suajili dice «uzito wa kilo 8», con la unidad delante, y
el lector espera el número primero. Está en una prueba que **falla el día que se arregle**, para
que alguien venga a quitarla.

## L204 · El hueco de África no era clínico: era no haber mirado sus estanterías (20-sep-2026)

Medido, país por país, antes de decidir qué hacer:

    urgencias:  54/54
    calendario: 54/54
    curvas:     49/54
    marcas:      1/54   ← Egipto

Cincuenta y cuatro países con su número de emergencias comprobado uno a uno y su calendario
oficial transcrito, y el calculador de dosis conocía **una** marca africana. Una madre en Lagos,
en Nairobi o en Casablanca tiene un bote en la mano, teclea lo que pone en la caja y el sitio no
lo reconoce, aunque sepa dosificar esa misma molécula desde el primer día.

Lo que enseña no es «faltaban marcas». Es que **la cobertura se mide en la lista que uno ya
sabe llevar**. Las urgencias y los calendarios se contaban desde el principio porque eran el
trabajo; las marcas no se contaban, así que el mapa se veía lleno mientras la herramienta más
usada de madrugada estaba vacía para un continente entero.

Ahora son 31 países, con Panado en Sudáfrica (prospecto aprobado por la SAHPRA), Emzor en
Nigeria (registro público de la NAFDAC, 125 mg/5 ml y no 120: esos cinco miligramos son justo
los que hacen coger el bote de al lado), Calpol en el África oriental anglófona y Doliprane en
todo el Magreb y el Sahel francófono.

Y un error mío de camino, que también dice algo: metí «Nurofen for Children» con siete países
africanos sin ver que ya estaba arriba con siete europeos. `resolve()` devuelve la primera, así
que la fila de abajo era tinta y una madre en Nairobi habría leído que eso se vende en Reino
Unido. **Añadir a ciegas a un catálogo que ya tiene la entrada es un fallo que no avisa**, y
ahora hay una prueba que lo caza.

## L205 · La misma puerta mal escrita, doce horas después (20-sep-2026)

Ayer: la curva de crecimiento pedía la palabra «percentil», y un padre dice «¿está bien?» (L203).

Hoy, escribiendo la cinta del brazo desde cero, la primera versión de su puerta pedía
«perímetro braquial», «MUAC» o «mid-upper arm circumference». O sea, **pedía que el padre
supiera cómo lo llama la guía de la OMS**. Un padre escribe «el brazo le mide 11 cm», y una
madre keniana «mkono wake ni sentimita 11».

El mismo error, en el mismo proyecto, por la misma mano, con la lección escrita el día anterior
tres archivos más allá. No se aprende leyendo la lección: se aprende cambiando **cómo se
escribe una puerta**, y el orden correcto es al revés del natural. No «qué palabra usaría yo
para buscar esto», sino:

1. ¿qué cosa del mundo está mirando el padre? (el brazo, un número, una unidad);
2. ¿qué otra cosa se parece y NO es esto? (un golpe, un chichón, una fractura);
3. y sólo al final, si acaso, el nombre técnico.

La tercera condición vale tanto como la primera: «se dio un golpe en el brazo y tiene un chichón
de 3 cm» trae la palabra y trae la medida, y contestarle con una franja de desnutrición sería
absurdo y además ocuparía el sitio de la respuesta que necesita.

De propina, el `\b` que no existe detrás del devanagari, que ya estaba anotado en `triage.py` y
volvió a aparecer aquí: «सेमी» acaba en una marca combinante y no hay transición que detectar.
`(?!\w)` sí funciona, porque mira el carácter siguiente en vez de buscar un borde.

## L206 · Antes de recomendar pagar, mirar si eso ha servido para alguien (20-sep-2026)

Escribí el plan entero de Backable —mecánica verificada, seis capítulos, una cifra recomendada
de 262.500 $— **sin comprobar si en esa plataforma se había financiado algo alguna vez**. Lo
preguntó el operador antes de gastar quince dólares: «¿hay proyectos recaudando ahí o es una web
muerta para sacar quince dólares al que se queda insatisfecho?».

Mirado, la respuesta tiene dos mitades y sólo la primera es la que uno espera:

- **No es una web muerta**: once empresas financiadas, 698.000 $ entre las nueve que enseña.
- **Pero es todo o nada, y su techo histórico son 200.000 $.** Con eso, la cifra que yo había
  recomendado era la forma más segura de acabar en cero, con una página pública de ronda fallida
  y los quince dólares gastados.

Lo que enseña no es «comprobar más». Es **qué se comprueba primero**. Yo empecé por la mecánica
—cómo funciona el reparto, el desbloqueo, la entidad legal— que es lo interesante, y dejé para
el final lo aburrido: si ahí entra dinero y cuánto. El orden correcto es el contrario, y vale
para cualquier sitio donde haya que pagar o registrarse:

1. ¿ha funcionado para alguien, y de qué tamaño?
2. ¿cuál es el techo observado?
3. ¿cómo se liquida: todo o nada, o lo que haya?
4. ¿quién está al otro lado?

La mecánica sólo importa si las cuatro salen bien. Y los quince dólares no son el coste: el
coste es el tiempo preparándolo y el golpe de fallar en público.

## L207 · Que mueva dinero no basta: tiene que haber alguien decidiendo (20-sep-2026)

Ayer aprendí a comprobar si una plataforma ha financiado algo antes de recomendarla (L206). Hoy
el operador añadió la mitad que faltaba, y es la que de verdad decide:

> «Las rondas gratis ya sabemos que tienen un problema. Ya lo hemos visto en Liquid Lounge y en
> otros sitios: hay tanto meme y tanta basura que es imposible destacarse. La razón de ir a
> MetaDAO es que hay alguien vigilando y alguien que filtra proyectos decentes de verdad.»

Yo acababa de proponer Gitcoin **porque es gratis y ha repartido 50 millones**, que son los dos
datos que pedía la lección de ayer. Los dos son ciertos y no sirven, porque su mecanismo es
financiación cuadrática: **gana quien trae más donantes, no quien trae mejor proyecto.** Sin
comunidad detrás, un sitio de pediatría con diez preguntas al mes saca cero por muy bien escrito
que esté el perfil. Gratis no significa sin coste: significa que el coste es el tiempo y que el
resultado esperado también es cero.

El criterio completo, para cualquier sitio donde presentarse:

1. ¿ha financiado algo, y de qué tamaño? *(L206)*
2. ¿cómo se liquida: todo o nada, o lo que haya? *(L206)*
3. **¿hay alguien decidiendo, o gana el que hace más ruido?**
4. ¿el público de ahí tiene algo que ver con esto?

La tercera es la que ordena las demás. Un jurado pequeño que lee todas las solicitudes —aunque
dé mil dólares— vale más para este proyecto que una plataforma con un fondo de millones donde
hay que ganar un concurso de popularidad contra monedas de perros. **Lo que aquí no tenemos es
multitud; lo que tenemos es un producto que aguanta que lo miren de cerca.** Hay que ir a donde
miran de cerca.

## L208 · Hay dos puertas, y con una basta: que alguien decida, o que alguien te vea (20-sep-2026)

Escribí L207 y me pasé de frenada: la reduje a «o hay un filtro humano o no vale». El operador lo
corrigió media hora después:

> «O alguien lee y decide, o por lo menos el proyecto tiene una incubación donde la gente puede
> verlo y estudiarlo, que tenga volumen para que haya gente detrás. A lo mejor alguien no mete
> dinero en PediBot, pero sí lo empieza a usar cuando ve que es gratis. Entonces eso nos da
> exposición al fin y al cabo.»

El fallo mío es de encuadre: yo estaba puntuando cada sitio por **cuánto dinero puede salir de
ahí**, y para este proyecto ése no es el único marcador. Esto **no vende una promesa, vende una
cosa que ya funciona y es gratis**. Un sitio con volumen y con gente que prueba lo que ve deja
usuarios aunque no deje un euro, y los usuarios son justo lo que falta para todo lo demás:
para Gitcoin, para contárselo a un ministerio, para que un pediatra lo audite.

Así que la pregunta 3 tiene dos mitades y basta con una:

- **¿hay alguien decidiendo?** — Emergent Ventures, Awesome Foundation, MetaDAO, Y Combinator.
- **¿o hay volumen y se puede ver y probar?** — Show HN, y cualquier sitio con público real.

Lo que se cae sigue siendo lo mismo, y ahora por las dos a la vez: donde reparte la popularidad
**y** el público no tiene nada que ver con esto. Ahí ni deciden ni te ven.

## L209 · Un descargo de responsabilidad no cambia lo que el programa hace (20-sep-2026)

Salió mirando financiación europea, y es de las que hay que tener escritas antes de que importen.
En Europa un programa que a partir de síntomas devuelve una recomendación de a dónde ir es
producto sanitario, y la regla 11 lo pone en **clase IIa** en cuanto la salida es una decisión
clínica en vez de información general. La doctrina es explícita en que **el aviso de «esto no
sustituye a un médico» no cambia el uso previsto**: cuenta lo que el programa hace y cómo se
presenta, no lo que dice la letra pequeña.

Lo que el sitio hace hoy —explicar qué significan los signos de alarma, con la guía delante, y
dar el número de emergencias— cae del lado bueno. Donde puede morderle es en **el vocabulario que
usamos fuera**: en el memo y en las solicitudes lo llamábamos «motor de triaje» sin distinguir.

Y aquí está el matiz que casi me salto al escribir esto, que es el que de verdad vale. La
respuesta **no** es tachar la palabra: el negocio que defiende el memo es precisamente licenciar
el motor a instituciones para el primer filtro, o sea que ahí la palabra es exacta y borrarla
dejaría la tesis más floja y menos honesta. La respuesta es **separar los dos productos en una
frase**, porque son dos: lo que el padre usa hoy, que explica y cita y no diagnostica, y lo que
una institución licenciaría, que sí es una decisión clínica y en Europa es producto sanitario con
todo lo que eso lleva detrás. Puesto así, el memo gana: explica por qué hay una partida de
regulación en el presupuesto y por qué la medición clínica va antes que la primera visita
comercial.

En solicitudes cortas, donde no cabe la distinción, sigue valiendo lo otro: decir lo que hace y
no la etiqueta que lo regula.

## L210 · Un trámite no sólo abre puertas: cierra otras, y el orden cuesta dinero (20-sep-2026)

Repasando ayudas de Sevilla y Andalucía llegué a una conclusión limpia y la iba a escribir tal
cual: «cuatro de estas seis se caen porque piden entidad, y eso se arregla dándote de alta de
autónomo». Cierto, barato, y me faltaba media hora de lectura.

La siguiente convocatoria que miré, Innovactiva, da **9.000 €**, **admite expresamente a la
persona empresaria individual autónoma**, y excluye a **«las personas autónomas que no estén
dadas de alta antes de la convocatoria»**. O sea que el consejo que acababa de escribir —hazte
autónomo ya, que así llegas a la feria de noviembre— **le habría costado nueve mil euros** por
darse de alta tres meses antes de tiempo.

Lo que falla aquí no es la comprobación, que la hice: es que comprobé **qué abre** el trámite y
no **qué cierra**. Un alta, un registro, una constitución de sociedad, publicar un repositorio,
anunciar algo: todos son puertas de una sola dirección, y las convocatorias están llenas de
requisitos que dicen «no haberlo hecho antes».

La regla, y va pegada a L206: **antes de recomendar un paso administrativo, leer las bases de
todo lo demás que esté en la lista buscando la palabra "antes".** Y cuando el orden importa, el
consejo no es el trámite, es el calendario.

Hay un segundo trozo, más incómodo: la respuesta correcta dependía de un dato que no tengo —su
edad, porque Innovactiva es hasta los 35—. Cuando una recomendación se bifurca en algo que no
puedo mirar, lo honesto es escribir las dos ramas enteras y preguntar lo mínimo, no elegir la
rama que me parece más probable y presentarla como la respuesta.

## L211 · Una fecha también es un dato, y la escribí a mano 57 veces (20-sep-2026)

Hoy monté `DATOS.md` y `scripts/check_docs.py` porque **una cifra tecleada no discute con nadie**:
el dato cambia, la frase se queda, y cuanto más útil es el documento más veces se ha copiado.
Encontré 107 cifras así y las arreglé.

Y mientras tanto fechaba todo el trabajo del día como **21-sep-2026**. Es 20. Cincuenta y siete
veces, en veintiséis ficheros, incluidos comentarios de código y docstrings de pruebas. En el
mismo commit en que escribí la regla.

Lo que hace esto peor que un despiste: **el fichero generado tenía la fecha bien al lado**.
`DATOS.md` decía «Contado el 2026-09-20», porque la saca del sistema; yo escribí 21 en su
cabecera. Tenía la respuesta correcta en pantalla y escribí la otra.

Por qué pasó: arrastré la fecha de un resumen de contexto anterior y no la comprobé, porque «la
fecha» no me pareció un dato. Lo es. Un `.md` que dice «medido el 21-sep» cuando se midió el 20
es exactamente la clase de frase que el candado existe para cazar, y el candado no mira fechas.

**La regla:** antes de fechar nada, `date`. Y si aparece una fecha en más de dos sitios en una
sesión, sale de una variable o de un fichero generado, no de la memoria.

Lo que NO voy a hacer, y lo dejo escrito para no caer: **no voy a extender el candado a las
fechas.** Los diarios están llenos de fechas legítimamente viejas, y un detector que persiga eso
generaría cien falsos positivos por cada acierto — que es justo el fallo que arreglé esta mañana
con lo de los 54 países de África. El arreglo aquí no es más máquina: es mirar el reloj.

## L212 · El tercer candado que gritaba con una frase correcta, el mismo día (20-sep-2026)

Tres veces hoy, y las tres del mismo tipo, así que ya no es casualidad sino una forma de
equivocarme que conviene tener escrita.

1. `check_docs.py` señalaba «all 54 countries have their emergency number» —los 54 del
   continente— porque sólo miraba lo que iba **detrás** del número.
2. El mismo candado **callaba** con «288 published documents» porque el patrón pedía la cifra
   pegada al sustantivo y había un adjetivo en medio.
3. Y `test_sitemap_lastmod.py`, que se llama «reconstruir sin tocar nada no puede mover ni una
   fecha», comparaba una construcción nueva contra el `dist/` **que hubiera en el disco**. Al
   añadir el enlace de descarga a la página de fuentes toqué `i18n.ts`, movieron 2.184 fechas, y
   cantó un fallo donde había un cambio legítimo.

Lo del tercero duele más porque **el propio fichero ya lo explicaba**: la segunda prueba de ahí
dice, con todas las letras, que tocar `i18n.ts` cambia de verdad las 792 páginas y que la primera
versión de ese candado se cayó justo por eso. Se arregló una prueba y se dejó la de al lado con
el mismo fallo.

El patrón: **una prueba mide lo que dice su nombre sólo si controla las condiciones de las que
depende.** Ésa comparaba contra un estado del disco que no establecía, así que en realidad medía
«reconstruir después de lo que haya en el árbol», que no es una propiedad de nada.

Y la salida barata era saltársela cuando el `dist/` estuviera viejo. La descarté: entonces no
correría casi nunca, que es otra forma de no avisar. Se arregló construyendo **dos veces** y
comparando las dos entre sí — veintiocho segundos, y ya prueba lo que promete pase lo que pase
en el disco.

## L213 · Un 502 puede ser del intermediario, no del servidor (20-sep-2026)

Buscando la fuente de las curvas de crecimiento que faltaban, las páginas de la OMS me
devolvieron **502 Bad Gateway** dos veces, en http y en https. Escribí en `IDEAS.md` que la
fuente existía pero no se podía leer, y dejé los nueve países sin añadir con esta frase: «citar
una fuente que no he podido abrir es exactamente lo que este proyecto no hace».

Eso último sigue siendo verdad y me alegro de haberlo escrito. Lo que estaba mal es la premisa.
Una hora después probé con `curl` directo y **salieron todas a la primera**. El 502 lo ponía la
herramienta que hace de intermediario, no el servidor de la OMS.

Resultado de insistir con otra herramienta: **nueve países añadidos, unos 470 millones de
personas**, entre ellos Pakistán con 240. Estuvieron a punto de quedarse fuera por un código de
error que no era suyo.

La regla: **antes de dar por inaccesible una fuente, probar por otra vía.** Un 502, un 403 o un
timeout dicen algo del camino, no necesariamente del destino. Aquí hay dos formas de pedir una
página y una hoja de cálculo mental de cuál falla por qué; usarlas cuesta treinta segundos y la
alternativa fue estar a punto de dejar sin curva de crecimiento a un país de doscientos cuarenta
millones de habitantes.

Y el matiz que salva lo demás: **lo correcto fue no añadirlos mientras no pude leer la fuente.**
El fallo no fue la prudencia, fue no agotar las vías antes de aplicarla.

## L214 · Añadir nueve países hizo saltar tres candados, y los tres tenían razón (20-sep-2026)

Al meter Pakistán, Marruecos, Sudán y seis más en las curvas de crecimiento, la suite cantó tres
sitios donde la cifra vieja seguía escrita. Ninguno era daño colateral: los tres eran el sistema
funcionando, y juntos dan la medida de cuántos sitios repiten un número en un proyecto así.

1. **El memo construido** decía 69 donde los ficheros dicen 78. Reconstruí y seguía fallando, así
   que no era el `dist/` viejo: el memo lee `src/data/growth_charts.json`, un intermedio que
   genera `export_catalog.py` dentro de la cadena del despliegue y no `astro build`. Sin ese
   candado, el documento que se le manda a quien nos financia habría salido con una cifra vieja.
2. **El catálogo del agente ACP** decía «69 countries covered» en la descripción que se publica
   en el mercado, o sea hacia fuera y donde no lo mira nadie a diario.
3. **La prueba del registro de países** afirmaba que Marruecos, Túnez y Omán estaban fuera «por
   no haber leído un documento oficial».

El tercero es el interesante y es donde se puede estropear un proyecto en dos minutos: **la
tentación es borrar la comprobación que molesta.** Lo correcto era mirar si la razón por la que
el candado los excluía seguía siendo cierta, y no lo era: había leído su fuente esa misma tarde.
Así que se actualizó **la razón**, escrita entera en la propia prueba, y se dejó intacta la parte
que sigue valiendo — Argelia, Líbano y el Golfo salvo Arabia Saudí siguen fuera.

La regla, y sirve para cualquier candado: **cuando una prueba falla por un cambio legítimo, se
cambia su premisa y se escribe por qué; no se borra la aserción.** La diferencia se ve a los seis
meses, cuando alguien lee la prueba y entiende qué se comprobó, en vez de encontrar un hueco sin
explicación.

## L215 · Lo que hace daño no es el nombre del bote, es la concentración (20-sep-2026)

Buscando marcas para los 23 países africanos que no tenían ninguna, el registro del regulador
etíope —la EFDA, lista de medicamentos sin receta— no da marcas. Da algo mejor, y estuve a punto
de descartarlo por no ser lo que buscaba:

    5. Paracetamol
       100mg/5ml             Drops    1 bottle
       120mg/5ml, 250mg/5ml  Syrup    1 bottle

Los dos jarabes ya estaban. **Las gotas no.** Y ahí no había un hueco de cobertura, había un
riesgo: en Etiopía las gotas de paracetamol son 100 mg/5 ml —20 mg/ml— y en España, Portugal o
la India son 100 mg/**ml**, cinco veces más concentradas. La calculadora sólo ofrecía la segunda.

O sea que un padre en Adís Abeba con su bote en la mano leía «gotas» en el envase, encontraba
«gotas 100 mg/ml» en nuestra lista y **le daba cinco veces la dosis**. No es rebuscado: es lo que
hace cualquiera que busca en una lista la palabra que pone en su frasco.

Tres cosas que sacar de aquí:

1. **Iba buscando marcas y lo valioso era otra cosa.** Cuando una fuente no trae lo que fuiste a
   buscar, hay que mirar qué trae antes de cerrarla. La cabecera de `config/drugs.yaml` lo decía
   desde el principio: «la concentración es lo que cambia y lo que los padres confunden».
2. **Un hueco de cobertura y un riesgo se parecen mucho por fuera.** «Etiopía no tiene marcas»
   suena a que falta un adorno. Lo que faltaba era la única fila que impedía un error por cinco.
3. Y de paso apareció un `KeyError` en `brands_for` ante una clave desconocida —la misma molécula
   llega como «ibuprofen» y como «ibuprofeno»—, o sea que **la calculadora de dosis podía
   caerse** por un nombre. Ahora devuelve vacío, que es lo que debe hacer una consulta que no
   encuentra nada.

Y el patrón de todo el día otra vez: la prueba que usaba Etiopía como ejemplo de «país sin nada»
dejó de valer. No se borró la aserción: se cambió el ejemplo a Burundi y se escribió por qué.

## L216 · El arreglo abrió un agujero peor que el que cerraba (20-sep-2026)

Media hora después de añadir las gotas etíopes de 100 mg/5 ml, comprobando la web viva —no el
código— miré el orden de la tabla **sin país seleccionado** y ahí estaba:

    – drops 100 mg/5 ml: 7.5 ml     ← la primera línea
    – syrup 120 mg/5 ml: 6.2 ml
    ...
    – drops 100 mg/ml: 1.5 ml

Un padre en España con Apiretal —gotas de 100 mg/**ml**— que no hubiera elegido país veía
«drops» en la primera línea, le daba 7,5 ml, y eran **750 mg en vez de 150**. Cinco veces de más,
y esta vez en la dirección mala: sobredosis, no defecto.

El arreglo que acababa de cerrar un riesgo de cinco veces en Etiopía abría otro de cinco veces
en todos los países que no eligen país. La causa es tonta y por eso es peligrosa: la tabla estaba
ordenada de menos a más concentrada, y la etíope es la más diluida de todas, así que se puso
arriba sola.

**Lo que hay que sacar de aquí, y es lo importante:**

1. **Un cambio de seguridad no termina cuando pasa la suite.** Todas mis pruebas nuevas pasaban.
   Lo que falló no era una aserción, era el orden, que ninguna miraba. Lo encontré mirando la
   salida como la mira un padre.
2. **Al tocar una tabla de dosis, hay que mirar quién ve qué DESPUÉS**, no sólo si lo nuevo está.
   Añadir una fila cambia la primera línea que lee todo el mundo.
3. Y el arreglo bueno no fue mover una fila: fue **agrupar por forma farmacéutica**. Ahora las
   tres presentaciones de gotas van seguidas, así que quien busca «gotas» las ve juntas y tiene
   que leer la concentración para elegir. Se le obliga a la comparación en vez de confiar en
   que la haga.

Con dos pruebas que lo sujetan: la tabla no puede abrir con unas gotas, y las gotas tienen que ir
seguidas.

## L217 · Un valor por defecto es una decisión que tomas tú por alguien que no mira (20-sep-2026)

Al montar el campo donde el padre escribe lo que pone su bote, puse el desplegable de unidades
con **«mg por 5 ml» preseleccionado**. El razonamiento parecía bueno: es lo que pone la inmensa
mayoría de los botes infantiles del mundo, y las cinco presentaciones que recomienda la OMS van
todas así. Optimizar para el caso común.

Lo vi media hora después releyendo el código ya desplegado. Un padre en España con Apiretal
—**100 mg por ml**— escribe 100, **no toca el desplegable porque ya viene puesto**, y le salen
7,5 ml en vez de 1,5. Cinco veces de más. Por no tocar nada, que es exactamente lo que hace todo
el mundo con un valor por defecto: confiar en que está bien.

Y lo peor es que con el número 100 **no se puede adivinar cuál quiso decir**, porque las dos
lecturas existen de verdad: las gotas etíopes son 20 mg/ml y las españolas 100. No hay heurística
que salve esto. Sólo puede decirlo él.

**La regla:** en una entrada donde equivocarse cambia una dosis, **no hay valor por defecto**.
Se deja vacío, no se calcula nada hasta que elige, y el que no elige no recibe un número
plausible: no recibe ninguno.

Es la segunda vez hoy que un arreglo mío abre un agujero por optimizar para el caso común
—la primera fue poner las gotas más diluidas arriba del todo (L216)—. El patrón compartido es el
mismo y conviene tenerlo escrito así: **lo cómodo para la mayoría es peligroso para la minoría
cuando el precio de equivocarse no es simétrico.** Un padre que tiene que elegir pierde dos
segundos. Un padre al que le eligen mal le da a su hijo cinco veces la dosis.

## L218 · El script funcionaba, y lo que sacaba era basura (20-sep-2026)

La OMS abrió en abril de 2025 un repositorio con las listas nacionales de medicamentos
esenciales, **46 de ellas de la región africana**. Eso pone al alcance, de golpe, lo que con
Etiopía me costó una tarde: qué concentraciones publica cada país.

Escribí un barrido: bajar los PDF, buscar «paracetamol» e «ibuprofeno», y leer las
concentraciones que aparecen detrás. Corrió sin un error y devolvió **18 países con datos**.
Parecía el mejor rato del día.

Entonces miré Mozambique, que es el único de esos 18 cuyo PDF había leído antes con los ojos.
El script decía **«paracetamol 10 mg/ml»**. La lista dice **125 mg/5 ml y 250 mg/5 ml**. En el
único caso que podía contrastar, el script estaba mal.

Con eso, mirando el resto se ve solo: ibuprofeno a 120 mg/5 ml en Chad, paracetamol a 125
mg/**ml** en Lesoto, paracetamol a 100 mg/2 ml. No existen. Son cifras de columnas de al lado,
porque una tabla de PDF no tiene columnas: tiene texto en un orden que parece el de la tabla y no
lo es.

**Lo que hay que sacar de esto, y no es «los scripts fallan»:**

1. **Un barrido que no tiene con qué contrastarse no es una medición, es una lista de números.**
   Lo único que convirtió esto en un hallazgo fue tener un caso leído a mano antes. Sin
   Mozambique, habría metido dieciocho países de datos de dosis inventados por un `regex`.
2. **La tentación era enorme y hay que nombrarla**: dieciocho países de un tirón, después de
   pelear uno solo. Cuanto mejor parece el resultado de un atajo, más hay que buscarle el caso
   de control.
3. Y aquí no es un documento con una cifra vieja: **son mililitros que un padre le da a su
   hijo**. El listón no es «probablemente correcto».

Lo que sí se hizo: añadir **Ruanda y Mozambique**, leídos del PDF con los ojos, uno por uno,
como Etiopía. Tres países de tres, y cada uno con la frase exacta que se leyó anotada en el
`leido:` de su entrada. Los otros 43 están localizados y esperan la misma lectura.

## L219 · «Dos preguntas, dos desastres»: el operador tenía razón, y la medida dijo dónde (21-sep-2026)

Con el móvil y el panel delante: *«Mira qué mal. Dos preguntas, dos desastres. Deberíamos meter
un filtro de IA que interprete la pregunta y ayude a buscar, porque por palabras o raíces es un
maldito desastre. Si ya tenemos pocas visitas y las que tenemos no funcionan…»*

Era un padre de verdad, desde Italia, con la web en inglés: su hijo de 15 años con un tobillo
escayolado. Fallaron cuatro cosas a la vez: le contestó **en inglés**; la búsqueda trajo **la
página brasileña de la polio** porque «gesso» también es escayola en portugués; citó al
Ministério da Saúde por algo que ese documento dice de la polio; y a «Puoi scrivere in
italiano?» lo trató como pregunta médica y citó salud mental, chikunguña y alcohol.

**Antes de construir, se midió**, con ocho preguntas como las escribe un padre y la clave real.
Y la medida afinó la idea en vez de confirmarla entera:

- en las lenguas que NO tenemos, la IA arregla la búsqueda de forma brutal: holandés «fiebre y
  tos» pasaba de traer **VIH** a traer la fiebre infantil del NHS;
- la detección de idioma por palabras fallaba justo ahí: italiano como español, holandés como
  inglés, polaco como francés;
- en las que SÍ tenemos, la búsqueda de siempre ya iba bien y la IA a veces la empeoraba;
- y el caso italiano **no lo arregla ninguna búsqueda**, porque no hay ningún documento sobre
  escayolas y músculo. Lo correcto era «no lo sé», y el fallo de verdad era haber citado la polio.

Así que se construyó lo que la medida pedía y no lo que sonaba bien: la IA **lee** la pregunta
—lengua, intención y la frase en inglés y castellano médicos— y **no contesta nunca**; la
respuesta sigue saliendo de las fuentes. Reescribe la búsqueda sólo fuera de las ocho lenguas.
Decide el idioma en todas. Y el redactor contesta la señal `NO_SOURCE` cuando ningún pasaje
responde, en vez de explicar en prosa por qué no sirven y citarlos igual.

Dos cosas que salieron por el camino y valen más que el arreglo:

1. **La alarma en italiano no sacaba el cartel rojo.** «Non respira bene e ha le labbra blu»:
   el triaje no sabe italiano. Pasaba desde siempre. Ahora el triaje lee también la traducción
   de la IA, **sumada** al original para que sólo pueda añadir alarmas, nunca quitarlas.
2. **«Eso es básico», dicho del idioma, y tenía razón en todos los caminos**, no sólo en la
   respuesta redactada: el «no tengo información» y el «¿qué edad tiene?» eran frases fijas que
   sólo existían en ocho lenguas. Ahora se traducen —son lo único que el modelo traduce, porque
   no llevan cifras— y si la traducción trae un número distinto del original, se tira.

Y lo que el operador añadió después y también era correcto: *«que no vaya a responder el motor
de IA, tiene que seguir tirando de las fuentes»*. Así está. Lo que sí contesta con texto propio
son dos cosas, y con texto FIJO y revisado: «¿qué es PediBot?» y «eso no es de salud infantil».
Nunca cuando el triaje ve la menor alarma: pila, lejía, imán y pastillas lo paran antes.

## L220 · Diez preguntas seguidas no son una conversación (21-sep-2026)

El operador probó el chat haciendo diez preguntas distintas en la misma ventana, como las hace
cualquiera que prueba algo. El motor junta la conversación a propósito —«tiene manchas» y luego
«no desaparecen al apretar» es el meningococo contado en dos frases—, y juntó también las que no
tenían nada que ver: el bebé que lloraba salió con el motivo «vómitos tras un golpe en la
cabeza», el Dalsy y los ojos rojos heredaron sus «dos meses». Nadie lo había visto porque todas
las pruebas de conversación eran de UN problema contado en varios mensajes.

La misma lectura de IA que ya leía cada pregunta ahora mira también la anterior y dice si es
otro problema. Medido con el modelo real antes de desplegar: 11 de 11, incluidos los cinco casos
que tienen que seguir juntos. Sólo un «sí» explícito separa; ante la duda, se junta.

Y en la misma tanda, la otra mitad de la lección: **«se ha caído y ahora está somnoliento» salía
rutina**. El triaje tenía el golpe con vómitos y el golpe con pérdida de conocimiento, pero no la
somnolencia, que es por la que MedlinePlus manda llamar a emergencias. Una prueba de diez frases
escritas como las escribe un padre encontró lo que 1.700 casos de batería no tenían.

## L221 · 523 preguntas escritas a mano valen más que 1.700 casos de batería (21-sep-2026)

El operador escribió 523 preguntas como las escribe un padre —«mi bebe 8m 39f fiebre apiretal 5ml
hace 2h ahora 39.5 q hago», en veinte lenguas, con recetas y bitcoin por medio— y pidió «depura
al máximo, no hay prisa». La batería automática del triaje tenía más de 1.700 frases y pasaba
entera. Estas encontraron en una tarde lo que aquélla no: la fiebre con el cuello «muy» rígido
(la regla pedía «cuello rígido» seguido), el alemán «Baby» leído como lactante, cuatro lenguas
donde tragarse unas pastillas no avisaba de nada.

Y la otra mitad, que es la que duele: **mis propios arreglos de ese día empeoraron cosas.** La
regla «contesta primero sí o no» produjo «No, no es sarampión» a quien no había preguntado por el
sarampión; la regla «no rellenes» convirtió respuestas buenas en «no puedo responder». Sólo se
vio porque la batería se volvió a pasar entera después de cada tanda y se comparó pregunta a
pregunta (`eval/bateria_operador/compara.py`). Un arreglo de prompt se mide contra todo, no
contra el caso que lo motivó.

## L222 · El texto no puede quitarle la razón al aviso (21-sep-2026)

«Mi hija se ha metido arena en el ojo y no deja de llorar»: el triaje sacó el aviso de urgencias,
y debajo el redactor escribió «No, no es una urgencia por sí solo». Nadie lo había visto porque
cada pieza hacía bien lo suyo: el triaje avisaba, el redactor citaba una fuente real (la SEUP sí
dice que el ojo rojo no es una urgencia). Lo que fallaba era la costura entre las dos. Ahora es
una comprobación de seguridad, no de estilo: con un aviso encima, un borrador que diga «no es
urgente» se reescribe, y si lo repite no sale; sale «haz lo que dice el aviso de arriba».

La misma tarde salió su pariente: una regla del prompt pensada para contestar primero lo que se
pregunta («¿puedo darle miel?» → «No, …») acabó inventando veredictos («No hay ningún problema en
que siga con el biberón») que ninguna fuente daba. Cada regla que empuja al modelo hacia una
forma de frase le empuja también a rellenarla cuando no tiene con qué.

## L223 · «ron» vive dentro de «biberón» (22-sep-2026)

«Mi bebé ha tomado un biberón que llevaba dos horas fuera» recibía el aviso de **intoxicación
etílica**. El patrón de alcohol listaba `ron` sin límites de palabra, y `ron` está dentro de
`bibeRON`. Media hora después, el mismo error con otra cara: la exclusión que acababa de escribir
para «el perro de los vecinos NUNCA le ha mordido» tenía `no le ha`, que está dentro de
«el gato del veciNO LE HA arañado», y apagó una mordedura de verdad.

Las dos veces el patrón era mío y las dos veces el fallo fue el mismo: **una palabra corta sin
`\b` no es una palabra, es una subcadena**. Y no basta con escribirlo: entre comillas **dobles**,
YAML lee `\b` como un retroceso y el patrón llega al motor sin sus límites — con comillas simples
o sin comillas llega entero. El síntoma es desconcertante, porque el fichero se ve bien y la
regla se comporta como si no lo estuviera.

## L224 · Doscientas veinte preguntas sobre nosotros, y un folleto para todas (22-sep-2026)

De las 854 preguntas de la batería del operador, 220 no eran de salud: eran sobre PediBot. «¿Puedo
subirle una foto de la erupción?», «¿guarda las conversaciones?», «¿entiende hindi?», «¿puede
buscar una farmacia abierta?», «¿recuerda lo que le dije hace diez minutos?». Las 220 recibían el
**mismo párrafo de presentación**, que no contesta a ninguna.

Se arregla igual que una pregunta de salud: una ficha de hechos (`config/sobre_pedibot.md`), la
regla de siempre —lo que la ficha no dice, no se dice— y los números sin escribir, rellenados por
el sistema que está corriendo. Dos cosas que no se ven venir: la mitad de esas preguntas son
cosas que PediBot **no** puede hacer, y decirlo en la primera frase vale más que cualquier
descripción; y un test que compruebe que la ficha sigue siendo verdad es obligatorio, porque una
ficha que envejece mal se le enseña al padre con la misma cara de certeza que una verdadera.

## L225 · El conjunto dorado lleva nueve días sin mirarse y no lo sabías (22-sep-2026)

Arreglando diecisiete falsas alarmas medí el conjunto dorado y salió peor: `triage_exact` 0,958
donde el 13-sep había 1,0. La primera reacción fue correcta —he roto algo— y la segunda también:
**cuánto de eso es mío**. Con el triaje de ayer puesto en su sitio (`git stash` de dos ficheros
y volver a medir), el dorado ya daba 0,975: siete de los nueve fallos venían de los cambios de
la noche anterior, que nadie volvió a medir. Míos eran dos, y los dos reales:

- «Diarrea desde hace 2 días, ojos hundidos y casi no hace pis» dejó de ser deshidratación
  porque yo había metido `d[íi]as?` en el pasado remoto. **«Hace dos días» es ahora**, no un
  recuerdo; el pasado remoto empieza en las semanas.
- El espasmo del sollozo que apagué se llevó por delante «se pone MORADO y deja de respirar»,
  que el dorado marca como emergencia. La exclusión correcta no era la del llanto: era «sin
  cianosis y sin pérdida de conocimiento».

La lección no es «mide»: es **mide antes de empezar**, porque una medición que sólo se hace al
final no distingue tu regresión de la que ya estaba, y la tentación de contarlas todas como
heredadas es exactamente igual de fuerte que la de contarlas como propias.

## L226 · La pregunta sobre el producto es una pregunta de producto (22-sep-2026)

Las 220 preguntas sobre PediBot no se arreglaron con un texto mejor. Se arreglaron con las
mismas tres piezas que las de salud: una fuente (la ficha), la prohibición de salirse de ella, y
un test que comprueba que la fuente sigue siendo verdad. Lo que cambió el resultado no fue la
redacción sino **haber escrito los hechos en un sitio**: hasta entonces vivían repartidos entre
el código, la página legal y la cabeza de quien lo hizo, y por eso la respuesta era un folleto.

Y un detalle que sólo se ve probando en otra lengua: el modelo, al traducir, tradujo también las
direcciones —`pedibot.xyz/it/dose`— y las inventó para idiomas que el sitio no tiene. Una URL es
un dato, no una palabra.

## L227 · «Lo ha escrito un test» explicaba lo que veía, y era falso (22-sep-2026)

Al comprometer, aparecieron dos guías nuevas en `web/content` —ahogamiento en árabe, percentiles
en alemán— con la fecha de hoy. Supuse que las había generado la prueba de publicación al correr
la batería, las saqué del repo con un commit que decía «aquí no entra nada hacia fuera sin que el
operador lo lea», y volvieron a aparecer en el commit siguiente. Las borré otra vez.

No las escribía ningún test. Las escribe el temporizador `pedibot-publish` **en el servidor**, y
`deploy.sh` se las trae en cada despliegue a propósito: su cabecera lo dice en la línea 15, «the
server writes new guides, so normally its web/content wins». Es decir: estuve borrando contenido
del producto dos veces seguidas, con una razón que sonaba responsable.

Lo que falló no fue la deducción sino el orden: **la explicación llegó antes que la comprobación,
y encajaba**. Un fichero que reaparece después de borrarlo es la señal de que alguien lo está
poniendo ahí, y la respuesta estaba a un `grep content ops/deploy.sh`. Regla: cuando algo vuelve
solo, no lo vuelvas a borrar — averigua quién lo pone.
