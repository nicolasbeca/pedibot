# Fuentes rusas — resultado del rastreo de licencias (3-sep-2026)

> Paso 1 de la fase rusa, mismo método que el francés y el alemán: la licencia se lee en la
> página legal del propio sitio. El rastreo se hace desde el VPS porque el antivirus local rompe
> el TLS de Python (L65).

## El criterio que salió del alemán, y aquí decide

**¿Publica la OMS en ese idioma?** Sus seis lenguas oficiales (árabe, chino, español, francés,
inglés, ruso) vienen con **CC BY-NC-SA 3.0 IGO**, que es la licencia que el proyecto ya aceptó en
agosto. El alemán no está en esa lista y por eso su corpus es fino; el ruso sí.

## Lo que se verificó

| Fuente | Quién es | Licencia leída | Veredicto |
|---|---|---|---|
| **OMS en ruso** (who.int/ru) | Fichas de enfermedades en ruso, escritas por la propia OMS | La página de derechos de autor en ruso remite a la política de acceso abierto: «все публикации ВОЗ на условиях лицензии **CC BY-NC-SA 3.0 IGO**» | ✅ usable, misma licencia ya aceptada |
| Rospotrebnadzor | El organismo sanitario ruso | **No verificable**: la web no responde desde el VPS (tiempo de espera agotado) | ❓ sin comprobar |
| minzdrav.gov.ru | Ministerio de Sanidad ruso | Responde, pero no se localizó una cláusula de licencia | ❓ sin comprobar |
| UNICEF en ruso | Contenido de crianza | Responde; UNICEF suele reservarse los derechos | ⏳ segunda ronda |

## Lo que se añadió

**15 fichas de la OMS en ruso.** Cada una se comprobó con un 200 antes de listarla; **cuatro de
las que se usan en otros idiomas no existen en ruso** (`breastfeeding`, `mumps`, `newborn-health`,
`hand-hygiene`) y se descartaron en vez de adivinar la URL.

Sarampión, rubéola, neumonía, diarrea, alimentación del lactante, desnutrición, salud mental
adolescente, cobertura de vacunación, meningitis, poliomielitis, hepatitis B, tuberculosis,
ahogamiento, quemaduras y caídas.

Índice: **273 documentos, 6.422 pasajes**. El ruso entra por debajo del 10% del corpus, así que
recibe automáticamente el **impulso de idioma escaso** — medido del propio índice, no fijado a
mano, igual que el francés.

## La foto honesta

El ruso queda **entre el francés y el alemán**: tiene un pilar abierto de verdad (la OMS), pero
no tiene el equivalente de Canada.ca, y las fuentes rusas propias no se han podido verificar. En
la práctica, buena parte del consejo en ruso se apoyará en guías del NHS, la SEUP, MedlinePlus y
los CDC traducidas al escribir, con el organismo nombrado en cada frase. La regla del generador
que prohíbe remitir al servicio sanitario de otro país evita el error grave.

## Sin calendario de vacunación ruso

Los cinco calendarios (España, Reino Unido, EE. UU., Francia, Alemania) **están traducidos al
ruso** y `/ru/vaccines` funciona, pero **no hay calendario de Rusia**: transcribirlo exige leer
la orden vigente del Ministerio, y publicar de memoria un calendario de vacunación infantil es
justo el tipo de cosa que este proyecto no hace. Queda pendiente y explícito.

Es menos grave de lo que parece: buena parte de los lectores en ruso están en Alemania, España,
Reino Unido o Estados Unidos, y esos cuatro sí están.
