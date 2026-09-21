# La batería del operador (21-sep-2026)

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
