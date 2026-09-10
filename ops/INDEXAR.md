# Las URLs que pedir a mano en Search Console

Actualizado el **10-sep-2026**. **No están elegidas a ojo**: se le preguntó a Google, una por una, con
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

## 🔄 Vuelto a medir el 10-sep-2026

Preguntadas las 779 una por una otra vez. **Ha mejorado solo**: de las tandas del 7-sep, Google ya
tiene la mayoría sin que hiciera falta pedirlas — el anillo de enlaces internos del 9-sep hizo su
trabajo.

| Estado | URLs |
|---|---|
| Enviada e indexada | **557** |
| Google no reconoce la URL | 194 |
| Rastreada y descartada | 28 |

Las 194 desconocidas se concentran en los tres idiomas más nuevos (ru 44, pt 43, hi 41) y **no se
piden a mano**: son 194 días de cupo, y el anillo de enlaces las va metiendo solo. Las 28
rastreadas y descartadas tampoco: Google las vio y dijo que no, y volver a pedirlas casi nunca
cambia eso.

### Tanda de hoy — las 12 que sí valen el cupo

Elegidas cruzando con `config/drugs.yaml`: la mitad de las páginas de dosis sin indexar son
combinaciones idioma × marca sin público (`/hi/dose/doliprane`, `/ru/dose/dalsy`), y pedirlas es
gastar el cupo. Éstas son marcas que se venden donde se habla ese idioma, y páginas sueltas que
faltan enteras.

```
https://pedibot.xyz/pt/vaccines/br
https://pedibot.xyz/pt/vaccines/pt
https://pedibot.xyz/dose/tylenol
https://pedibot.xyz/pt/dose/tylenol
https://pedibot.xyz/es/dose/efferalgan
https://pedibot.xyz/es/dose/apirofeno
https://pedibot.xyz/es/dose/termalgin
https://pedibot.xyz/es/dose/motrin
https://pedibot.xyz/pt/emergency
https://pedibot.xyz/de/support
https://pedibot.xyz/de/diary
https://pedibot.xyz/ar/sources
```

**Por qué esas y no otras**: las páginas de marca son lo que más rinde del sitio —`/dose/nurofen`
158 impresiones en 90 días, `/es/dose/apiretal` 139, `/es/dose/dalsy` 107— y **Tylenol, que es la
marca de paracetamol infantil de Estados Unidos y de Brasil, no está indexada en ninguno de los
dos idiomas**. El calendario brasileño en portugués tampoco.

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
