# APP.md — PediBot en el móvil, de verdad

> Primer borrador, 19-sep-2026, escrito para que lo revises tú. Lo que pediste: «vamos a crear
> una app basada en el web. Mismas herramientas, etc, pero optimizado para móvil. Haz un plan de
> adaptación y de publicación en Google Store y Apple Store. El logo debe ser LOGO_PEDIBOT_CARA
> no uno inventado».
>
> **Actualizado esa misma tarde.** Lo que empezó siendo todo plan ya no lo es del todo: los
> iconos salen de tu JPG (§2), la web funciona sin cobertura y se puede instalar (F1, §6), y la
> cuenta de familia con los hijos y su curva está construida y desplegada (§4 ter). Sigue siendo
> plan la carcasa nativa y todo lo de las tiendas. Tus cuatro decisiones están en §10, ya
> contestadas.

---

## 1. La pregunta que hay que contestar antes de escribir una línea

Apple la hace por escrito, en la directriz 4.2 de su guía de revisión, y la cito entera porque
es el criterio con el que van a mirar esto:

> «Your app should include features, content, and UI that elevate it beyond a repackaged
> website. If your app is not particularly useful, unique, or "app-like", it doesn't belong on
> the App Store.»

O sea: si la app es pedibot.xyz metido en una ventana, la rechazan. Y tendrían razón, porque el
sitio ya se ve bien en un móvil. **Así que la app tiene que hacer algo que la web no puede**, y
la buena noticia es que ese algo existe y es grande:

**Sin cobertura, la web es una pantalla en blanco. La app no.**

Piensa en dónde queremos estar: India, el mundo árabe, África. El proyecto tiene desde esta
semana 88 países con número de emergencias, 61 calendarios de vacunas y 69 tablas de
crecimiento, y una parte enorme de las madres a las que eso les sirve tienen un Android barato
con datos que se acaban a mitad de mes. Una madre en Kisumu a las tres de la mañana, sin saldo,
no puede abrir una web. Pero puede abrir una app que ya tiene dentro el número al que llamar en
Kenia, los signos de alarma que significan ir ya, y la fecha de la próxima vacuna de su hija.

Lo medí antes de proponerlo. Todo lo que el proyecto sabe, menos el chat, cabe en el teléfono:

| Lo que se guardaría dentro | Tamaño |
|---|---|
| `vaccines.json` — 61 calendarios | 568 KB |
| `checklist.json` — los signos de alarma, en 8 idiomas | 29 KB |
| `emergency.json` — 88 países | 29 KB |
| `growth_charts.json` + tablas OMS | 26 KB |
| `drugs.json` + `dose_table.json` | 24 KB |
| Las 502 guías en markdown (las 8 lenguas) | 4,9 MB |
| **Total, con todas las lenguas** | **~5,6 MB** |

Una app de menos de 20 MB con todo eso dentro. Si además se descargan las guías sólo del idioma
del teléfono, bajamos de 10 MB, que es el umbral por debajo del cual la gente se instala cosas
con datos móviles en Nigeria o en India.

Lo único que necesita red es el chat, porque la respuesta la escribe un modelo que vive en el
VPS. Y eso está bien: sin red, la app dice lo que sabe y no finge.

---

## 2. El logo, que es lo primero que pediste y ya está hecho

Tenías razón en la queja. `web/site/public/logo.svg` era **un dibujo mío**: un bocadillo redondo
con la cara descentrada y una oreja, hecho con elipses y arcos copiando de memoria. Se parecía
lo bastante como para que no saltara a la vista, y por eso llevaba semanas ahí. El de verdad
—`LOGOS/LOGO_PEDIBOT_CARA.jpg`, 471×428— tiene el bocadillo con el rabo abajo a la izquierda, la
cara centrada y el rizo arriba.

Hoy se ha escrito `scripts/make_icons.py`, que saca **todo** de tu archivo y de ningún otro:

