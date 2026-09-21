# DATOS.md — las cifras del proyecto, contadas

> **Este fichero se genera. No se edita a mano.**
> `uv run python scripts/build_datos.py` lo reescribe leyendo los ficheros de datos de verdad.
>
> Existe porque el 20-sep-2026 se midió cuántas cifras escritas a mano en los `.md` ya no eran
> verdad: **107**. Ninguna estaba mal el día que se escribió. Una cifra tecleada no discute con
> nadie: el dato cambia y la frase se queda, y cuanto más útil es el documento más veces se ha
> copiado esa frase.
>
> **La regla, desde hoy:** ningún documento vuelve a escribir una de estas cifras. Se enlaza
> aquí. `scripts/check_docs.py` comprueba que nadie la repita mal, y la suite lo ejecuta.
>
> Lo que sí puede llevar cifras viejas, a propósito: `LESSONS.md`, `STATE.md` e `IDEAS.md`, que
> son diarios. Una cifra de hace un mes ahí no es un error, es lo que pasó ese día.


Contado el **2026-09-21**.

| | cifra | de dónde sale |
|---|---:|---|
| países con número de emergencia | **90** | config/emergency_numbers.yaml |
| de ellos, sin número nacional | **8** | los marcados `no_national` o `unverified` |
| calendarios de vacunas | **66** | config/vaccines.yaml |
| tablas de crecimiento por país | **78** | config/growth_charts.yaml |
| reglas de alarma | **87** | config/red_flags.yaml |
| marcas de medicamento | **35** | config/drugs.yaml |
| países con alguna marca | **57** | los `countries` de esas marcas |
| nombres de vacuna traducidos | **40** | config/vaccine_names.yaml |
| documentos del catálogo público | **546** | dataset/sources.json (CC0) |
| documentos del catálogo interno | **549** | incluye los que no se pueden redistribuir |
| guías publicadas | **507** | web/content/*/*.md |
| pruebas automáticas | **9.785** | `uv run pytest --collect-only` |
| África: países con número | **54** | los 54 del continente |
| África: con calendario | **54** | los 54 del continente |
| África: con curva | **52** | los 54 del continente |
| África: con alguna marca | **31** | los 54 del continente |
| guías: idiomas | **8** | una carpeta por lengua en web/content |

Si una de estas cifras te parece mal, el fallo está en el fichero de datos que la alimenta, no aquí. Ésa es la idea.
