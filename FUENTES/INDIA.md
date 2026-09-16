# Fuentes de India — rastreo de licencias (11-sep-2026)

> Mismo criterio que decidió el francés, el ruso y el árabe: **la licencia se lee en la página del
> propio sitio**, no se supone. Lo que no se puede leer se marca como pendiente.

## La licencia, leída literal

**National Health Mission** (nhm.gov.in), política de copyright:

> «The contents on this website may not be reproduced partially or fully, **without duly &
> prominently acknowledging the source**. The contents of this website cannot be used in any
> misleading or objectionable context or derogatory manner. However the permission to reproduce
> the material available on the **Ministry of Health & Family Welfare website** shall not extend
> to any material which is identified as being copyright of a third party.»

✅ **Usable citando la fuente de forma prominente**, excluido lo de terceros. Es la misma clase que
Canada.ca, aceptada el 2-sep. Y la frase nombra expresamente al ministerio, así que cubre también
su material.

**Cómo se consiguió**: `mohfw.gov.in` devuelve **403 desde España** y desde el VPS sirve una
cáscara de JavaScript sin texto. La política se leyó en `nhm.gov.in`, que es el mismo ministerio
y cuya página sí se renderiza en servidor. Es el mismo truco que con `sante.gouv.fr`: cuando el
portal principal está detrás de un muro, la de un organismo dependiente suele decir lo mismo.

## Lo primero que se ha traído

**El calendario vacunal nacional** (`/vaccines/in`, en los ocho idiomas), transcrito de las tres
páginas del PDF oficial de la NHM. Es una tabla de datos oficiales citada, no una reproducción de
contenido — el mismo criterio con el que se publicaron los de Francia y Alemania.

### Lo que un europeo corregiría y estropearía

Está fijado en `tests/test_vaccines_india.py` porque son diferencias reales, no erratas:

| | India | Europa |
|---|---|---|
| Sarampión | **MR** — sarampión y rubéola | MMR, con paperas |
| Difteria/tétanos/tosferina | **Pentavalente** (DTP+HepB+Hib) | Hexavalente, con la polio dentro |
| Polio | **OPV oral**, con dosis 0 al nacer, **más fIPV** (dosis *fraccionada*) | IPV inyectada entera |
| Citas de lactante | **6, 10 y 14 semanas** | 2, 4 y 6 meses |
| Neumocócica | Solo en algunos estados | Nacional |
| Encefalitis japonesa | Solo en distritos endémicos | No existe |
| Adolescencia | **Td a los 10 y a los 16 años** | Refuerzos distintos |

El PDF **no lleva año impreso**; 2018 es la carpeta en la que la NHM lo publica, y así se cita.
El vigilante de enlaces (`sources_alive`) ya lo incluye: avisará si aparece una edición con año.

## Lo que queda

- **Contenido en hindi**: el índice sigue con **cero documentos** en hindi. La licencia está
  abierta; falta elegir qué páginas de la NHM y del ministerio se indexan y comprobar que el
  texto se extrae (varias de sus páginas se pintan con JavaScript).
- **Números de emergencia**: ya estaban (112, y Tele-MANAS 14416 para salud mental).
- **Sin verificar**: UNICEF India (su material suele llevar derechos propios) y los portales
  estatales.

## 16-sep-2026 · por qué el corpus en hindi sigue teniendo diez documentos

La licencia está abierta desde el 11-sep y aun así no entra nada. **El muro no es legal, es de
codificación**, y está medido sobre cuatro documentos:

| Documento | Fuente | Qué extrae |
|---|---|---|
| Manual de ASHA para el niño pequeño, edición hindi (116 págs) | NHSRC | 192.715 caracteres, **cero devanagari**. Fuentes: KrutiDev010 y KrutiDev240 |
| Notas para formadores VHSNC, hindi (76 págs) | NHM | 30.918 caracteres, **cero devanagari** |
| Centro de salud primaria (IEC) | NHM | 0 caracteres: es una imagen |
| Guía del programa de salud escolar, hindi (56 págs) | NHM | 78 % devanagari — **el mejor caso, y aun así corrompe palabras** |

El mejor caso es el que decide: con fuente Kokila el texto se lee, pero llega con vocales
dobladas y letras perdidas — «विद्ालय» por «विद्यालय», «इसतेमाल» por «इस्तेमाल», «हैै» por «है».
Para un corpus cuya promesa es citar literalmente, eso no vale.

**Lo que se descartó, y por qué, para no repetirlo:**

- **Deducir la tabla del propio PDF.** La fuente incrustada declara sus glifos con nombres
  latinos (`A`, `exclam`…) y su `ToUnicode` mapea a letras latinas: el fichero no sabe que es
  devanagari.
- **El conversor académico de referencia** (LTRC, IIIT Hyderabad) **no lleva licencia** en su
  repositorio, así que su tabla no se puede reutilizar.
- **OCR.** Hay tesseract en el servidor y el paquete hindi se instala en un minuto. Se descarta
  para contenido de salud: un dígito mal leído en una dosis o en una edad es exactamente el
  error que este producto existe para no cometer. (Sí valdría como piedra Rosetta para deducir
  la tabla y luego convertir el texto exacto del PDF; es trabajo de verdad y queda apuntado.)
- **Vikaspedia** (C-DAC, gobierno de India) tiene justo lo que hace falta —contenido para padres,
  en hindi, en HTML con Unicode correcto— pero su política **exige pedir permiso por correo**.
  No se usa sin ese permiso. Es la puerta más prometedora y la decisión es del operador.
- **Saudi MoH** (para el árabe, mismo rastreo): sus condiciones **prohíben copiar** contenido del
  portal; la excepción sólo permite enlazar.

**Mientras tanto, lo que sí funciona**: el motor responde en hindi citando fichas del NHS, la OMS
y el CDC, que un padre indio puede abrir y comprobar (el inglés es lengua oficial allí), y desde
hoy el buscador garantiza que entre las tres primeras fuentes haya una legible.
