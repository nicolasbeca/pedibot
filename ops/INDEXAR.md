# Las URLs que pedir a mano en Search Console

Actualizado el 7-sep-2026. **No están elegidas a ojo**: se le preguntó a Google, una por una, con
la API de inspección de URL, cuáles de las páginas de más valor NO tiene.

**Todas van con la dirección completa, para copiar y pegar sin tocarlas.**

## Cómo se pide

Search Console → la barra de arriba **«Inspeccionar las URL de…»** → pegas la dirección → esperas
a que responda → **Solicitar indexación**.

### ⚠️ Hay un límite diario, y es de verdad

**Medido el 7-sep-2026: a la décima, Search Console dejó de aceptar.** No avisa antes; simplemente
la opción deja de estar disponible. La cuota se repone sola al día siguiente.

Por eso **los bloques de abajo van de diez en diez**: cada uno es una sesión. No intentes hacer
dos seguidos.

Va de una en una, y están en orden de valor medido, no de comodidad: empieza siempre por arriba
del primer bloque que te quede.

---

## ✅ Hechas el 7-sep-2026

```
https://pedibot.xyz/de/vaccines/de
https://pedibot.xyz/es/vaccines/es
https://pedibot.xyz/vaccines/us
https://pedibot.xyz/vaccines/de
https://pedibot.xyz/es/vaccines/gb
https://pedibot.xyz/es/vaccines/us
https://pedibot.xyz/es/vaccines/br
https://pedibot.xyz/vaccines/br
https://pedibot.xyz/vaccines/pt
https://pedibot.xyz/de/vaccines/br
```

Google tarda de días a un par de semanas en decidir. Se puede comprobar cuándo entran: la
inspección de URL lo dice, y el panel las contará en cuanto empiecen a salir.

---

## Tanda 2 — el resto de calendarios (mañana)

**Por qué esta categoría antes que nada:** es la que mejor posiciona de toda la web. Las dos únicas
consultas no de marca donde salimos por encima del puesto 30 son suyas — «calendario vacunal
alemania» en el **puesto 11** y «vacuna meningococo» en el **27** — frente al 88-95 de las guías.
De las 56 que hay (7 países × 8 idiomas), Google no conocía 31.

```
https://pedibot.xyz/fr/vaccines/br
https://pedibot.xyz/fr/vaccines/de
https://pedibot.xyz/fr/vaccines/gb
https://pedibot.xyz/fr/vaccines/pt
https://pedibot.xyz/pt/vaccines/br
https://pedibot.xyz/pt/vaccines/de
https://pedibot.xyz/pt/vaccines/pt
https://pedibot.xyz/pt/vaccines/us
https://pedibot.xyz/ar/vaccines/de
https://pedibot.xyz/ar/vaccines/fr
```

### Tanda 3 — diez más

```
https://pedibot.xyz/ar/vaccines/gb
https://pedibot.xyz/ar/vaccines/us
https://pedibot.xyz/ru/vaccines/br
https://pedibot.xyz/ru/vaccines/de
https://pedibot.xyz/ru/vaccines/es
https://pedibot.xyz/ru/vaccines/fr
https://pedibot.xyz/ru/vaccines/gb
https://pedibot.xyz/ru/vaccines/pt
https://pedibot.xyz/ru/vaccines/us
https://pedibot.xyz/hi/vaccines/de
```

### Tanda 4 — el último calendario, y las dosis en español

La otra demanda medida y no de marca: «calculadora apiretal» (6 impresiones), «apiretal
calculadora» (3), «calculadora ibuprofeno» (3), «calcular dosis apiretal» (2). Compiten contra
blogs, no contra el NHS — es la única categoría donde una web nueva puede ganar de verdad.

**`apirofeno` es la más fácil de ganar de toda la lista**: es *ibuprofeno* mal escrito, la gente
lo busca así (dos consultas medidas), tenemos la página, y nadie optimiza para una falta de
ortografía.

Y todas estas cambiaron el 6-sep: llevan ya la calculadora de verdad con su medicamento puesto, y
el título dice «Calculadora de dosis de X por peso». Pedir la indexación de algo recién cambiado
vale más que de algo que lleva semanas igual.

```
https://pedibot.xyz/hi/vaccines/us
https://pedibot.xyz/es/dose/apirofeno
https://pedibot.xyz/es/dose/nurofen
https://pedibot.xyz/es/dose/paracetamol
https://pedibot.xyz/es/dose/termalgin
https://pedibot.xyz/es/dose/efferalgan
https://pedibot.xyz/es/dose/panadol
https://pedibot.xyz/es/dose/advil
https://pedibot.xyz/es/dose/motrin
https://pedibot.xyz/es/dose/tylenol
```

### Tanda 5 — lo que queda

```
https://pedibot.xyz/es/dose/doliprane
https://pedibot.xyz/es/dose/ben
https://pedibot.xyz/dose/paracetamol
https://pedibot.xyz/dose/tylenol
https://pedibot.xyz/es/guides/fiebre_en_ninos_que_temperatura_es_preocupante
https://pedibot.xyz/es/guides/que_hago_si_mi_hijo_tiene_fiebre
https://pedibot.xyz/es/guides/puedo_alternar_paracetamol_e_ibuprofeno_para_la_fiebre
https://pedibot.xyz/guides/can_i_give_my_child_paracetamol_and_ibuprofen_together
```

---

## No las pidas: Google ya las tiene

```
https://pedibot.xyz/vaccines
https://pedibot.xyz/es/vaccines
https://pedibot.xyz/es/vaccines/de
https://pedibot.xyz/es/dose/apiretal
https://pedibot.xyz/es/dose/dalsy
https://pedibot.xyz/es/dose/alivium
https://pedibot.xyz/es/dose/calpol
https://pedibot.xyz/es/dose/gelocatil
https://pedibot.xyz/es/dose/junifen
https://pedibot.xyz/es/dose/tachipirina
https://pedibot.xyz/es/dose/tempra
https://pedibot.xyz/dose/calpol
https://pedibot.xyz/dose/nurofen
https://pedibot.xyz/dose/panadol
```

(más otros 23 calendarios ya indexados)

## Lo que esto NO hace

Pedir indexación mete la página en el índice. **No la sube de puesto.** De las que ya están
dentro, la mayoría rondan el 80. Esto sirve para que existan en la carrera, no para ganarla — y
con 780 páginas de las que solo 45 han salido alguna vez, existir es el primer paso.

Bing, Yandex, Seznam y Naver no necesitan nada de esto: `ops/indexnow.py` les avisa solo cada
mañana. Google es el único que exige la sesión del operador.
