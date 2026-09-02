# Fuentes francesas — resultado del rastreo de licencias (2-sep-2026)

> Paso 1 de la fase francesa («primero fuentes»). Cada licencia se leyó en la página legal del
> sitio, no se supuso. La misma criba que en agosto descartó a la AAP, Raising Children y
> KidsHealth y dejó entrar al NHS (OGL), MedlinePlus/CDC (dominio público) y la OMS (CC BY-NC-SA).

## Lo que se verificó

| Fuente | Quién es | Licencia leída | Veredicto |
|---|---|---|---|
| **Santé publique France** (santepubliquefrance.fr, vaccination-info-service.fr) | La agencia de salud pública — el equivalente del NHS para padres | «Tous droits réservés». Reproducción solo «à des fins de recherche ou d'étude personnelle… ne peuvent être ni vendues ni utilisées à des fins commerciales»; cualquier otro uso exige «autorisation écrite formelle» (droits@santepubliquefrance.fr) | ❌ cerrada sin permiso escrito |
| **ameli.fr** (Assurance Maladie) | La seguridad social; contenido de salud para pacientes excelente | Todos los derechos reservados; «sauf autorisation formelle écrite préalable», solo consulta individual y privada. Permiso: CNAM, París | ❌ cerrada sin permiso escrito |
| **OMS en francés** (who.int/fr) | Fichas de enfermedades en francés | CC BY-NC-SA — la misma licencia ya aceptada el 25-ago para la OMS en inglés y español | ✅ usable ya, mismas condiciones |
| **Canada.ca en francés** (canada.ca/fr/sante-publique) | Gobierno de Canadá; mucho contenido pediátrico en francés correcto | «Reproduction à des fins non commerciales» libre y sin permiso, con diligencia de exactitud + título + autor + URL de origen. Comercial: prohibido sin permiso. Símbolos oficiales: nunca | ✅ usable, clase NC como la OMS |
| **sante.gouv.fr** (Ministerio) | El calendario vacunal y documentos oficiales | **Sin verificar**: la web está detrás de un WAF con CAPTCHA (Cegedim) que bloquea la lectura de las mentions légales. Por ley (CRPA/Etalab) los documentos administrativos son reutilizables por defecto, pero no he podido leer su página para confirmarlo | ❓ pendiente |
| service-public.gouv.fr | Fichas prácticas administrativas | Licence Ouverte (Etalab) según su reputación; contenido clínicamente fino | ⏳ segunda ronda |
| HAS, ONE (Bélgica), CHUV (Suiza), mpedia (AFPA), naitreetgrandir (Quebec) | Otros candidatos | Sin verificar aún | ⏳ segunda ronda |

## La foto honesta

**El corazón del contenido francés para padres está legalmente cerrado** — Santé publique
France y ameli son el SEUP+AEP de Francia, y ambos exigen permiso escrito. El camino abierto
(OMS-FR + Canadá) cubre enfermedades y crianza en buen francés, pero con dos costes: parte de la
guía práctica sería canadiense (sistema sanitario distinto, se debe decir), y el calendario y las
particularidades francesas dependen del ministerio (pendiente de verificar).

**Nota**: el calendario vacunal francés ya está transcrito y publicado en `/vaccines/fr` desde
hoy — eso es una tabla de datos oficiales citada, no una reproducción de contenido.

## Decisión pendiente del operador (bloqueante para la forma del corpus)

- **Opción A**: corpus abierto (OMS-FR + Canadá + lo que verifique de Etalab), sin SpF ni ameli.
- **Opción B**: pedir permiso por correo a droits@santepubliquefrance.fr y a la CNAM antes de
  construir; PediBot es gratis para los padres, sin anuncios y nombra la fuente en cada frase —
  hay una posibilidad real de que digan que sí.
- **Opción C (recomendada)**: las dos a la vez — empezar con el corpus abierto mientras el
  correo está en vuelo, y ampliar si contestan que sí.
