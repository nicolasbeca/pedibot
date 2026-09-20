# Lo que tienes que hacer tú — paso a paso

> 19-sep-2026. Todo lo que está parado esperándote, en orden. Cada punto dice **qué**, **dónde**,
> **cuánto tarda** y **qué me tienes que decir después**, si hace falta.
>
> Lo que no está aquí es porque puedo hacerlo yo. Si algo de esta lista crees que puedo hacerlo,
> dímelo y lo hago.

---

## FECHAS QUE NO SE TE PUEDEN PASAR

*(anotadas el 20-sep-2026)*

| cuándo | qué | por qué esa fecha |
|---|---|---|
| **miércoles 23 de septiembre** | se acaban las 72 horas de MetaDAO | Su acuse dice que escriben en ~72 h **sólo si tienen preguntas**. Lo enviaste el domingo 20, así que el reloj empieza el lunes. Si no escriben, no pasa nada: ellos mismos avisan de que no contestar es lo normal. |
| **viernes 2 de octubre** | dejar de esperar a MetaDAO | Diez días hábiles. A partir de ahí, silencio es silencio, y no significa que el proyecto sea malo: significa que no llegó a la mesa. |
| **a partir del 2 de octubre** | decidir lo de Backable | No antes: si aparecen con preguntas mientras tienes una ronda abierta, la conversación se complica sin ganar nada. El borrador sí se puede preparar ya, que es gratis hasta los 15 $ del final. |
| **domingo 5 de octubre** | cierre de InproInnova 2026, la feria de IA de la Diputación de Sevilla | Es en el Pabellón de la Navegación el 18 de noviembre. Leí las bases firmadas: piden empresa constituida de menos de 7 años con sede en la provincia, y decide un comité técnico por innovación, escalabilidad y contribución a Sevilla. **Lo único que falta saber es si admiten autónomo**, y eso es un correo de tres líneas a `inproinnova@dipusevilla.es` que no puedo mandar yo; el texto está escrito en `ops/ANDALUCIA.md`. Publican los seleccionados el 16 de octubre. |
| **lunes 2 de noviembre, 20:00 en California** | cierre de Y Combinator, tanda de invierno 2027 | Es hora del Pacífico, o sea las 5 de la madrugada del martes aquí. Contestan el 11 de diciembre y la tanda es en San Francisco, de enero a marzo. Presentarse es gratis y lo lee gente: entra en la lista sólo desde que dijiste que el anonimato ya da igual. Entero, con sus pegas, en `ops/FINANCIACION.md`. |

**Y un aviso sobre Backable que cambia el número**: sus once rondas financiadas tienen un techo
de 200.000 $ y **es todo o nada** —si no llegas al objetivo no recibes nada—. La cifra que
encaja ahí son **75.000 $**, no los 262.500 que te dije primero. Está en `ops/BACKABLE.md` con
los números de cada ronda.

---

## HOY

### 1. Probar la web antes de MetaDAO — 10 minutos

Con el móvil, no con el ordenador, que es donde la va a abrir la gente.

1. Abre **https://pedibot.xyz** y pregunta cualquier cosa («mi hijo de 2 años tiene fiebre»).
2. Abajo del todo, pincha **«Tus hijos»** (o ve a `pedibot.xyz/es/family`).
3. Escribe tu correo y una contraseña de ocho letras o más. Dale a **Crear cuenta**.
4. **Añadir un hijo**: nombre, fecha de nacimiento, sexo y país. Guarda.
5. Apunta una medida: fecha, peso en kg, talla en cm. Tiene que salir su curva y su percentil.
6. Mira su **calendario de vacunas**: las fechas son suyas, calculadas desde su nacimiento.
7. Vuelve al chat y pregunta **«¿qué vacunas le tocan a [su nombre]?»**. Arriba de la respuesta
   tiene que poner su nombre y su edad.
8. Si algo falla o chirría, apúntalo y me lo dices. **Eso es lo único que necesito.**

### 2. Publicar en MetaDAO

Lo tuyo. Yo no toco nada ahí.

---

## ESTA SEMANA — lo que destraba trabajo mío

