# app/ — la carcasa nativa de PediBot

Estado a 19-sep-2026: **montada, no compilada.** Lo que hay aquí funciona y está probado; lo que
falta necesita una máquina distinta, no más código. El plan entero está en `APP.md`, en la raíz.

## Qué hay

    capacitor.config.json   identificador xyz.pedibot.app, pantalla de arranque, notificaciones
    package.json            las dependencias de Capacitor y los tres comandos
    scripts/copy-web.mjs    mete el sitio construido en www/, eligiendo qué va dentro
    assets/                 los iconos, sacados de LOGOS/LOGO_PEDIBOT_CARA.jpg
    www/                    lo generado por el script (no se guarda en el repositorio)

## Cómo se pone al día

Es la regla del operador —«cada vez que actualicemos la web hay que actualizar la app»— en dos
órdenes. La app **no tiene su propio sitio**: sale del mismo `web/site/dist`.

    cd web/site && npm run build     # construye la web, con sus datos sin conexión
    cd ../../app && npm run sync     # copia lo que va dentro y sincroniza los proyectos nativos

## Qué va dentro y qué no

El sitio entero son 81 MB. Dentro van 20,6: las 88 fichas de emergencia por país en los ocho
idiomas, los datos en bruto, las portadas y las pantallas que tienen que abrir sin red. Las
guías, las fichas de dosis por marca y los calendarios país por país se quedan fuera y siguen
funcionando con red. El motivo está escrito en la cabecera de `scripts/copy-web.mjs`: se elige
por lo que hace falta a las tres de la mañana sin cobertura, no por lo que cabe.

## Lo que falta para compilar

En el PC donde se escribió esto hay Java 8 y ningún SDK de Android, así que no se puede generar
el APK. Hacen falta, por orden:

1. **JDK 17** — Gradle 8 no arranca con el 8.
2. **Android Studio** con el SDK y las herramientas de línea de comandos.
3. `npm install && npx cap add android && npm run sync && npm run android`.

Para iOS, además, **un Mac con Xcode**: desde Windows no hay forma. Por eso Android va primero
(decisión D-A4).
