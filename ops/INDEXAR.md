# Las 20 páginas que pedir a mano en Search Console

Medido el 6-sep-2026 preguntándole a Google, una por una, con la API de inspección de URL. **No
son elegidas a ojo: son las que Google dice que NO tiene**, ordenadas por lo que puede dar cada una.

## Cómo se pide

Search Console → arriba, la barra **«Inspeccionar las URL de…»** → pegas la dirección → esperas a
que responda → **Solicitar indexación**.

Va de una en una y el límite ronda las **10-12 al día por propiedad**, así que esto son dos días.
Empieza por arriba: están en orden de valor, no de comodidad.

## Por qué estas y no otras

La única demanda real que nos alcanza, y que no es gente buscando la marca «pedibot», son
**consultas de dosis por medicamento**: «calculadora apiretal», «apirofeno 40 mg calculadora»,
«calcular dosis apiretal». Compiten contra blogs, no contra el NHS — es la única categoría donde
una web nueva puede ganar. Y los **calendarios de vacunas** son la categoría que mejor puesto
saca de todo el sitio (11 y 27, frente al 88-95 de las guías).

**Ya indexadas, no las pidas** (gastarías el cupo del día para nada): `/es/dose/apiretal`,
`/es/dose/dalsy`, `/es/dose/alivium`, `/es/dose/calpol`, `/es/dose/gelocatil`, `/es/dose/junifen`,
`/es/dose/tachipirina`, `/es/dose/tempra`, `/dose/calpol`, `/dose/nurofen`, `/dose/panadol`,
`/es/vaccines`, `/vaccines`.

## La lista

### Día 1 — dosis por marca en español, que es donde está la demanda medida

```
 1  https://pedibot.xyz/es/dose/apirofeno
 2  https://pedibot.xyz/es/dose/nurofen
 3  https://pedibot.xyz/es/dose/paracetamol
 4  https://pedibot.xyz/es/dose/termalgin
 5  https://pedibot.xyz/es/dose/efferalgan
 6  https://pedibot.xyz/es/dose/panadol
 7  https://pedibot.xyz/es/dose/advil
 8  https://pedibot.xyz/es/dose/motrin
 9  https://pedibot.xyz/es/dose/tylenol
10  https://pedibot.xyz/es/dose/doliprane
```

`apirofeno` va la primera a propósito: es *ibuprofeno* mal escrito, la gente lo busca así (dos
consultas medidas), tenemos la página, y **nadie optimiza para una falta de ortografía**. Es lo
más fácil de ganar que hay en toda la lista.

### Día 2 — vacunas, inglés, y las guías de fiebre

```
11  https://pedibot.xyz/es/vaccines/es
12  https://pedibot.xyz/vaccines/us
13  https://pedibot.xyz/vaccines/gb
14  https://pedibot.xyz/dose/paracetamol
15  https://pedibot.xyz/dose/tylenol
16  https://pedibot.xyz/es/dose/ben
17  https://pedibot.xyz/es/guides/fiebre_en_ninos_que_temperatura_es_preocupante
18  https://pedibot.xyz/es/guides/que_hago_si_mi_hijo_tiene_fiebre
19  https://pedibot.xyz/es/guides/puedo_alternar_paracetamol_e_ibuprofeno_para_la_fiebre
20  https://pedibot.xyz/guides/can_i_give_my_child_paracetamol_and_ibuprofen_together
```

## Un detalle que juega a favor ahora mismo

Las páginas de medicamento **cambiaron hoy**: llevan ya la calculadora de verdad con su fármaco
puesto, y el título dice «Calculadora de dosis de X por peso» en vez de «Dosis de X por peso».
Pedir la indexación de una página recién cambiada vale más que pedirla de una que lleva semanas
igual: Google la rastrea y encuentra algo nuevo.

## Lo que esto NO va a hacer

Pedir indexación mete la página en el índice. **No la sube de puesto.** De las que ya están
indexadas, la mayoría rondan el puesto 80. Esto sirve para que existan en la carrera, no para
ganarla — y con 780 páginas de las que solo 45 han salido alguna vez, existir es el primer paso.
