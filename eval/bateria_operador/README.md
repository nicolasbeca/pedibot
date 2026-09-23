# La batería del operador (21 y 22-sep-2026)

523 preguntas escritas por el operador como las escribe un padre: con faltas, sin tildes, en
veinte lenguas (las ocho del sitio y otras doce), mezcladas con cosas que no tienen nada que ver
(«y por cierto, ¿cómo se hace una bechamel?») y con las 63 que el chat había contestado mal de
verdad en producción.

Ese día sacaron a la luz, entre otras cosas:

- alarmas que faltaban: fiebre con el cuello muy rígido, el pecho que se hunde, manchas moradas
  con fiebre en portugués, somnoliento tras una caída, pastillas o detergente tragados en hindi,
  suajili y árabe, la raya roja que sube desde un corte;
- falsas alarmas: «Baby» con fiebre en alemán leído como lactante, el sobresalto del sueño leído
  como convulsión, morado al llorar (espasmo del sollozo), la mancha mongólica;
- respuestas que empezaban por «si tiene menos de 3 meses» con un niño que ya habla, que pedían
  «¿qué le pasa?» a preguntas claras, o que rellenaban con otra enfermedad.

## Cómo se usa

    S=eval/bateria_operador
    uv run --env-file .env python $S/correr.py $S/01_primera_260.txt /tmp/antes.jsonl
    # … cambio …
    uv run --env-file .env python $S/correr.py $S/01_primera_260.txt /tmp/despues.jsonl
    uv run python $S/compara.py /tmp/antes.jsonl /tmp/despues.jsonl

Usa el motor de la web con el índice local y el modelo de verdad (cuesta céntimos). No pasa por
la API, así que no cuenta en el límite de preguntas ni aparece en el panel. No es un test
automático: hay que leer las respuestas. Lo que sí es automático está en `tests/`, y cada fallo
de aquí que se arregló dejó allí su frase.


## La sexta tanda: 854 preguntas (22-sep-2026)

`05_sexta_600.txt`. El operador las mandó de una tirada por la mañana, tal cual las escribe un
padre, y traen dos cosas que las anteriores no tenían:

- **crianza de verdad**: el sueño, las rabietas, los hitos por edad, el niño que no come, los
  dientes, los ojos, y lo que dicen la suegra, el abuelo y una cuenta de Instagram;
- **220 preguntas sobre PediBot**: qué sabe hacer, qué guarda, qué idiomas entiende, si puede
  ver una foto o buscar una farmacia. Todas recibían el mismo párrafo de presentación.

De las primeras 380 respuestas, 87 salieron «no tengo fuente». Casi ninguna era por falta de
documento raro: faltaba la mitad de la crianza en el corpus (45 fuentes nuevas) y faltaba el
puente castellano→inglés para llegar a la otra mitad («dentición» no llevaba a `teething`).


## La séptima y la octava: 1.000 preguntas en un día (23-sep-2026)

`06_septima_500.txt` y `07_octava_500.txt`. Escritas con el mapa de las trece superficies
delante: la misma señal dicha de diez maneras, negada («no tiene manchas»), pasada («la semana
pasada»), hipotética («¿y si algún día…?»), preguntada al chat («¿tú qué haces si…?») y mezclada
con la vida real («estoy en una isla sin pediatra»).

Sin fuentes: **4,6 %** en la séptima y **3,4 %** en la octava, contra el 23 % de la primera.

Lo que encontraron no fue falta de documentos, sino **bordes**: frases que hacían saltar una
alarma que no tocaba («¿puedo mandarte una foto de labios azules?»), frases que no la hacían
saltar y debían («se ha puesto azul»), y dos respuestas que tranquilizaban sin base — un peso de
14 kg a los 6 meses llamado «dentro de lo normal», y un percentil de talla dado sin decir que
faltaba el peso.

Cómo se corre, de principio a fin:

    uv run python eval/bateria_operador/correr.py 07_octava_500.txt r14_07.jsonl
    uv run python eval/bateria_operador/revisor.py r14_07.jsonl rev14.jsonl
    uv run python eval/bateria_operador/resumen.py r14_07.jsonl

Y después se leen. El revisor marca de más —discute umbrales que tienen fuente y fecha—, así que
su lista es por dónde empezar a leer, no la lista de arreglos.
