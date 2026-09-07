# Las URLs que pedir a mano en Search Console

Actualizado el 7-sep-2026. **No están elegidas a ojo**: se le preguntó a Google, una por una, con
la API de inspección de URL, cuáles de las páginas de más valor NO tiene.

## Cómo se pide

Search Console → la barra de arriba **«Inspeccionar las URL de…»** → pegas la dirección → esperas
a que responda → **Solicitar indexación**.

Va de una en una y el límite ronda las **10-12 al día por propiedad**. Empieza por arriba: están
en orden de valor medido, no de comodidad.

---

## Prioridad 1 — los calendarios de vacunas

**Por qué esta categoría antes que nada:** es la que mejor posiciona de toda la web. Las dos únicas
consultas no de marca donde salimos por encima del puesto 30 son suyas — «calendario vacunal
alemania» en el **puesto 11** y «vacuna meningococo» en el **27** — frente al 88-95 de las guías.
Google considera estas páginas competitivas.

**Y de las 56 que hay (7 países × 8 idiomas), no conoce 31.** No es un problema de calidad: es que
más de la mitad no existen para él.

Ordenadas por el público que de verdad tenemos medido (Alemania se lleva 116 de las 235
impresiones del mes; España, 51):

```
 1  https://pedibot.xyz/de/vaccines/de     ← la más valiosa de toda la lista
 2  https://pedibot.xyz/es/vaccines/es
 3  https://pedibot.xyz/vaccines/us
 4  https://pedibot.xyz/vaccines/de
 5  https://pedibot.xyz/es/vaccines/gb
 6  https://pedibot.xyz/es/vaccines/us
 7  https://pedibot.xyz/es/vaccines/br
 8  https://pedibot.xyz/vaccines/br
 9  https://pedibot.xyz/vaccines/pt
10  https://pedibot.xyz/de/vaccines/br
```

La primera merece la explicación: **`/es/vaccines/de` está en el puesto 11 y `/de/vaccines/de` —la
misma página, en alemán— Google ni la conoce.** Alemania es donde más nos muestra, y ahí no
tenemos nada indexado sobre su propio calendario.

### Día 2 — el resto de calendarios

```
/fr/vaccines/br   /fr/vaccines/de   /fr/vaccines/gb   /fr/vaccines/pt
/pt/vaccines/br   /pt/vaccines/de   /pt/vaccines/pt   /pt/vaccines/us
/ar/vaccines/de   /ar/vaccines/fr   /ar/vaccines/gb   /ar/vaccines/us
```

Y si quedan turnos: `/ru/vaccines/{br,de,es,fr,gb,pt,us}` y `/hi/vaccines/{de,us}`.

---

## Prioridad 2 — dosis por marca en español

La otra demanda medida y no de marca: «calculadora apiretal» (6 impresiones), «apiretal
calculadora» (3), «calculadora ibuprofeno» (3), «calcular dosis apiretal» (2). Compiten contra
blogs, no contra el NHS — es la única categoría donde una web nueva puede ganar de verdad.

```
/es/dose/apirofeno      ← ibuprofeno mal escrito: la gente lo busca así, y nadie
/es/dose/nurofen           optimiza para una falta de ortografía
/es/dose/paracetamol
/es/dose/termalgin
/es/dose/efferalgan
/es/dose/panadol
/es/dose/advil
/es/dose/motrin
/es/dose/tylenol
/es/dose/doliprane
```

Estas páginas **cambiaron el 6-sep**: llevan ya la calculadora de verdad con su medicamento
puesto, y el título dice «Calculadora de dosis de X por peso». Pedir la indexación de algo recién
cambiado vale más que de algo que lleva semanas igual.

---

## Prioridad 3 — las guías de fiebre y dosis

```
/es/guides/fiebre_en_ninos_que_temperatura_es_preocupante
/es/guides/que_hago_si_mi_hijo_tiene_fiebre
/es/guides/puedo_alternar_paracetamol_e_ibuprofeno_para_la_fiebre
/guides/can_i_give_my_child_paracetamol_and_ibuprofen_together
```

---

## No las pidas: ya están indexadas

`/es/dose/apiretal` · `/es/dose/dalsy` · `/es/dose/alivium` · `/es/dose/calpol` ·
`/es/dose/gelocatil` · `/es/dose/junifen` · `/es/dose/tachipirina` · `/es/dose/tempra` ·
`/dose/calpol` · `/dose/nurofen` · `/dose/panadol` · `/es/vaccines` · `/vaccines` ·
`/es/vaccines/de` · y otros 23 calendarios.

## Lo que esto NO hace

Pedir indexación mete la página en el índice. **No la sube de puesto.** De las que ya están
dentro, la mayoría rondan el 80. Esto sirve para que existan en la carrera, no para ganarla — y
con 780 páginas de las que solo 45 han salido alguna vez, existir es el primer paso.

Bing, Yandex, Seznam y Naver no necesitan nada de esto: `ops/indexnow.py` les avisa solo cada
mañana. Google es el único que exige la sesión del operador.
