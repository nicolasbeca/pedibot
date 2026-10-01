# appgoogle.md — PediBot en Google Play, al mínimo coste

> Arranque: 1-oct-2026. El operador: «Vamos a arrancar con el desarrollo de la App en google.
> Todo tiene que ser al mínimo coste. Empieza a diseñar conforme a la web y vamos viendo.»
>
> Este fichero es el cuaderno de la app de Android: decisiones, costes, diseño, pasos y lo que se
> va haciendo, con fecha. El plan anterior (iOS + Android con Capacitor, 19 y 20-sep) está en
> `APP.md`; aquí se dice qué se hereda de él y qué cambia.

---

## 1. La decisión técnica: una TWA, no Capacitor

**Trusted Web Activity (TWA):** la app de Android es pedibot.xyz abierta por Chrome a pantalla
completa, sin barra de direcciones, con su icono en el móvil y su ficha en Play. Se genera con
**Bubblewrap**, la herramienta de Google para esto (gratis y de código abierto).

`APP.md` §3 descartó la TWA por una sola razón: Apple la rechaza (directriz 4.2, «una web
envuelta»). Ahora el objetivo es **sólo Google** y **al mínimo coste**, y para eso la TWA gana:

| | TWA (Bubblewrap) | Capacitor (lo de `APP.md`) |
|---|---|---|
| Dinero | 25 $ (la cuenta de Play), una vez | 25 $ igual |
| Código nativo que mantener | **ninguno** | un proyecto Android entero |
| Un cambio en la web llega a la app | **solo, al desplegar** | sólo lo que no viaja en el paquete; la interfaz pide versión nueva |
| La «regla de oro» de `APP.md` §4 bis (si se toca la web, se toca la app) | **se cumple sola**: es la misma web | hay que vigilarla con pruebas |
| Sin cobertura | lo que ya hace la web (service worker, F1 de `APP.md`) | lo mismo, más lo empaquetado |
| Tamaño de la descarga | ~1 MB | ~20 MB |
| iOS más adelante | no sirve | sirve |

Lo que se pierde frente a Capacitor, dicho claro: notificaciones locales de vacunas sin red
(D-A3) y la cámara nativa. Las dos se pueden hacer más tarde **desde la web** (Web Push y el
selector de fotos de Android, que ya abre la cámara) si se ve que hacen falta. Si un día se va a
Apple, la carcasa de Capacitor de `app/` sigue ahí, sin tocar.

**Propuesta: TWA.** Pendiente del sí del operador (§9, D-G1).

## 2. Lo que cuesta, entero

| Concepto | Coste |
|---|---|
| Cuenta de desarrollador de Google Play (personal, D-A1) | **25 $, una vez** |
| Bubblewrap, JDK 17, SDK de Android | 0 — se descargan gratis en este PC |
| Servidor, dominio, la web | 0 más — ya se pagan |
| Firma de la app | 0 — clave propia + «Play App Signing» de Google |
| Capturas, gráfico de la ficha, textos | 0 — se hacen aquí |
| **Total** | **25 $** |

Lo que NO se paga: ningún servicio de compilación en la nube, ninguna biblioteca, ningún
diseñador, ninguna cuenta de empresa (las de organización piden un número D-U-N-S y papeles de
sociedad).

## 3. Cómo encaja con la web («diseñar conforme a la web»)

La app **es** la web. Así que el diseño no es de pantallas nuevas sino de **qué cambia la web
cuando sabe que está dentro de la app**: el «modo app».

### 3.1 Cómo sabe la web que está en la app

La TWA abre `start_url` con una marca: `https://pedibot.xyz/?source=android`. La web la ve en la
primera carga, la guarda (`sessionStorage`, y una clase `in-app` en `<html>`) y la mantiene al
navegar. Respaldo: `document.referrer` empieza por `android-app://xyz.pedibot.app` en la primera
apertura. Sin marca, la web se comporta exactamente como hoy.

### 3.2 Lo que se esconde dentro de la app, y por qué

| En la web hoy | En la app | Motivo |
|---|---|---|
| Donaciones en cripto (`Donate.astro`, `/support`) | **fuera** | Política de pagos de Play: una app no puede pedir dinero por fuera de su sistema de cobro; la excepción de donaciones es sólo para entidades benéficas verificadas. |
| Menciones al token (PDBT) y a Virtuals/ACP | **fuera** | Política de Play de contenido con blockchain y productos financieros: pide declaraciones y licencias que no tenemos. |
| El cartel «app coming soon» y el «instala la web» | **fuera** | Ya estás en la app. |
| Chat, urgencias, vacunas, curvas, dosis, MUAC, guías, cuenta de familia, diario | **igual** | Es la app. |
| Enlaces a fuentes externas (NHS, OMS…) | se abren en Chrome normal | Lo hace la TWA sola: lo que no es pedibot.xyz sale de la app. |

Una prueba recorre el sitio construido y comprueba que todo lo de la columna «fuera» lleva la
marca que lo esconde. Si mañana alguien añade un botón de donar en otra página, la prueba falla.

### 3.3 Lo que hay que retocar para el pulgar

