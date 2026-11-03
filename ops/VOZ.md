# VOZ.md — cómo escribe Nicolas, y el filtro antes de que salga un texto

> 3-nov-2026. Wayan Vota (ICTworks) devolvió el borrador del artículo: «This reads as if it was
> written by AI… It sounds like a copy-paste from AI. Please add your own color to the words.» No
> era la primera vez: el 14-oct el operador leyó la tercera tanda y dijo «a veces parece muy IA».
> Pidió un perfil de cómo habla él y un filtro por el que pase todo lo que salga con su nombre.

## Cuándo se usa

**Todo texto que sale con su nombre**, de cualquier proyecto: correos, artículos, respuestas en
hilos, posts, formularios con texto libre. Dos pasos, siempre los dos:

1. **El filtro mecánico**: `python ops/voz.py cuerpo.txt [otro.txt …]` (con `--palabras 800`
   para un artículo). Con varios ficheros mira también la tanda junta. `ops/correo.py` lo pasa solo
   y **no envía** si algo «para»; `--sin-filtro` lo salta, a sabiendas y diciéndolo.
2. **La pasada humana**: la lista de «Cómo se reescribe», leyendo el texto como si lo dijera él.

El filtro mecánico encuentra lo que se puede contar. Lo que más delata a una IA no se puede contar:
que el texto no tenga nada que sólo esta persona le diría a esta otra. Eso es el paso 2.

## Lo que el filtro no hace

- **No inventa vida.** Lo que hace humano un texto largo son cosas que sólo él sabe: por qué empezó,
  una noche concreta, qué le sorprendió, en qué se equivocó. Para un artículo se le piden tres o
  cuatro detalles de verdad (con dos minutos de audio basta) y se escriben con sus palabras.
  Nunca se inventa una anécdota, una noche o un hijo con fiebre.
- **No es para colar nada.** Donde una publicación pide textos no escritos con IA (Think Global
  Health), lo escribe él. Wayan, en cambio, dice que usar IA está bien si se nota que una persona
  lo ha hecho suyo: ahí sí sirve.

## Cómo escribe (447 mensajes suyos, sep-nov 2026)

Contado sobre unas 19.000 palabras de sus mensajes en las sesiones:

| | |
|---|---|
| palabras por frase (mediana) | 9 (el 90 % por debajo de 23) |
| rayas largas | 0 |
| «por favor» / «gracias» | 0 / 2 |
| «tenemos» · «mejor» · «cosas» · «tipo» | 61 · 45 · 40 · 33 |
| «vamos a» · «me gusta / no me gusta» · «dime» | 30 · 27 · 25 |
| «creo que» · «demasiado» · «por ejemplo» | 20 · 18 · 17 |

Los rasgos, con frases suyas:

1. **Va al grano y abre con lo que pasa**, no con quién es. «El problema que tenemos ahora mismo es
   que ganamos muchas veces poco dinero, pero cuando perdemos, perdemos mucho.» «Lo que me preocupa
   es estar entrando mal.»
2. **Explica con un ejemplo y la cuenta hecha.** «Sabemos que nuestras obras rondan entre 10 y 80
   millones. Un 1 % de negociación son entre 100.000 y 800.000 € de ahorro directo.» «Hoy por hoy un
   comparativo cuesta 4-5 días de trabajo intenso.»
3. **Frases cortas.** Cuando se alarga, encadena hablando: «con lo cual», «es decir», «eso por un
   lado; por otro lado», «simplemente».
4. **Dice lo que no sabe.** «No sé», «entiendo que», «creo que», «quizás». Pregunta cuando duda.
5. **Opina claro y en corto.** «Me gusta bastante como está.» «No aporta mucho.» «Le damos demasiado
   bombo.» «No tiene sentido.»
6. **Humor contra sí mismo, poco y de verdad.** «Dime cómo lo configuro paso a paso como si fuera
   tonto.» «Tengo un poquito de trastorno obsesivo compulsivo.»
7. **Plural de equipo en lo de la empresa** («tenemos», «hacemos»); en PediBot es él solo: «I», «yo».
8. **Cero adorno.** Ni «estaré encantado», ni «es un placer», ni superlativos. Agradece con hechos.
9. **Registro medio-alto, culto sin ser técnico.** Palabras normales y precisas («volumetría»,
   «recodifican», «homogeneizadas»); si una es técnica, la explica en media línea.

Hacia fuera, su voz pero escrita: con tildes, signos de apertura y sin faltas. En inglés y francés,
igual de directo y de corto; el inglés que escribe no es nativo y no tiene que parecerlo.

## Lo que delata a una IA

Recogido de la guía de Wikipedia «Signs of AI writing» (la más completa, actualizada en 2026), de
Maldita.es y de guías de correo en frío (Hunter, Unify, Lilach Bullock, 2025-2026), más lo que el
operador ya marcó. **PARA** = `voz.py` no lo deja salir. **ojo** = avisa; se reescribe salvo motivo.

**Forma**
- PARA: rayas largas (— y –), en cualquier lengua. Para rangos, «6-8» o «de 6 a 8».
- PARA: listas, números de apartado, negritas, almohadillas. Un correo es prosa.
- PARA: comillas curvas inglesas (“ ” ’). Las españolas « » y las francesas valen.
- ojo: más de 170 palabras en un correo; frases de más de 35.
- ojo: todos los párrafos del mismo largo, todo demasiado pulido y uniforme.

