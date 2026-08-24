# Catálogo de fuentes — PediBot

Inventario de los 49 PDF de `FUENTES/` (los 2 PDF del dossier de inversores están en la raíz y no son fuentes) (24-ago-2026). Los PDF **no se commitean**; este catálogo sí. Columna `uso`: `publico` = hoja de organismo público / sociedad científica destinada a padres, se indexa y se cita con enlace al original; `citar_solo` = obra de referencia clínica, se indexa para respaldo y se cita, pero no se reproduce en artículos; `excluido` = no entra en el índice; `?` = decidir (duda D-03).

`texto`: ✅ extraíble · 🔍 escaneado, necesita OCR · ⚠️ corrupto/protegido.

## Hojas "Información para padres" — SEUP (Sociedad Española de Urgencias de Pediatría)

Serie numerada 1-27 (faltan algunos números). Año no consta en el texto → duda D-05 (probablemente 2019-2023).

| Fichero | Tema | Franja edad | texto | uso |
|---|---|---|---|---|
| `1_alteraciones.pdf` | Alteraciones conductuales (detección, prevención, manejo) | escolar/adolescente | ✅ | publico |
| `2_Anafilaxia.pdf` | Anafilaxia | todas | ✅ | publico · **red flag** |
| `3_Ansiedad.pdf` | Ansiedad | escolar/adolescente | ✅ | publico |
| `4_Bronquiolitis.pdf` | Bronquiolitis | lactante | ✅ | publico · red flag parcial |
| `Subidos/5_Catarro.pdf` | Catarro de vías altas | todas | ✅ | publico |
| `6_Cefalea.pdf` | Cefalea | escolar/adolescente | ✅ | publico |
| `7_Colico.pdf` | Cólico del lactante | lactante | ✅ | publico |
| `8_Autolesiva.pdf` | Conducta autolesiva no suicida | adolescente | ✅ | publico · **salud mental** |
| `9_Suicida.pdf` | Conducta suicida | adolescente | ✅ | publico · **salud mental** |
| `Subidos/10_Convulsion.pdf` | Convulsión febril | lactante/preescolar | ✅ | publico · **red flag** |
| `11_Crisisasma.pdf` | Crisis asmática | todas | ✅ | publico · red flag parcial |
| `Subidos/12_Dolorabdominal.pdf` | Dolor abdominal | todas | ✅ | publico |
| `13_Sollozos.pdf` | Espasmos del sollozo | lactante/preescolar | ✅ | publico |
| `Subidos/14_Estreñimiento.pdf` | Estreñimiento | todas | ✅ | publico |
| `Subidos/15_Fiebre.pdf` | Fiebre | todas | ✅ | publico · **la más consultada** |
| `Subidos/16_Gastroente.pdf` | Gastroenteritis aguda | todas | ✅ | publico |
| `Subidos/17_Golpecalor.pdf` | Golpe de calor | todas | ✅ | publico · **red flag** |
| `Subidos/18_Intoxicacion.pdf` | Intoxicaciones | todas | ✅ | publico · **red flag** |
| `Subidos/19_Laringitis.pdf` | Laringitis / crup | lactante/preescolar | ✅ | publico |
| `Subidos/20_Neumonia.pdf` | Neumonía | todas | ✅ | publico |
| `Subidos/21_Otitis_media.pdf` | Otitis media aguda | lactante/preescolar | ✅ | publico |
| `22_Sincope.pdf` | Síncope | escolar/adolescente | ✅ | publico |
| `23_GuiaConductaaliment.pdf` | Trastornos de la conducta alimentaria | adolescente | ✅ | publico · salud mental |
| `Subidos/24_Traumatismo-craneal_nueva.pdf` | Traumatismo craneal | todas | ✅ | publico · **red flag** |
| `25_Urticaria.pdf` | Urticaria | todas | ✅ | publico |
| `26_Procedimientos.pdf` | Sedoanalgesia en urgencias | todas | ✅ | publico |
| `Subidos/27_Vomitos.pdf` | Vómitos | todas | ✅ | publico |

## Triaje / urgencias / primeros auxilios

| Fichero | Descripción | Organismo | texto | uso |
|---|---|---|---|---|
| `Subidos/acudir_urgencias.pdf` | "¿Debo acudir a urgencias?" — guía rápida por síntoma (piel, comportamiento, respiración…) | por identificar (formato SEUP/AEP) | ✅ | publico · **fuente canónica de `red_flags.yaml`** |
| `Subidos/guia_primeros_auxilios.pdf` | Guía práctica de primeros auxilios para padres (Casado Flores, Jiménez García; H. Niño Jesús). ISBN 978-84-16732-74-6 (2017) | Hospital Niño Jesús / editorial | ✅ | ? (libro con ISBN — probablemente `citar_solo`) |
| `8_ACCIONES_NO_2020.pdf` | 8 acciones que NO hacer ante contacto con tóxico (2020) | SEUP (Grupo Intoxicaciones) | ✅ | publico · red flag |