De `APP.md` §5, lo que sigue vivo: zonas de toque de 44 px, la caja del chat abajo, el modo noche
y las fuentes de hindi y árabe guardadas para usarse sin red. Se revisa con la app instalada en un
Android barato de verdad, no en el emulador.

## 4. Las piezas técnicas

1. **`twa-manifest.json`** (Bubblewrap): `packageId` **`xyz.pedibot.app`** (el mismo que se
   reservó en `APP.md`), nombre «PediBot», colores del manifiesto web, icono de 512 sacado del
   logo (`app/assets/icon-1024.png`), `startUrl` con la marca de §3.1, atajos a urgencias y
   vacunas.
2. **La clave de firma** (`pedibot-upload.keystore`). **Nunca en git.** Se guarda en el PC del
   operador y una copia fuera (sin ella no se puede volver a subir una versión). Con «Play App
   Signing», Google guarda la clave final y ésta es sólo la de subida: si se pierde, se puede
   pedir otra.
3. **`/.well-known/assetlinks.json`** en pedibot.xyz, con la huella SHA-256 de las dos claves (la
   de subida y la que da Google en la consola). Sin esto la app abre **con barra de direcciones**,
   que es lo que Google rechaza como «web envuelta».
4. **El modo app** en la web (§3).
5. **El paquete AAB** que se sube a Play, compilado aquí.

## 5. Lo que pide Google Play, y lo que ya tenemos

| Requisito | Estado |
|---|---|
| Cuenta personal + verificar identidad | **operador**: 25 $ y un documento |
| Prueba cerrada: 12 probadores, 14 días seguidos (cuentas personales) | **operador**: lista de 15 correos de Gmail |
| Ficha: nombre, descripción corta (80) y larga (4.000) | escrita en `app/TIENDAS.md` (revisar que no prometa nada de Capacitor) |
| Icono 512 × 512 | hecho (`app/assets/icon-1024.png`) |
| Gráfico destacado 1024 × 500 | falta |
| Capturas (2 mínimo) | faltan, con la app instalada |
| Política de privacidad pública | `https://pedibot.xyz/legal` (revisar que nombre al proveedor del modelo) |
| Formulario de seguridad de los datos | borrador en `app/TIENDAS.md` |
| Declaración de apps de salud | por rellenar: app de **información** que cita guías, no de diagnóstico |
| Clasificación de contenido (IARC) | cuestionario en la consola |
| Nivel de API de destino exigido | lo pone Bubblewrap; comprobar el vigente al compilar |

## 6. Los pasos, en orden

| # | Qué | Quién | Coste |
|---|---|---|---|
| G1 | Este documento y la decisión TWA | yo / operador decide | 0 |
| G2 | Modo app en la web, con su prueba, y desplegado | yo — **hecho 1-oct** | 0 |
| G3 | Herramientas en este PC (JDK 17, SDK) y `twa-manifest.json` | yo — **hecho 1-oct** | 0 |
| G4 | Clave de subida y primer AAB compilado | yo — **hecho 1-oct** (contraseña en `LEEME-clave.txt`) | 0 |
| G5 | `assetlinks.json` en la web | yo — **hecho 1-oct** (falta la huella de Play) | 0 |
| G6 | Abrir la cuenta de Play y verificarla | **operador** | **25 $** |
| G7 | Lista de 15 probadores | **operador** | 0 |
| G8 | Ficha, capturas, formularios | yo, y el operador los pega en la consola | 0 |
| G9 | Prueba cerrada, 14 días | reloj | 0 |
| G10 | Producción | operador pulsa | 0 |

G6 y G7 son el camino largo: los 14 días no empiezan hasta que haya cuenta y probadores. Pueden
ir en paralelo con G2 a G5.

## 7. Riesgos

- **«Funcionalidad mínima / web envuelta».** Google acepta TWAs (es su propia tecnología), pero
  pide que la app funcione como app: pantalla completa (por eso `assetlinks.json`), sin cobertura
  (ya lo hace el service worker) y sin barra del navegador.
- **Política de salud.** La app informa y cita; no diagnostica. El aviso legal ya está en todas
  las páginas. Se declara como tal en el formulario de apps de salud.
- **Pagos y cripto.** Resuelto escondiendo esas partes en modo app (§3.2). Si alguien las cuela
  después, la prueba lo para.
- **La clave de firma.** Si se pierde la de subida, Google permite cambiarla; si no se activó
  Play App Signing, se pierde la app. Se activa desde el primer envío.

## 8. Cuaderno

- **1-oct-2026.** Creado este documento. Propuesta TWA en vez de Capacitor por coste y por la
  regla de oro. Comprobado: el manifiesto web ya sirve para la TWA (standalone, icono de 512,
  atajos); falta `assetlinks.json` (da 404). En este PC hay Node 24 y Java 8; Bubblewrap pide JDK
  17 y el SDK de Android, gratis.
