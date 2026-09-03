# Fuentes árabes — resultado del rastreo de licencias (3-sep-2026)

> Paso 1 de la fase árabe. Mismo criterio que decidió el ruso: **si la OMS publica en ese idioma,
> hay corpus abierto garantizado**, porque sus seis lenguas oficiales van con CC BY-NC-SA 3.0 IGO,
> la licencia que el proyecto ya aceptó en agosto.

## Lo que se verificó

| Fuente | Licencia | Veredicto |
|---|---|---|
| **OMS en árabe** (who.int/ar) | CC BY-NC-SA 3.0 IGO, la misma política de acceso abierto ya comprobada para el ruso | ✅ usable |

**Las 15 fichas están disponibles en árabe**, las mismas quince que en ruso, todas con un 200
comprobado antes de listarlas: sarampión, rubéola, neumonía, diarrea, alimentación del lactante,
desnutrición, salud mental adolescente, cobertura de vacunación, meningitis, poliomielitis,
hepatitis B, tuberculosis, ahogamiento, quemaduras y caídas.

Índice tras la ingesta: **288 documentos, 6.548 pasajes**. El árabe entra por debajo del 10% del
corpus, así que recibe el **impulso de idioma escaso** automáticamente, igual que el ruso y el
francés.

## Lo específico del árabe, que no es la licencia

El árabe es el primer idioma del proyecto que **no se escribe de izquierda a derecha**, y eso
tocó cosas que ningún idioma anterior había tocado:

- **La maquetación se refleja.** Las 43 declaraciones de CSS con dirección física
  (`margin-right`, `border-left`, `text-align: left`) se convirtieron a propiedades lógicas
  (`margin-inline-end`, `border-inline-start`, `text-align: start`), que significan «después del
  texto» en vez de «a la derecha». Se hizo **antes** de que el árabe existiera, para que fueran
  43 cambios comprobables por sí solos y no quedaran mezclados con el idioma.
- **La fuente.** Ninguna de las tres tipografías del sitio tiene glifos árabes, así que sin una
  fuente propia la página caía en la que tuviera el dispositivo. Se carga Noto Sans Arabic **solo
  en las páginas que la necesitan**.
- **La fecha.** `toLocaleDateString('ar-SA')` devuelve fecha **hijri** en la mayoría de
  navegadores: un artículo escrito ayer se leería como «12/03/1448». Las fechas tienen ahora su
  propia configuración, y el árabe pide el calendario gregoriano de forma explícita.
- **Los dígitos** se dejan occidentales (0-9), no índico-arábigos (٠-٩): las dosis son lo único
  del sitio que no puede prestarse a confusión, y es lo que está impreso en los envases.

## Lo que encontró el check y no habría encontrado una lectura

Dos fallos de **gramática**, no de vocabulario, que solo aparecieron al pasar frases reales por
el triaje:

1. **Los verbos se conjugan por género.** «لا يستجيب» es *él* no responde; una madre escribiendo
   sobre su hija teclea «لا تستجيب». Todos los patrones estaban en masculino, así que la mitad de
   los niños del mundo no disparaban las reglas de alarma. Añadidos 34 patrones en femenino.
2. **El dual.** El árabe tiene una forma propia para exactamente dos: «شهران» es *dos meses*, no
   «2 meses», y el analizador de edades lee dígitos. La regla más importante del listado —
   lactante de menos de 3 meses con fiebre — estaba muda justo para la edad por la que existe.

Ambos quedan fijados en `tests/test_triage_ar.py`.

## La foto honesta

El árabe queda como el ruso: **un pilar abierto de verdad (la OMS) y nada más verificado**. No se
comprobaron fuentes nacionales árabes, y no hay ningún calendario de vacunación de país árabe en
el sitio — los cinco que hay (España, Reino Unido, EE. UU., Francia, Alemania) están traducidos al
árabe y son útiles para la diáspora, pero un padre en Riad o El Cairo no encuentra el suyo.

Buena parte del consejo en árabe se apoyará en guías del NHS, la SEUP, MedlinePlus y los CDC
traducidas al escribir, con el organismo nombrado en cada frase.
