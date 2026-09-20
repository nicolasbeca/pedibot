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

(más otras 23 páginas de calendario ya indexadas)

## Lo que esto NO hace

Pedir indexación mete la página en el índice. **No la sube de puesto.** De las que ya están
dentro, la mayoría rondan el 80. Esto sirve para que existan en la carrera, no para ganarla — y
con 780 páginas de las que solo 45 han salido alguna vez, existir es el primer paso.

Bing, Yandex, Seznam y Naver no necesitan nada de esto: `ops/indexnow.py` les avisa solo cada
mañana. Google es el único que exige la sesión del operador.

---

## Medido el 21-sep-2026, contra Search Console, y cambia la conclusión

Preguntado a Google directamente con la clave del proyecto, ventana de 28 días hasta el 17 de
septiembre, y comparado con la medición anterior (28 días hasta el 5 de septiembre):

| | 5-sep | 17-sep |
|---|---:|---:|
| impresiones | 392 | **1.837** |
| posición media | 74,3 | **65,6** |
| clics | 3 | 3 |

**La indexación no es el problema.** Las impresiones se han multiplicado casi por cinco en doce
días y la posición media ha subido nueve puestos, sin pedir nada a mano. El anillo de enlaces
internos del 9-sep y el tiempo están haciendo su trabajo solos.

**Lo que sí dice este dato, y es lo importante:** Google ya sabe qué es esta web y a quién
enseñársela. Lo que busca la gente que la ve es **dosis por marca**, y con diferencia:

| página | impresiones | posición |
|---|---:|---:|
| `/dose/nurofen` | 207 | 52,9 |
| `/es/dose/apiretal` | 152 | 78,0 |
| `/es/dose/dalsy` | 131 | 81,2 |
| `/dose/panadol` | 55 | 54,8 |
| `/fr/dose/doliprane` | 34 | 70,2 |
| `/de/dose/calpol` | 26 | **10,2** |

Y las consultas son exactamente eso: «calculadora apiretal», «calculadora dalsy», «dosis
ibuprofeno niños», «calpol dosage», «doliprane posologie», «dosage paracétamol par kg», «advil
dosage». Ni una sola consulta de chat, ni una sola de triaje. **Los padres buscan cuánto darle a
su hijo, y eso es justo lo que la web calcula con una tabla fija y la fuente delante.**

**Por qué están en la página 5 u 8 y no es por calidad.** Miré `/es/dose/dalsy` entera: 1.050
palabras, título y descripción correctos, seis preguntas que coinciden con lo que la gente
escribe, la tabla completa de 5 a 40 kg por concentración, y la AEPap citada. La página está
bien. Está en la posición 81 porque **el dominio tiene tres semanas y ningún enlace entrante**, y
compite contra el fabricante, los vademécums y los portales grandes. Eso no se arregla
escribiendo más: se arregla con tiempo y con que alguien enlace.

O sea que el cuello de botella **no está en la web**. Está en que nadie la enlaza todavía.

**Lo único con una acción clara aquí:** `/de/dose/calpol` está en la posición 10,2 para «calpol
deutsch», a un puesto de la primera página, y es lo más cerca que ha estado esto de tener sus
primeros clics de verdad. No es el gran salto —son 22 impresiones al mes—, pero es la única
página que está a un empujón.