- **1-oct-2026, tarde. Primera versión compilada (G2 a G5 hechos).**
  - **Modo app (G2), desplegado:** guion en la cabecera de todas las páginas
    (`layouts/Base.astro`), regla en `styles/global.css` que esconde todo enlace a `/support` y lo
    marcado `data-no-app` (cartel de la app, bloque de apoyo de la portada, donaciones).
    `tests/test_app_mode_hides_what_play_forbids.py`. Fuera de /support y /memo no hay token ni
    direcciones; /memo no se enlaza desde ninguna página.
  - **Herramientas (G3), gratis, fuera del repo:** `D:/Nicolas/android-tools` (JDK 17 Temurin, SDK
    con plataforma 36 y build-tools 36.1.0, que es la que pide Bubblewrap 1.25). Configuración de
    Bubblewrap en `~/.bubblewrap/config.json`. Tres trampas: Bubblewrap busca `sdk/tools` (se hizo
    un enlace a `cmdline-tools/latest`); esta sesión tiene `NoDefaultCurrentDirectoryInExePath`,
    que le impide encontrar `gradlew.bat` (compilar con `env -u NoDefaultCurrentDirectoryInExePath`);
    y `jarsigner` no está en el PATH, así que el AAB se firma a mano con el del JDK 17.
  - **`app/twa/`**: `make-manifest.mjs` genera `twa-manifest.json` desde el manifiesto vivo
    (`xyz.pedibot.app`, `?source=android` también en los atajos, barra de navegación del color
    de la web). El proyecto Gradle lo regenera `bubblewrap update` y no va a git.
  - **Icono maskable** nuevo en la web (`logo-maskable.png`, 512, la cara al 70 % sobre el fondo),
    sacado de `scripts/make_icons.py` como todos; sustituye en el manifiesto al de Apple de 180.
  - **Clave de subida (G4):** `D:/Nicolas/android-keys/pedibot-upload.keystore`, contraseña en
    `LEEME-clave.txt` al lado. **Fuera del repo.** SHA-256
    `ED:3E:01:F0:D9:C1:2D:DD:2E:D2:EA:F6:46:76:D9:A0:4B:68:FD:8F:6C:CF:0A:3E:E4:AA:B6:72:2E:21:EB:EB`.
    Ojo: `bubblewrap build` escribe la contraseña en su registro; se borra al acabar.
  - **Compilado:** APK firmado de 1,6 MB y AAB de 1,8 MB, `targetSdkVersion 36`,
    `minSdkVersion 21`. Copias en `D:/Nicolas/pedibot-android/` (`PediBot-1.0.0-prueba.apk` para
    instalar a mano, `PediBot-1.0.0.aab` para Play).
  - **`assetlinks.json` (G5), desplegado** y validado con la API de Google (Digital Asset Links):
    devuelve `xyz.pedibot.app` con nuestra huella.
    `tests/test_assetlinks_lets_the_app_open_full_screen.py`. Cuando exista la cuenta se añade
    la huella de Play App Signing (la da la consola en «Integridad de la app»).
  - De paso: el despliegue esperaba 20 s a la API y ya tarda 21 en arrancar; ahora espera 60.

## 9. Decisiones del operador

| # | Pregunta | Respuesta |
|---|---|---|
| D-G1 | ¿TWA (25 $, sin código nativo) en vez de Capacitor? | pendiente |
| D-A1 | Cuenta de Play personal (de `APP.md`) | sí, 19-sep |

## 10. Sin Android en casa (1-oct-2026)

El operador tiene iPhone y no conoce a nadie con Android. Dos cosas distintas:

- **Probar la app nosotros: el emulador del PC, gratis.** Montado en `D:/Nicolas/android-tools`
  (Android 15 con Play Store, móvil virtual `pedibot35`, aceleración WHPX de Windows; el PC tiene
  8 GB, justo pero va). Arranque sin ventana y capturas con `adb exec-out screencap -p`. Primera
  prueba: la app abre **a pantalla completa, sin barra de Chrome** (o sea, `assetlinks.json`
  funciona) y **sin el botón ♥ Apoyar** (el modo app funciona). Capturas en
  `D:/Nicolas/pedibot-android/`. Truco: en un Android recién creado Chrome enseña su bienvenida;
  se salta con `--disable-fre` en `/data/local/tmp/chrome-command-line` y
  `am set-debug-app --persistent com.android.chrome`.
- **Lo que el emulador NO cubre, y es obligatorio:** las cuentas personales nuevas tienen que
  verificar acceso a **un Android físico** (Android 10 o más, sin root) entrando en la app «Play
  Console» (support.google.com/googleplay/android-developer/answer/14316361). Una sola vez. Y los
  probadores cuentan con **Android de verdad**: según las guías de 2026, el emulador no cuenta y
  Google mira si usaron la app. Los probadores **pueden ser desconocidos** (la página oficial
  propone comunidades y público, no sólo amigos).
- **Recomendado:** un Android de segunda mano (Android 10+, 40-60 €). Verifica la cuenta, prueba
  en real y hace de probador. **No pagar los 25 $ antes de saber de dónde sale ese Android.**
- La contraseña de la clave de subida ya existe (generada, en `LEEME-clave.txt`): el operador sólo
  tiene que guardarla en su gestor y copiar la carpeta fuera del PC.