### 3. Decidir el proveedor de correo — 15 minutos, y es el más importante

Sin esto, **quien pierda su contraseña no la puede recuperar**, y el boletín que querías no se
puede mandar. Es la única cosa de la cuenta que está prometida y no funciona.

1. Elige uno: **Resend** (resend.com, el más simple, 3.000 correos al mes gratis), **Brevo** o
   **Amazon SES** (el más barato con volumen, el más engorroso de montar).
2. Crea la cuenta y verifica el dominio `pedibot.xyz` (te pedirá poner dos o tres registros DNS
   en Cloudflare; si me dices cuáles, te digo exactamente dónde van).
3. Sácate una **clave API** y pégamela aquí.
4. Yo monto: verificación del correo al registrarse, «he olvidado mi contraseña» y el envío del
   boletín con su baja en un clic.

### 4. Los tres posts de Reddit y Hacker News — 20 minutos

Te los mandé a Telegram: tres títulos y tres cuerpos, en mensajes separados para copiar y pegar.

1. **Antes de publicar, lee las reglas fijadas del sub.** Casi todos exigen haber participado
   antes de poner un enlace, y algunos piden marcar que el sitio es tuyo (los tres textos ya lo
   dicen).
2. Pega el título en su hueco y el cuerpo en el suyo.
3. **Edita dos o tres frases a mano dentro del cuadro** antes de enviar: el texto largo pegado de
   golpe dispara los detectores de IA.
4. No los publiques los tres el mismo día. Uno, y a los dos días el siguiente.

### 5. Los cinco tuits — 5 minutos

Te los acabo de mandar a Telegram, uno por mensaje. Yo los separaría un par de horas entre ellos,
y el primero lo pondría cuando tengas rato de contestar, porque puede traer respuestas.

### 6. Los dos correos de permisos — 10 minutos

Están escritos enteros en `ops/PERMISOS.md`, listos para copiar y pegar.

1. **Immunize.org** → `admin@immunize.org`. Son 36 hojas de vacunas en suajili, que es la única
   fuente pediátrica en esa lengua que hemos encontrado con contenido utilizable.
2. **Vikaspedia (C-DAC)** → por su formulario web, no por correo. Es el hindi.
3. Si contestan, me pasas la respuesta y yo hago lo que toque.

### 7. Search Console — 10 minutos

Las 800 páginas africanas nuevas están en el sitemap, pero Google no las ha visto todas.

1. Entra en **search.google.com/search-console** con la cuenta del proyecto.
2. Sitemaps → comprueba que `sitemap-index.xml` está enviado y sin errores.
3. En la barra de arriba, pega `https://pedibot.xyz/es/emergency/ke` y dale a **Solicitar
   indexación**. Repite con tres o cuatro más (ng, tz, ug, za).
4. No hace falta más: pidiendo unas pocas, el rastreador encuentra el resto.

---

## PARA LA APP — **en pausa hasta que haya tracción** (decisión tuya, 19-sep)

> «Ponemos un cartel tipo coming soon la app y vemos si cuando haya más tracción nos compensa el
> desembolso.» Hecho: el cartel ya está en las ocho portadas, y dice lo que se puede hacer hoy
> (instalar la web, que abre sin cobertura) sin prometer fecha ni pedir el correo.
>
> Así que **no pagues nada todavía**. Los puntos 8 a 13 quedan aquí escritos para el día que
> decidas, y en ese orden. Lo único que conviene hacer ya es el 13, que es gratis.

## PARA LA APP — cuando decidas, en este orden

### 8. Abrir la cuenta de Google Play — 30 minutos y 25 $, una sola vez

**Este es el que arranca el reloj.** Hasta que no esté, los catorce días de prueba obligatoria no
empiezan a contar.

1. Entra en **play.google.com/console** con una cuenta de Google que vayas a conservar.
2. Elige **cuenta personal** (fue tu decisión D-A1; la de empresa se salta la prueba de los 12
   probadores pero pide papeles de la sociedad y tarda más en verificarse).
3. Paga los 25 $. Te pedirán verificar identidad con un documento: tarda de un día a una semana.
4. Dímelo cuando esté verificada.