```
web/site/public/logo.png            512 px, fondo transparente
web/site/public/logo-192.png        192 px
web/site/public/apple-touch-icon.png 180 px, sobre blanco (iOS no admite transparencia)
web/site/public/favicon.ico         16/32/48
web/site/public/og.png              la tarjeta de compartir, con la cara de verdad
app/assets/icon-1024.png            App Store y Play Store
app/assets/adaptive-foreground.png  432 px, icono adaptativo de Android
app/assets/android/mipmap-*.png     48, 72, 96, 144, 192
```

Dos cosas que merecen estar escritas, porque son las que hacen que esto no se vuelva a torcer:

1. **No vale un «blanco a transparente»**: la cara del bebé es crema, (255, 249, 235), a seis
   niveles del blanco del fondo. Cualquier umbral que borre el fondo se come la cara. Lo que
   hace el script es una inundación desde las cuatro esquinas, como la varita mágica, que sólo
   alcanza el blanco pegado al borde.
2. **Los iconos de la web y los de la app salen de la misma línea de código**, con el mismo
   recorte. Es lo que impide que dentro de seis meses la app y la web tengan caras distintas.

Ya no queda ningún SVG dibujado por mí en el proyecto: `logo.svg` y `favicon.svg` están
borrados.

---

## 3. La decisión técnica: la web que ya existe, dentro de una carcasa nativa

**Propuesta: Capacitor.** El sitio Astro que ya tenemos se empaqueta tal cual dentro de una app
nativa de Android y de iOS, y desde JavaScript se llama a lo nativo (notificaciones, cámara,
llamada de teléfono, sistema de archivos) con las mismas APIs en las dos plataformas.

Es lo que pediste con «mismas herramientas». Y las alternativas las descarto por escrito para
que se pueda discutir:

| Camino | Por qué no |
|---|---|
| Reescribir en React Native / Flutter | Son 2.598 páginas en 8 idiomas y 8.454 pruebas que ya funcionan. Reescribir la interfaz duplica la superficie donde puede haber un fallo, y en este proyecto un fallo es un número de emergencias equivocado. Además tardaría meses, no semanas. |
| PWA sola, sin tienda | Funciona y es gratis, pero en iOS las notificaciones de una PWA son un campo de minas y, sobre todo, **no sales en la tienda**. Y estar en la tienda es la mitad del motivo: «pedibot» buscado en Play es un canal que hoy no existe. |
| TWA (Trusted Web Activity) | Sólo Android, y es literalmente la web en una ventana: se estrella contra la 4.2 el día que intentemos lo mismo en Apple. |
| Capacitor | Reutiliza todo, publica en las dos tiendas, y deja añadir lo nativo que justifica que sea una app. **Esta.** |

La estructura quedaría así, sin tocar nada de lo que ya hay:

```
app/
  assets/            ← ya está, sale de tu logo
  capacitor.config.ts
  android/           ← proyecto Android generado
  ios/               ← proyecto Xcode generado
  www/               ← aquí se copia web/site/dist + los datos empaquetados
  src/
    offline.ts       ← qué se guarda y cuándo se refresca
    notifications.ts ← los recordatorios de vacunas
    native.ts        ← llamar, compartir, cámara
```

Identificador: `xyz.pedibot.app` en las dos tiendas, para que coincida con el dominio.

---

## 4. Qué hace la app que la web no hace

Esta lista es, a la vez, la lista de funciones y la defensa ante la directriz 4.2 de Apple.

1. **Todo menos el chat, sin conexión.** Números de emergencia de los 88 países, los signos de
   alarma, los 61 calendarios, las 69 curvas, las tablas de dosis y las 502 guías. Sin red, la
   app abre igual y lo dice arriba: «sin conexión: esto es lo que llevas dentro».
2. **Recordatorios de vacunas.** Metes la fecha de nacimiento **en el teléfono, que no sale de
   ahí**, y la app avisa tres días antes de cada cita del calendario de tu país. Es lo que más
   me piden los calendarios y lo que una web no puede hacer.
3. **Llamar de un toque.** El número de emergencias del país elegido, en un botón fijo, que
   marca. Con el niño en brazos, marcar tiene que ser un toque.
4. **El diario de síntomas, en el dispositivo.** Hoy vive en el `localStorage` del navegador, que
   se borra cuando el navegador quiere. En la app es un fichero suyo.