## Alimentación, crecimiento, desarrollo, prevención

| Fichero | Descripción | Organismo / año | texto | uso |
|---|---|---|---|---|
| `Subidos/recomendaciones_aep_sobre_alimentacio_n_complementaria.pdf` | Recomendaciones sobre alimentación complementaria (Comité de Lactancia) | AEP, 2018 | ✅ | publico |
| `Subidos/Alimentacion_OMS.pdf` | WHO Guideline for complementary feeding 6-23 months | OMS, 2023 (inglés) | ✅ | publico |
| `Subidos/Sedentarismo_OMS.pdf` | Guidelines on physical activity, sedentary behaviour and sleep < 5 años | OMS, 2019 (inglés) | ✅ | publico |
| `Subidos/Autismo_OMS.pdf` | Autism spectrum disorders — meeting report | OMS, 2013 (inglés) | ✅ | ? (informe de reunión, poco útil para padres) |
| `Subidos/CalendarioVacunacion_Todalavida.pdf` | Calendario común de vacunación a lo largo de toda la vida, 2025 | Ministerio de Sanidad | ✅ | publico · **fuente de la herramienta de vacunas** |
| `3-cuidame_esp.pdf` | "Cuídame: guía para madres y padres" | Junta de Andalucía (Consejería de Salud) | ✅ | publico |
| `Subidos/Guia_Cuidame_comienzo_vida.pdf` | "Cuídame: orientaciones para el comienzo de la vida" (16 MB) | Junta de Andalucía | ✅ | publico |
| `Subidos/cuidados_recien_nacido.pdf` | Cuidados generales del recién nacido sano (Doménech, González, Rodríguez-Alarcón) | AEP — Protocolos de Neonatología | ✅ | publico |
| `Subidos/ECE101_version1.2.pdf` | Child Growth and Development (OER, College of the Canyons, 20 MB, inglés) | OER — licencia CC | ✅ | citar_solo (desarrollo, no clínico) |
| `Subidos/Obesidad_AAP.pdf` | Clinical Practice Guideline: obesity in children and adolescents | AAP, 2023 (inglés) | ✅ | citar_solo |
| `Subidos/Hiperactividad_AAP.pdf` | Clinical Practice Guideline: ADHD | AAP, 2019 (inglés) | ✅ | citar_solo |
| `Subidos/Sindromedown_AAP.pdf` | Health supervision for children with Down syndrome | AAP, 2022 (inglés) | ✅ | citar_solo |
| `Subidos/neonatal_AAP.pdf` | Neonatal Care — compendium of AAP guidelines | AAP (inglés) | ✅ | ? (compendio con copyright AAP) |

## Referencia clínica (nivel profesional)

| Fichero | Descripción | Organismo / año | texto | uso |
|---|---|---|---|---|
| `Guia_dosificacion_3_edicion.pdf` | Guía rápida de dosificación práctica en pediatría, 3.ª ed. (8 MB) | AEPap | ✅ | citar_solo · **fuente de la calculadora de dosis** (transcripción a tablas, F-06) |
| `Guia_Antibiotico_Pediatria.pdf` | Guía de tratamiento antibiótico en pediatría | H. U. Donostia (Osakidetza) | ✅ | citar_solo (el bot NUNCA recomienda antibióticos; solo para contexto) |
| `Manual-de-Pediatria.pdf` | Manual de Pediatría (transcripción de clases, 22 MB) | Pontificia U. Católica de Chile (INNOVADOC) | ✅ | ? (uso docente; probablemente `citar_solo`) |
| `cub-ch-20-01-guideline-2016-esp-pediatria-completo.pdf` | Pediatría. Diagnóstico y tratamiento (638 p.) | Ecimed, La Habana, 2016 | ✅ | ? (obra editorial; también 2016 y de otro sistema sanitario) |
| `Subidos/las_50_principales_consultas.pdf` | "Las 50 principales consultas en pediatría de atención primaria" (10 MB) | por identificar tras OCR (¿AEPap/Lúa Ediciones?) | 🔍 | ? |
| `dermatologia_pedi.pdf` | Hurwitz/Morelli — Dermatología pediátrica (Elsevier) | Elsevier | ⚠️ texto corrupto (8 k palabras de 1,9 MB) | **excluido** (copyright editorial + inservible) |

## Resumen

- 49 ficheros · 27 hojas SEUP · 3 de triaje/primeros auxilios · 13 de alimentación/desarrollo/prevención · 6 de referencia clínica · 1 excluido. Fuente de verdad para el código: `config/fuentes.yaml`.
- OCR pendiente: 1 (`las_50_principales_consultas.pdf`; `14_Estreñimiento.pdf` SÍ tiene capa de texto para pymupdf — pdftotext fallaba por el nombre con ñ). Licencia por decidir (`?`): 7.
- Idiomas: español 41, inglés 9.
- Faltan (candidatas, ver `IDEAS.md` F-01…F-05): hojas "En Familia" AEP, AEPap "Familia y salud", Toxicología, calendarios autonómicos.