### 9. Reunir doce probadores — mientras esperas lo anterior

Google exige **12 personas con cuenta de Google, apuntadas 14 días seguidos**, antes de dejarte
publicar. No vale con enseñarles la app: tienen que **aceptar la invitación e instalarla**.

1. Haz una lista de **quince** correos de Gmail (con doce justos, si uno desinstala, el contador
   se reinicia). Familia, amigos, los padres de la beta de Telegram.
2. Avísales de que tendrán que pulsar un enlace e instalar, y que no la desinstalen en dos
   semanas.
3. Pásame la lista cuando la tengas y la dejo preparada en el formato que pide Play.

### 10. Abrir la cuenta de Apple — 30 minutos y 99 $ al año

1. **developer.apple.com/programs**. Como persona física vale.
2. Paga los 99 $. La verificación suele tardar un par de días.
3. No corre tanta prisa como la de Google: Android va primero (decisión D-A4).

### 11. Un ordenador que pueda compilar — el que me falta a mí

Aquí donde trabajo hay **Java 8 y ningún SDK de Android**, así que puedo dejar la app montada
pero no convertirla en un APK. Hacen falta, por este orden:

1. **JDK 17** (el 8 no sirve, Gradle no arranca).
2. **Android Studio**, con el SDK de Android y las herramientas de línea de comandos.
3. Para iPhone, además, **un Mac con Xcode**. Desde Windows no hay forma, no es pereza mía.

Dime si lo instalas en tu PC, si hay otra máquina, o si prefieres que esto lo haga un tercero.

### 12. Las cinco capturas — 20 minutos, cuando la app funcione en tu móvil

Con la app instalada, no montadas en Photoshop:

1. El chat contestando algo **con su fuente a la vista**.
2. El aviso rojo con el número de emergencias, **en modo avión** (es también la prueba para
   Apple de que la app funciona sin red).
3. La ficha de un hijo con su curva de crecimiento.
4. Su calendario de vacunas con fechas.
5. El calendario vacunal de un país con su fuente citada abajo.

### 13. Comprobar la marca — 10 minutos, **y esto sí conviene hacerlo ya**

Busca **«PediBot»** en Google Play y en la App Store antes de mandar la ficha. Si hay otra app
con ese nombre, mejor enterarse ahora que cuando te la rechacen.

---

## DECISIONES TUYAS, SIN PRISA

### 14. ¿Pedimos respaldo para la calculadora de dosis?

Apple no admite calculadoras de dosis que no vengan de un hospital, una universidad, una farmacia
o un fabricante. Tu decisión fue sacar iOS sin ella, y está bien. Si además quieres intentar el
respaldo de la **AEPap** o la **SEUP** (a las que ya citamos), dímelo y te escribo el correo.

### 15. ¿WhatsApp?

Es el canal natural de los padres en India, Nigeria y Brasil. La API de Meta es gratis hasta
cierto volumen pero pide verificar la empresa. Son varios días de trabajo míos. Sí o no.

### 16. ¿Más lenguas africanas?

Hoy el triaje habla suajili. Las siguientes por tamaño serían hausa (Nigeria, Níger) y amárico
(Etiopía). Cada una son dos o tres días y **no hay fuentes pediátricas con licencia abierta** en
ninguna de las dos, así que sería como el suajili: el aviso en su lengua y la explicación en
inglés.

### 17. El catálogo del agente ACP

El fichero se puso al día el 20-sep-2026 y lo comprueba una prueba; el panel de Virtuals sigue con las cifras
viejas. La sincronización se lanza desde el servidor y la puedo hacer yo: **dime si quiero que la
lance** y lo hago. Lo que no puedo es ocultar en el panel cuatro recursos viejos con
descripciones caducadas, porque la herramienta no los deja ni editar ni borrar. Eso es un clic
tuyo en el panel web.

---

## Lo que estoy haciendo yo mientras

Depuración y mejoras, sin tocar nada de lo de arriba. Si algo de lo tuyo se desbloquea, lo retomo
en cuanto me lo digas.