5. **La cámara de verdad**, para la foto de una erupción, en vez del selector de archivos.
6. **Estar en la pantalla de inicio.** Suena a poco y no lo es: la diferencia entre «¿cómo se
   llamaba aquella web?» y un icono con la cara del bebé.

---

## 4 bis. La regla de oro: si se toca la web, se toca la app

Tuya, del 19-sep-2026, y la pongo aquí arriba porque es la que más fácil se incumple:
**cada vez que actualicemos la web hay que actualizar la app.** Dos productos con el mismo
nombre que dicen cosas distintas sobre la misma vacuna es peor que tener uno solo.

La buena noticia es que el diseño de §3 hace que casi todo se arrastre solo: la app lleva dentro
**el mismo `web/site/dist`**, así que un arreglo en un componente o una guía nueva no se
reescribe dos veces. Pero «casi todo» no es «todo», y esto es lo que hay que tener claro:

| Lo que cambia | ¿Llega a la app sin publicar en la tienda? |
|---|---|
| Guías, textos, respuestas del chat | **Sí**, el chat y las guías se piden al servidor cuando hay red |
| Los datos que van dentro (vacunas, emergencias, curvas, dosis) | **Sí**, si se refrescan en segundo plano — hay que construirlo así desde el primer día (§F1) |
| La interfaz: componentes, páginas, estilos | **No**: viajan dentro del paquete. Hace falta una versión nueva |
| Una lengua nueva, una regla de triaje nueva | La regla es del servidor y llega sola; la **traducción** de la interfaz, no |
| Los iconos, el nombre, los permisos | **No**: versión nueva y revisión de la tienda |

De ahí salen tres cosas que hay que montar y que no son opcionales:

1. **Un solo origen de los datos.** Los JSON de `web/site/src/data/` son los que se empaquetan;
   nadie copia un fichero a mano dentro de `app/`. Lo hace el script del empaquetado.
2. **Refresco en segundo plano con fecha a la vista.** La app se trae los datos nuevos cuando hay
   red y **escribe en pantalla de cuándo es lo que estás leyendo**. Un calendario de vacunas de
   hace ocho meses guardado en un teléfono es peor que no tenerlo.
3. **Una prueba que compare las dos.** Igual que hoy hay pruebas que leen el HTML construido,
   tiene que haber una que falle si lo empaquetado en la app no coincide con lo publicado en la
   web. Mientras no exista, esto es una promesa; con ella, es una comprobación.

Y en lo operativo: la lista de despliegue (`ops/deploy.sh`) pasa a tener **dos destinos**. Hoy
«desplegar» es el VPS; a partir de la app, desplegar es el VPS **y** decidir si eso pide una
versión nueva en las tiendas. La columna de la tabla de arriba es esa decisión, escrita.

## 4 ter. La ficha del niño — **ya construida en la web** (19-sep-2026)

> Esto se escribió por la mañana como «lo que viene después». Por la tarde el operador decidió
> hacerlo, y saltándose la fase 1: «fase 2 directamente. La cuenta puede ser simplemente un email
> y una contraseña». Así que ya está en pedibot.xyz y la app se lo encuentra hecho.

Lo que hay hoy en la web, y que la carcasa de §3 hereda sin escribir una línea:

- **cuenta opcional** con correo y contraseña (`/family` en los ocho idiomas), sesión en cookie
  `HttpOnly`, contraseña guardada como `scrypt`;
- **una ficha por hijo** —nombre, fecha de nacimiento, sexo, país— y su historial de medidas;
- **su curva** sobre las bandas de percentiles de la OMS, dibujada en SVG sin bibliotecas;
- **el chat contesta por su edad**: «¿qué vacunas le tocan a Laura?» sale respondida por la edad
  de Laura, y la respuesta dice con qué hijo y con qué edad contestó;
- **descargar y borrar** en un botón, y el boletín como casilla aparte.

Lo que eso cambia en este plan:

