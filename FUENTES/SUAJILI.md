# Fuentes en suajili — resultado del rastreo de licencias (18-sep-2026)

> Fase 3 del plan de África. Mismo método que el alemán, el francés y el árabe: cada licencia se
> lee en la página legal del sitio, no se supone. Lo que no tiene licencia abierta escrita no
> entra, por buena que sea la fuente.

El suajili lo hablan más de doscientos millones de personas en Kenia, Tanzania, Uganda y el este
de la RD del Congo. El triaje ya lo entiende —las 83 reglas, el detector y los avisos— y lo único
que falta para que sea una lengua completa es **corpus**: documentos que un padre pueda abrir y
que nosotros podamos citar.

## Lo que se verificó

| Fuente | Quién es | Qué hay en suajili | Licencia leída | Veredicto |
|---|---|---|---|---|
| **MedlinePlus** (`medlineplus.gov/languages/swahili.html`) | La biblioteca nacional de medicina de EE. UU., que el proyecto ya usa (74 documentos) | Un índice con **65 materiales**, pero **ninguno propio**: todos enlazan fuera | La página índice es dominio público; los materiales, no | ⚠️ es una puerta, no una fuente |
| **Immunize.org** (antes IAC) | Quien traduce las hojas de vacunas (VIS) de los CDC | **36 materiales**, justo los de vacunas, que es lo más visitado de este sitio | «© Copyright 2026 Immunize». No hay página de permisos ni cláusula de reutilización | ❌ cerrada |
| **Health Information Translations** (Ohio State y hospitales de Ohio) | Traduce hojas para pacientes a decenas de lenguas | **15 materiales** (emergencias químicas, ántrax, etc.), poco pediátricos | Sin cláusula localizable; su `copyright.php` da 404 | ❌ cerrada |
| **OMS en suajili** (`who.int/sw`) | — | **No existe**: devuelve 404. El suajili no es lengua oficial de la OMS | — | ❌ no hay |
| **OMS AFRO** (`afro.who.int`) | La oficina regional africana, que sí publica material propio | La portada de temas de salud no ofrece suajili | (CC BY-NC-SA 3.0 IGO si lo hubiera) | ❌ no hay |
| **Hesperian Health Guides** | *Where There Is No Doctor*, escrito justo para donde no hay médico | Existe el libro de salud ambiental en suajili (`sw.hesperian.org`) | Sólo «© Copyright Hesperian Health Guides» en el pie; no se localizó Creative Commons en la edición suajili | ❌ cerrada sin permiso escrito |
| **Healthy Roads Media** | Materiales multilingües de salud | Tiene sección de suajili | El sitio no respondió al rastreo | ❓ segunda ronda |
| **Ministerios de Kenia y Tanzania** | Las fuentes nacionales | Material existe | Sin cláusula de licencia publicada, como casi todos los ministerios africanos (ya pasó con los números de emergencia) | ❌ sin licencia escrita |

## La foto honesta

**No hay hoy un corpus pediátrico en suajili con licencia abierta verificable.** Lo más cercano
—las hojas de vacunas de Immunize.org— es exactamente lo que este proyecto más usaría, y está
cerrado. El patrón se repite: el material existe, alguien lo tradujo bien, y nadie le puso una
licencia.

Eso no es un fracaso del rastreo: **es el dato que justifica la decisión de la fase 3** (L183).
El suajili entra por la capa de seguridad —el aviso rojo en su lengua, que es lo que salva— y la
explicación larga sale en inglés, que es lengua oficial en Kenia, Tanzania y Uganda, con fuentes
que el lector puede abrir. Prometer la respuesta entera en suajili sin nada que citar sería
exactamente lo que el proyecto no hace.

## Qué haría falta para cambiarlo

Por orden de probabilidad, no de calidad:

1. **Escribir a Immunize.org.** Son una organización sin ánimo de lucro de salud pública y su
   material es una traducción de documentos de dominio público de los CDC. Un permiso por escrito
   para las hojas de vacunas abriría de golpe la parte más visitada del sitio. Es el mismo camino
   que está pendiente con Vikaspedia para el hindi.
2. **Hesperian.** Su HealthWiki ha usado Creative Commons en otras ediciones; merece una consulta
   directa antes de darlo por cerrado.
3. **OMS AFRO.** Si publican material en suajili bajo la licencia habitual de la OMS, entra solo:
   ya tenemos 212 documentos suyos y el cargador los reconoce.

Mientras tanto, el puente de sinónimos (`sw_en` y `sw_es` en `config/synonyms.yaml`) hace que una
pregunta en suajili llegue a los documentos ingleses y castellanos que sí podemos citar. Medido:
«mtoto ana homa» pasó de **cero resultados** a la hoja del NHS sobre la fiebre.
