# La ficha de las tiendas — textos listos para pegar

> 19-sep-2026. Fase F6 del plan de `APP.md`. Está escrito para **pegarlo tal cual** en Play
> Console y en App Store Connect: cada bloque dice su campo y su límite de caracteres, y el
> texto ya cabe. Nada de esto necesita Android Studio, así que se puede dejar hecho mientras
> llega la máquina que compile.
>
> Lo que **no** está aquí y hay que hacer con la app delante: las capturas de pantalla. Se
> explica al final qué hacen falta exactamente.

---

## 1. Lo que las dos tiendas piden igual

| Campo | Valor |
|---|---|
| Nombre del paquete | `xyz.pedibot.app` |
| Categoría | Medicina (Play) · Medical (App Store) |
| Web | https://pedibot.xyz |
| Privacidad | https://pedibot.xyz/legal |
| Soporte | pedibot.ai@gmail.com |
| Precio | Gratis, sin compras dentro, sin anuncios |
| Idiomas de la ficha | inglés, español, francés, alemán, ruso, árabe, portugués, hindi |

---

## 2. Google Play

### Nombre de la app (30 caracteres)

```
PediBot: salud infantil
```

Inglés: `PediBot: child health`

### Descripción breve (80 caracteres)

**Español** (70):
```
Guías pediátricas citadas, vacunas y urgencias. Gratis y sin conexión.
```

**Inglés** (79):
```
Paediatric answers with sources, vaccines and emergency numbers. Free, offline.
```

**Francés** (77):
```
Réponses pédiatriques sourcées, vaccins et urgences. Gratuit, hors connexion.
```

**Alemán** (75):
```
Kindermedizin mit Quellen, Impfungen und Notrufnummern. Kostenlos, offline.
```

**Ruso** (71):
```
Детское здоровье с источниками, прививки и скорая. Бесплатно, без сети.
```

**Árabe** (72):
```
إجابات طب الأطفال بمصادرها، التطعيمات وأرقام الطوارئ. مجانا وبلا إنترنت.
```

**Portugués** (76):
```
Respostas pediátricas com fontes, vacinas e urgências. Grátis e sem ligação.
```

**Hindi** (76):
```
स्रोत सहित बाल-स्वास्थ्य जवाब, टीके और आपातकालीन नंबर। मुफ़्त, बिना इंटरनेट।
```

### Descripción completa (4.000 caracteres)

**Español** (1912):

```
PediBot contesta preguntas sobre la salud de tu hijo con lo que dicen las guías pediátricas publicadas, y te enseña de dónde sale cada respuesta.

No es un médico y no diagnostica. Es la parte que suele faltar a las tres de la mañana: qué dicen las sociedades pediátricas y los servicios de salud sobre lo que te está pasando, dicho en tu idioma y con el enlace al documento original al lado.

QUÉ HACE

• Responde en ocho idiomas citando a la SEUP, la AEP, el NHS, los CDC, la OMS y otras dos docenas de organismos.
• Avisa cuando lo que cuentas encaja con un signo de alarma, y te da el número de emergencias de tu país.
• Calendario de vacunas de 61 países, transcrito de los documentos oficiales, con su fuente y su fecha.
• Curvas de crecimiento de la OMS: peso y talla de tu hijo, con su percentil.
• Calculadora de dosis de paracetamol e ibuprofeno por peso, con las marcas de tu país.
• Diario de síntomas y lista de «¿tengo que ir a urgencias?».

FUNCIONA SIN COBERTURA

Los números de emergencia de 88 países, los signos de alarma, los calendarios de vacunas y las tablas de crecimiento están dentro de la app. Sin conexión abre igual y te dice lo que sabe. Sólo el chat necesita red.

TUS HIJOS, SI QUIERES

Puedes crear una cuenta gratuita y guardar la fecha de nacimiento de cada hijo. Entonces preguntas «¿qué vacunas le tocan a Laura?» y contesta por la edad de Laura. Puedes apuntar su peso y su talla y ver su curva, y llevarte las próximas vacunas al calendario del teléfono.

La cuenta es opcional: sin ella funciona todo igual. Lo que guardes puedes descargarlo o borrarlo cuando quieras, desde la propia app.

LO QUE NO HACE

No diagnostica. No sustituye a tu pediatra ni a urgencias. No tiene anuncios, no vende datos y no pide dinero. Si tu centro de salud dice otra cosa, tu centro de salud tiene razón.

Todas las respuestas llevan la fuente, con su año y su enlace. Puedes comprobarlas.
```