1. **D-A3 (recordatorios de vacunas) ya tiene de dónde salir.** La fecha de nacimiento está en
   la cuenta, así que la F4 deja de ser «guardar una fecha en el teléfono» y pasa a ser «pedir
   las fechas al servidor y programar la notificación local». Menos trabajo y sin datos
   duplicados en dos sitios.
2. **Las dos fichas de tienda cambian, y ya sabemos exactamente cómo.** Hay cuenta, hay correo y
   hay datos de salud de un menor identificado: en el formulario de *Data safety* de Google eso
   se declara como *Personal info → Email address* y *Health and fitness → Health info*, con
   «recogido», «no compartido con terceros» —salvo lo que ya se declaraba del proveedor del
   modelo para el texto del chat— y con borrado a petición del usuario, que es cierto porque el
   botón existe. En la etiqueta de Apple, *Health & Fitness* y *Contact Info*, **vinculados a la
   identidad** (hay cuenta), sin seguimiento.
3. **Falta una pieza para poder prometer lo normal de una cuenta**: verificar el correo,
   recuperar una contraseña olvidada y mandar el boletín necesitan un proveedor de correo
   saliente, que el proyecto no tiene. Está anotado como I-20 en `IDEAS.md` y es una decisión del
   operador (proveedor y quién paga). Mientras tanto, el alta funciona en el acto y quien pierda
   la contraseña no puede recuperarla: eso hay que resolverlo **antes** de anunciar la cuenta a
   mucha gente.

## 4 quater. Lo que viene después: lo que la ficha dejó a medias

Pedido por el operador el mismo 19-sep y anotado en `IDEAS.md` (I-16 a I-19): **darse de alta,
en la web y en la app, para guardar los datos de cada hijo y llevar su curva de peso y talla**,
de forma que el bot los use directamente en vez de preguntarlos cada vez.

No se construye ahora, pero se nombra aquí por dos motivos que sí afectan a lo de arriba:

1. **La fase 1 de esa idea es la misma pieza que D-A3.** Los recordatorios de vacunas necesitan
   una fecha de nacimiento guardada en el aparato; la ficha del niño es esa misma fecha con tres
   campos más y un historial de medidas. Si la F4 se construye pensando en la ficha y no en «una
   fecha suelta para las notificaciones», la idea siguiente sale casi gratis.
2. **La fase 2, la cuenta, cambia las dos fichas de tienda.** Hoy declaramos que no hay cuenta y
   que no se piden datos personales. Con cuenta, entran datos de salud de un menor identificado
   —categoría especial del RGPD— y hay que rehacer el formulario de *Data safety* de Google, la
   etiqueta de privacidad de Apple y la página `/legal` en ocho idiomas. **Mejor saberlo antes de
   rellenar los formularios que después.**

La recomendación que está escrita en `IDEAS.md`: todo en el aparato primero, sin cuenta, que es
el 90 % del valor sin tocar la promesa del proyecto; y la cuenta sólo para no perderlo al cambiar
de teléfono, opcional y cifrada en el cliente.

## 4 quinquies. La cartilla de vacunación — **ya construida en la web** (20-sep-2026)

Cada visita del calendario del país tiene una casilla: el padre marca lo que ya le han puesto y
lo que queda sin marcar sale como **«no consta»**, con una lista aparte y una frase que dice qué
hacer con ella («llévala al centro de salud, lo que falte se puede poner al día»).

Por qué importa para la app más que para la web, que es lo que hay que recordar cuando se
construya:

1. **Es la pantalla que se usa sin cobertura.** Un padre en una sala de espera marcando cuatro
   visitas no tiene wifi. En la web hace falta red para guardar; en la app esto tiene que
   guardarse en el aparato y sincronizar cuando haya señal. Si se construye al revés, la función
   deja de servir justo donde más falta hace.
2. **Es lo que da sentido a los recordatorios (D-A3).** Avisar de una vacuna que ya se puso es la
   forma más rápida de que el padre apague los avisos. Con la cartilla, el aviso sabe callarse.
3. **La visita se identifica por la EDAD, nunca por el nombre de la vacuna.** El ministerio
   cambia de producto y el nombre cambia con él; la edad del calendario no. Una cartilla guardada
   por nombre se rompe sola el día que el país pase de pentavalente a hexavalente, y con ella el
   histórico de cada niño. Esto ya está así en la web y la app **tiene que copiarlo tal cual**.