**Frases hechas**
- PARA: «I hope this message finds you well», «I'd be really grateful», «Thank you for the work you
  do», «I'm reaching out», «Don't hesitate to», «Looking forward to hearing from you», «Espero que
  este correo te encuentre bien», «No dudes en contactarme», «Quedo a tu disposición», «Es importante
  destacar», «En el mundo actual», y sus hermanas en francés, alemán y portugués.
- ojo: vocabulario de IA: crucial, pivotal, robust, seamless, leverage, foster, delve, landscape,
  testament, showcase, underscore, vibrant; fundamental, clave, sin duda, cabe destacar, en
  definitiva, fomentar, potenciar, abordar, panorama, ecosistema.

**Estructuras**
- ojo: «no solo… sino también», «it's not X, it's Y», «more than just»: corregir algo que nadie ha
  dicho. La más reconocible, y la que más usa el modelo nuevo («X rather than Y»).
- Tríos: tres adjetivos, tres cosas, tres idiomas entre paréntesis. Dos o cuatro suenan a persona.
- Volver al final a lo que ya se dijo (el resumen de despedida).
- Cautelas de más: «podría», «parece que», «en principio» en cada frase.
- ojo: **abrir presentándose** («Soy Nicolas Beca y escribo desde Sevilla»).

**La tanda** (sólo se ve juntándolos; `voz.py` con varios ficheros)
- ojo: varios correos que empiezan igual.
- ojo: **la misma frase del producto en tres o más** («PediBot, una web gratuita que contesta…»,
  «con la fuente debajo de cada respuesta»). La tanda del 30-oct pasaba limpia correo a correo, y
  los diez abrían presentándose y repetían el folleto: eso es lo que vio Wayan.
- El mismo esqueleto en todos: presentación → dato → enlace → «si te sirve» → firma.

**Lo de fondo** (lo que no se cuenta y más pesa, según las guías de correo en frío)
- Que no se note por qué le escribes a ESTA persona y no a otra.
- Generalidades positivas en vez de un hecho raro y concreto.
- Pedir varias cosas, o ninguna clara.

## Cómo se reescribe

1. **Leerlo como si lo dijera él por teléfono.** Lo que no diría, fuera.
2. **La primera frase es para el otro**: el dato, lo que vio en su web, la razón de escribirle.
   Quién soy, después y en media línea («Lo hago yo, desde Sevilla, en mi tiempo libre»).
3. **Una sola petición**, al final, en una frase.
4. **Algo que sólo vale para ese destinatario**: su país, su programa, algo que publicaron.
5. **Cortar un tercio.** Si un párrafo se quita y no se pierde nada, se quita.
6. **Variar la tanda**: unos abren con el dato, otros con una pregunta, otros con lo que vi en su
   web; de 50 a 150 palabras; cierres distintos; la descripción del producto, con otras palabras
   cada vez o sin ella.
7. **Una frase sin verbo o una coletilla** está bien («Misma marca.», «la verdad», un paréntesis).
   Faltas de ortografía, no.
8. **Números como los diría él**: «unas cuatro veces», «casi 300», con la cuenta hecha.
9. **Lo de folleto, una vez y no en todos**: «gratis, sin anuncios ni registro».
10. **Si es largo (un artículo)**: pedirle sus detalles antes de escribir, no después.

## Un ejemplo

Antes (Maldita, 30-oct):

> Soy Nicolas Beca y escribo desde Sevilla. Hago PediBot, una web gratuita que contesta las dudas de
> salud de los niños solo con guías publicadas (la AEPap, la SEUP, el NHS...) y pone la fuente debajo
> de cada respuesta. Te escribo por algo que me encontré haciendo la calculadora de dosis y que creo
> que da para una pieza de Maldita Ciencia.

Después:

> El Gelocatil para niños viene en gotas de 100 mg por ml y en jarabe de 120 mg por 5 ml. Misma
> marca, y las gotas son unas cuatro veces más fuertes. Me di cuenta haciendo la calculadora de dosis
> de PediBot, una web que hago desde Sevilla en mis ratos libres.

## Fuentes

- Wikipedia, «Signs of AI writing»: https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing
- Maldita.es, cómo detectar textos generados con IA (2024-2025):
  https://maldita.es/malditatecnologia/20250917/detectar-textos-generados-inteligencia-artificial/
- Hunter, «How to use AI in your emails without losing your voice»:
  https://hunter.io/blog/how-to-use-ai-in-your-emails-without-losing-your-voice/
- Unify, «Outreach that sounds human»: https://www.unifygtm.com/explore/outreach-that-sounds-human
- Lilach Bullock, por qué los correos fríos con IA suenan todos igual:
  https://www.lilachbullock.com/ai-cold-emails-sound-the-same/

Las guías coinciden en que ningún rasgo suelto prueba nada (las personas también usan rayas y
tríos) y en que los detectores automáticos fallan. Por eso el filtro sólo para lo que nadie
echaría de menos, y lo demás es una lista para leer con cabeza.