**Inglés** (1957):

```
PediBot answers questions about your child's health using published paediatric guidance, and shows you where every answer comes from.

It is not a doctor and it does not diagnose. It is the part that tends to be missing at three in the morning: what the paediatric societies and health services actually say about what is happening, in your language, with the link to the original document beside it.

WHAT IT DOES

• Answers in eight languages, quoting the NHS, the CDC, the WHO, the AAP, Spanish and French paediatric societies and two dozen more.
• Warns you when what you describe matches a red flag, and gives you your country's emergency number.
• Vaccination schedules for 61 countries, transcribed from the official documents, with source and date.
• WHO growth charts: your child's weight and height, with percentile.
• Paracetamol and ibuprofen dosing by weight, with the brands sold in your country.
• Symptom diary and a "should I go to A&E?" checklist.

IT WORKS WITHOUT A SIGNAL

Emergency numbers for 88 countries, the red-flag checklist, the vaccination schedules and the growth tables are inside the app. With no connection it still opens and tells you what it knows. Only the chat needs the network.

YOUR CHILDREN, IF YOU WANT

You can create a free account and save each child's date of birth. Then you ask "what vaccines are due for Laura?" and it answers for Laura's age. You can record her weight and height and see her curve, and send the next appointments to your phone's calendar.

The account is optional: everything works without one. Whatever you save, you can download or delete whenever you like, from inside the app.

WHAT IT DOES NOT DO

It does not diagnose. It does not replace your paediatrician or the emergency department. No ads, no data selling, no payments. If your health service says something different, your health service is right.

Every answer carries its source, with the year and the link. You can check it.
```

> Las otras seis lenguas salen de traducir **estos dos**, no de escribirlos otra vez: la ficha
> tiene que decir lo mismo en las ocho. Se hace cuando la cuenta de Play esté abierta, porque
> Play permite pegarlas una a una y hasta entonces no hay dónde.

### Gráfico destacado (1.024 × 500)

Se genera con `scripts/make_og_image.py` cambiando el tamaño: el mismo logo y la misma frase que
la tarjeta de compartir, que ya está aprobada por el operador. **Pendiente.**

### Formulario «Data safety»

Lo que hay que marcar, y por qué. Esto no se improvisa el día del envío:

| Pregunta | Respuesta |
|---|---|
| ¿Recoge datos? | **Sí** |
| Personal info → Email address | Recogido · obligatorio sólo si el usuario crea cuenta · para gestionar la cuenta · **no compartido** |
| Personal info → Name | Recogido (el nombre del hijo, que lo escribe el usuario) · opcional · funcionalidad de la app · **no compartido** |
| Health and fitness → Health info | Recogido (la pregunta del chat, el peso y la talla) · para funcionalidad de la app · **compartido con un proveedor de modelo de lenguaje** para redactar la respuesta |
| ¿Cifrado en tránsito? | Sí, todo por HTTPS |
| ¿Se puede pedir el borrado? | **Sí**, desde la propia app, sin escribirnos |
| ¿Hay publicidad o analítica de terceros? | No |

### Declaración de app de salud

Categoría: **información de salud**, no app clínica. PediBot transcribe y cita guías publicadas;
no diagnostica, no mide nada con los sensores del teléfono y no sustituye a un profesional. La
página `https://pedibot.xyz/legal` lo dice con esas palabras y en los ocho idiomas.

### Clasificación por edad (IARC)

Hay «información médica o de tratamiento» → sale una edad recomendada más alta. No es un
problema: es una casilla y hay que responderla como es.

---

## 3. App Store

### Nombre (30) y subtítulo (30)

```
PediBot
```
```
Salud infantil con fuentes
```

Inglés: `Child health, with sources`

### Palabras clave (100 caracteres, separadas por comas, sin repetir el nombre)