4. **Nada de esto regaña.** «No consta» y no «atrasada»: mientras el padre no marque, lo único
   que sabemos es que no lo sabemos. En una notificación esa diferencia es aún más grande que en
   una pantalla.

Por dentro: tabla `doses` en `data/pedibot_familias.db`, endpoints `POST`/`DELETE` en
`/api/family/children/{id}/doses`, estados `done` · `pending` · `due` · `future` · `seasonal` en
`schedule_for_child()`, y el `.ics` ya no repite lo que está puesto.

## 5. Lo que hay que optimizar para el móvil

La web es adaptable, pero adaptable no es lo mismo que pensada para un pulgar. Lo que revisaría,
por orden de lo que más se nota:

- **El pulgar manda.** La caja de escribir, el micro y la cámara, abajo; los selectores de país,
  edad y peso, donde están ahora, pero más altos (44 px mínimo de zona tocable, que es lo que
  pide Apple y lo que hace falta con el móvil en una mano).
- **El país, ya arreglado hoy** (§8): bandera y nombre, y el buscador en los listados largos.
- **Las tablas de vacunas** en pantalla estrecha: hoy son una tabla de dos columnas que se
  aprieta; en la app deberían ser tarjetas por edad.
- **Árabe y hebreo de derecha a izquierda** ya funcionan en la web; hay que comprobarlos dentro
  de la carcasa, donde la dirección la fija también el sistema.
- **Hindi y árabe necesitan que la fuente viaje dentro de la app**, no descargada de Google
  Fonts: sin red, si la fuente no está, el texto sale en cuadraditos.
- **Modo noche**, ya está, y en el móvil a las tres de la mañana es lo que se usa.
- **Peso de la primera apertura**: la app no debe pedir red para pintar la primera pantalla.

---

## 6. Las fases, con lo que cuesta cada una

Los días son días de trabajo míos, seguidos, sin contar lo que tarda la tienda en responder.

| Fase | Qué | Días |
|---|---|---|
| **F0** | Iconos desde el logo real | **hecho el 19-sep** |
| **F1** | La web se vuelve PWA: `manifest.webmanifest`, service worker, pantalla de «sin conexión» en los ocho idiomas, instalable desde el móvil. | **hecho el 19-sep** |
| **F1b** | Empaquetar los datos (vacunas, emergencias, curvas, dosis) para que estén ANTES de que el lector visite esa página, y refrescarlos en segundo plano con la fecha a la vista. | 2 |
| **F2** | Carcasa Capacitor: proyectos Android e iOS, iconos, pantalla de arranque, que abra y navegue. | **a medias el 19-sep**: `app/capacitor.config.json`, `app/package.json` y el empaquetado (`app/scripts/copy-web.mjs`) hechos y probados. Falta generar los proyectos nativos, y para eso hace falta la máquina (ver abajo) |
| **F3** | Lo nativo: llamada de un toque, compartir, cámara, y el diario en el dispositivo. | 2 |
| **F4** | Recordatorios de vacunas (fecha de nacimiento local, notificaciones, el ajuste para apagarlos). | 3 |
| **F5** | Pulido móvil (§5) y pruebas en pantallas pequeñas de verdad. | 3 |
| **F6** | Fichas de tienda en los 8 idiomas, capturas, textos, formularios de privacidad. | **casi hecha el 19-sep**: todo escrito y medido en `app/TIENDAS.md` (nombre, descripciones, palabras clave, los dos formularios de privacidad y las notas para el revisor de Apple). Faltan las capturas, que hay que hacer con la app delante, y seis traducciones de la descripción larga |
| **F7** | Pruebas cerradas de Play (12 probadores, 14 días naturales) y TestFlight. | 14 días de reloj |
| **F8** | Envío, revisión y respuesta a lo que rechacen. | 3–10 días de reloj |

**En claro: unas tres semanas de trabajo y entre cuatro y seis semanas de calendario**, mandando
casi todo la espera obligatoria de Google.

### Lo que va DENTRO del paquete, y por qué no va todo (19-sep-2026)

El sitio entero son **81 MB**: 2.607 páginas en ocho idiomas, cada una con su CSS y su
navegación dentro. Meterlo todo daría una app que en Lagos o en Delhi nadie se instala con datos
móviles, que es justo el público al que va. Así que `app/scripts/copy-web.mjs` elige, y elige por
la pregunta que da sentido a la app: **¿qué hace falta a las tres de la mañana sin cobertura?**

| Va dentro | Cuánto |
|---|---|
| Las 88 fichas de emergencia por país, en los ocho idiomas | 17 MB |
| Los datos en bruto (`offline-data/`: emergencias, calendarios, curvas, dosis, signos de alarma) | 0,7 MB |
| Las portadas, `/legal`, `/family`, `/kit`, `/diary` y la pantalla de sin conexión, en los ocho | ~2 MB |
| Tipografías, estilos e iconos | 0,1 MB |
| **Total** | **20,6 MB** |

Fuera se quedan las guías (14 MB), las fichas de dosis por marca y los calendarios y curvas país
por país: **siguen funcionando con red**, y el service worker guarda lo que cada uno abra. No es
que no quepan; es que no es lo que se busca a oscuras.

### Lo que falta para compilar, y no depende de escribir código

En este PC hay **Java 8 y ningún SDK de Android**, así que la carcasa se puede montar pero no
compilar. Para generar el APK hacen falta, por orden:

1. **JDK 17** (Gradle 8 no arranca con el 8);
2. **Android Studio** con el SDK de Android y las herramientas de línea de comandos;
3. `cd app && npm install && npx cap add android && npm run sync && npm run android`.

Para iOS hace falta además **un Mac con Xcode**: no hay forma de compilar para iPhone desde
Windows, y eso no es un detalle del plan sino una condición de D-A4 (Android primero).

### Lo que ya está funcionando (19-sep-2026)

La F1 se hizo el mismo día que este documento, porque es la que mejora la web aunque la app
tardara en llegar. En pedibot.xyz, hoy:

- **el sitio se puede instalar** desde el móvil (manifiesto, iconos del logo de verdad, color de
  tema, atajos a los números de emergencia y al calendario);
- **lo ya visitado se abre sin cobertura**, y con él los números de emergencia, que se guardan
  desde la primera visita aunque nadie los haya abierto;
- **la página de «sin conexión» habla las ocho lenguas a la vez**, porque quien llega a ella no
  tiene red para cambiar de idioma;
- **las páginas van siempre a la red primero**: la copia guardada sólo aparece cuando la red
  falla. Un calendario de vacunas de hace ocho meses servido desde el teléfono sería peor que no
  tener nada;
- **la API no se guarda nunca**: una respuesta del chat es para una pregunta, un niño y un
  momento;
- **los datos se guardan al instalar el trabajador**, sin esperar a que nadie visite la página:
  los 88 países con su número, los 61 calendarios, las 69 tablas, las dosis y los signos de
  alarma. Es la diferencia entre «funciona sin cobertura si ya habías entrado ahí» y «funciona»;
- **el calendario de vacunas de cada hijo, con fechas de verdad**, y un botón para llevárselas al
  calendario del teléfono (`.ics`). En la app eso pasa a ser la notificación local de D-A3: el
  dato es el mismo, cambia quién avisa.

Y hay interruptor de emergencia: `/sw.js` se sirve sin caché, así que desplegarlo con un
`unregister()` dentro apaga todo esto en la siguiente carga de cualquiera.

---

## 7. Google Play, paso a paso

**La cuenta.** 25 $ una sola vez. Y aquí está la trampa que decide el calendario entero: las
cuentas **personales creadas después del 13 de noviembre de 2023** tienen que pasar una prueba
cerrada con **12 probadores apuntados durante 14 días seguidos** antes de poder publicar en
producción. Las cuentas de **organización** no pasan por ahí.

No es que haya que enseñarles la app a doce personas: doce cuentas de Google distintas tienen que
**aceptar la invitación e instalarla**, y el contador se reinicia si bajan de doce. Si vamos con
cuenta personal, esto hay que empezarlo **el primer día**, en paralelo con todo lo demás, y hacen
falta doce personas de verdad (los probadores de la beta de Telegram valen).