**Español** (96):
```
pediatría,fiebre,vacunas,bebé,urgencias,niños,percentiles,dosis,pediatra,tos,vómitos,crecimiento
```

**Inglés** (94):
```
paediatrics,fever,vaccines,baby,emergency,children,percentile,dosage,pediatrician,cough,growth
```

### Texto promocional (170, se puede cambiar sin revisión)

```
Ahora con la ficha de cada hijo: su edad, su curva de crecimiento y las vacunas que le tocan, con fecha. Y los números de emergencia de 88 países, también sin cobertura.
```

### Descripción

La misma de Play, quitando las viñetas con `•` si el revisor las marca (no suele). App Store no
tiene límite corto de descripción.

### Etiqueta de privacidad (App Privacy)

| Tipo de dato | Uso | ¿Vinculado a la identidad? | ¿Seguimiento? |
|---|---|---|---|
| Contact Info → Email | Funcionalidad de la app | **Sí** (hay cuenta) | No |
| Health & Fitness → Health | Funcionalidad de la app | Sí | No |
| User Content → Other | Funcionalidad de la app | Sí | No |
| Identifiers | — | — | — |

Sin SDK de publicidad, sin analítica de terceros, sin identificador de dispositivo.

### Notas para el revisor (el campo que decide la mitad de los rechazos)

```
PediBot is an information app for parents. It transcribes and quotes published paediatric guidance (NHS, CDC, WHO, AAP, SEUP, AEP and others) and always shows the source, the year and a link to the original document. It does not diagnose and it says so on every screen and in its legal page (https://pedibot.xyz/legal).

Two points about the App Review Guidelines:

1.4.2 — This version of the iOS app does NOT include the weight-based drug dosage calculator that the website offers. We removed it deliberately because the calculator does not come from a drug manufacturer, hospital, university, pharmacy or approved entity. The app shows dosing information only as it is published by the source, without calculating.

4.2 — The app is not a repackaged website. Emergency numbers for 88 countries, the red-flag checklist, 61 vaccination schedules and the WHO growth tables are bundled inside the app and work with no network at all: put the device in airplane mode and open it. It also schedules local notifications for each child's vaccination appointments, which a website cannot do.

There is no account needed to use the app. An optional free account stores a child's date of birth and measurements so the app can answer by their age; it can be deleted from inside the app at any time.

Test account, if you want one: (crear una en la propia app; no hay verificación por correo, así que cualquier dirección funciona)
```

---

## 4. Las capturas, que son lo que falta

Cinco por plataforma, en este orden, y hay que hacerlas **con la app funcionando**, no montadas:

1. **El chat contestando una pregunta con su fuente.** Es lo que la distingue de todo lo demás.
2. **El aviso rojo con el número de emergencias**, en modo avión, para que se vea que funciona
   sin red. Es la captura que también sirve de respuesta a la 4.2.
3. **La ficha de un hijo con su curva de crecimiento** sobre las bandas de la OMS.
4. **El calendario de vacunas de ese hijo, con fechas.**
5. **El calendario vacunal de un país** con su fuente oficial citada al pie.

Tamaños: Play pide 1.080 × 1.920 como mínimo y admite hasta ocho; Apple pide las de 6,7" y 6,5"
(1.290 × 2.796 y 1.242 × 2.688). Se sacan del propio teléfono, no de un emulador, porque el
emulador pinta las tipografías distinto.

---

## 5. Antes de darle a enviar

- [ ] La cuenta de Play abierta y pagada (25 $, una vez) — **decisión D-A1: personal**
- [ ] Doce probadores apuntados y **catorce días seguidos** corriendo
- [ ] La cuenta de Apple abierta (99 $/año)
- [ ] La app compilada en una máquina con JDK 17 y Android Studio (ver `app/README.md`)
- [ ] Las cinco capturas hechas en un teléfono de verdad
- [ ] El gráfico destacado de Play (1.024 × 500)
- [ ] Las seis traducciones de la descripción larga
- [ ] La calculadora de dosis **fuera** de la versión de iOS (D-A2)
- [ ] Recuperación de contraseña funcionando (I-20): hoy quien la pierde no puede recuperarla, y
      eso en una app con cuenta es una queja de una estrella el primer día