**Lo que pide la ficha**, en los 8 idiomas que ya tenemos:

- nombre (30 caracteres), descripción corta (80), descripción larga (4.000);
- icono 512×512 (hecho), gráfico destacado 1024×500 (falta, se hace con el mismo script);
- un mínimo de dos capturas por formato;
- política de privacidad en una URL pública: sirve `https://pedibot.xyz/legal`, con el arreglo
  del párrafo siguiente.

**Data safety, y aquí hay que ser honestos.** Hay que declarar que se recoge «información de
salud», porque la pregunta del padre lo es, y **que se comparte con un tercero**, porque el texto
va a un proveedor de modelo (DeepSeek) para redactar la respuesta. Eso **la página legal no lo
dice hoy**, y debería decirlo con o sin app. Lo apunto como arreglo pendiente de la web, no de la
app.

**Categoría y clasificación.** Categoría Medicina o Salud y bienestar; cuestionario IARC; al
responder que hay «información médica o de tratamiento» la edad recomendada sube. No es un
problema, es una casilla.

**Health apps.** Play pide una declaración extra para apps de salud. Encajamos como app de
**información** que cita guías publicadas, no como app clínica.

---

## 8. App Store, y el único bloqueo de verdad de todo este documento

99 $ al año. Sin la regla de los 12 probadores: TestFlight sirve.

Tres directrices nos miran de frente. Las dos primeras las cumplimos ya:

**1.4.1 (apps médicas).** «Medical apps that could provide inaccurate data or information, or
that could be used for diagnosing or treating patients may be reviewed with greater scrutiny…
Apps should remind users to check with a doctor». La web ya lo dice en todas las páginas y en
cada respuesta, y no medimos nada con los sensores del teléfono, que es lo que suelen rechazar.

**5.1.3 (datos de salud).** No usamos HealthKit, no hay publicidad, no hay minería de datos, no
hay cuenta. La etiqueta de privacidad saldría como «datos de salud, no vinculados a tu
identidad», que es la verdad.

**1.4.2 (calculadoras de dosis), y esto sí es un muro:**

> «Drug dosage calculators must come from the drug manufacturer, a hospital, university, health
> insurance company, pharmacy or other approved entity, or receive approval by the FDA or one of
> its international counterparts.»

PediBot tiene una calculadora de dosis por peso. Sus rangos salen de la guía de la AEPap y los
topes de las fichas técnicas, y cada fila tiene una prueba: está bien hecha. Pero la regla no
habla de estar bien hecha, habla de **de quién viene la app**, y la app vendría de nosotros, que
no somos ni un hospital ni una universidad ni una farmacia.

Tres salidas, y mi recomendación:

1. **Publicar iOS sin la calculadora** (la versión 1 de iOS enseña la tabla de dosis como lo que
   dice la fuente, sin calcular por peso). Android y la web la mantienen. ← **lo que yo haría**
2. Buscar que una sociedad científica —la AEPap o la SEUP, a las que ya citamos y a las que ya
   hay que escribir por lo de `ops/PERMISOS.md`— respalde la app. Es lo bueno y es lo lento.
3. Enviarla con la calculadora y aceptar el rechazo como respuesta oficial. Cuesta una o dos
   semanas y no rompe nada, pero retrasa el lanzamiento de iOS.

No lo decido yo: es §10, decisión 2.

---

## 9. Lo que puede salir mal

- **Rechazo por 4.2 («es una web envuelta»).** Se contesta con lo de §4, y en el vídeo de revisión
  se enseña **el modo avión**: eso es lo que no puede hacer una web.
- **Rechazo por 1.4.2.** Ver arriba.
- **Los 14 días de Google se alargan** porque un probador desinstala. Se sale apuntando a quince
  o dieciséis desde el principio.
- **La app se queda con datos viejos.** Un calendario de vacunas de hace ocho meses guardado en
  el teléfono es peor que no tenerlo: hay que refrescar en segundo plano y **escribir en pantalla
  la fecha de lo que estás leyendo**, como ya hacen las fichas de país.
- **La marca.** «PediBot» hay que comprobar que no choca con nada registrado en las tiendas antes
  de mandar la ficha.

---

## 10. Decisiones del operador (19-sep-2026, contestadas en el chat)

Las cuatro salieron por donde tenían que salir: preguntadas, no supuestas. Quedan aquí escritas
con su motivo, porque dentro de tres semanas nadie se acordará de por qué iOS sale sin
calculadora.

| # | Decisión | Lo que implica |
|---|---|---|
| **D-A1** | **Cuenta de Play personal** | 25 $ una vez, pero **12 probadores apuntados 14 días seguidos** antes de producción. Se empieza el primer día, en paralelo con todo lo demás, y se apunta a 15 o 16 por si alguno desinstala. Las cuentas van a nombre del operador. |
| **D-A2** | **iOS v1 sin calculadora de dosis** | La directriz 1.4.2 pide que venga de un hospital, universidad, farmacia o fabricante, y viene de nosotros. En iPhone se enseña la tabla como lo que dice la fuente, sin calcular por peso. **Android y la web la mantienen igual.** El respaldo de la AEPap o la SEUP se puede pedir después, sin bloquear el lanzamiento. |
| **D-A3** | **Recordatorios de vacunas en la v1** | La fecha de nacimiento se guarda **sólo en el teléfono** y nunca viaja. Aviso tres días antes de cada cita del calendario del país elegido. ~3 días de trabajo (F4) y es lo que hace que la app siga instalada. |
| **D-A4** | **Android primero, iOS detrás** | Es donde están India, Nigeria y Kenia, que es a donde apunta el proyecto, y la revisión de Apple es la que puede pedir cambios. iOS va después, con lo aprendido y ya sin calculadora. |

Lo que queda pendiente de él, y no es una decisión sino un trámite: abrir las dos cuentas
(Play, 25 $ una vez; Apple, 99 $ al año) y reunir los 12 probadores. Sin la cuenta de Play no
empieza el reloj de los 14 días, que es el camino largo de todo el calendario.

---

## 11. Conclusión

La app tiene sentido, pero no porque la web se vea mal en el móvil, que se ve bien. Tiene sentido
porque **sin cobertura la web no existe y la app sí**, y porque los países a los que apuntamos son
justo donde la cobertura se acaba. Todo lo que el proyecto sabe —88 países con su número de
emergencias, 61 calendarios, 69 curvas, 502 guías— cabe en cinco megas dentro del teléfono; sólo
el chat necesita red.

El camino es empaquetar la web que ya existe con Capacitor, no reescribir nada, y añadirle lo
que justifica que sea una app: funcionar sin red, avisar de las vacunas y marcar el número de un
toque. Son unas tres semanas de trabajo, y entre cuatro y seis de calendario, porque Google
obliga a catorce días de prueba cerrada con doce probadores si la cuenta es personal.

Hay un solo muro de verdad y conviene saberlo hoy: Apple no admite calculadoras de dosis que no
vengan de un hospital, una universidad, una farmacia o un fabricante. La nuestra está bien hecha
y eso da igual para esa regla. Mi propuesta es sacar iOS sin ella y mantenerla en Android y en la
web.

Lo del logo ya está arreglado y no era un detalle: llevabas razón, el de la web era un dibujo mío
parecido al tuyo. Ahora todos los iconos, los de la web y los de la app, salen del JPG que me
diste, con una sola línea de código.

Las cuatro decisiones están contestadas desde el mismo 19-sep y escritas en §10: cuenta personal
en Play —con lo que el reloj de los 12 probadores y los 14 días manda el calendario—, iOS sin
calculadora, recordatorios de vacunas dentro de la primera versión y Android primero. Con eso, el
trabajo empieza por la F1, que es la que hace que la web funcione sin cobertura y que mejora el
sitio aunque la app tardara en llegar.

Lo único que hace falta de ti para que arranque el reloj es abrir la cuenta de Google Play y
juntar doce probadores. Todo lo demás se puede ir construyendo mientras.
