# Ampliar las marcas por país — lo hecho y lo que falta

6-sep-2026. La única demanda no de marca que nos alcanza en Google son consultas de dosis por
medicamento («calculadora apiretal», «apirofeno 40 mg calculadora»), y compiten contra blogs en
vez de contra el NHS. Ampliar el catálogo de marcas es meterse justo en el nicho que ya funciona.

Este documento se escribió el 6-sep sin contar antes lo que ya había, y decía cosas que no
eran. Reescrito el 7-sep con el catálogo delante.

## Lo que de verdad hay publicado (contado el 7-sep-2026)

**20 marcas con su concentración**, y no solo españolas: Alemania, Brasil, Estados Unidos,
Francia, Italia, México, Argentina, Chile, Colombia, Reino Unido, Irlanda y Portugal.

Este documento decía ayer que no se podían publicar concentraciones de otros mercados porque la
única fuente de dosis del corpus es española. Eso era un marco equivocado, escrito sin contar lo
que había. Lo cierto:

  · Lo que sale de la AEPap es la **dosis por kilo**, que es universal y sí está citada.
  · La **concentración** es un dato del producto. Ninguna de las veinte lleva cita, y todas
    estaban ahí antes.

No es un agujero, porque el diseño lo resuelve por el otro lado: la entradilla de cada página de
medicamento dice, **en los ocho idiomas**, «comprueba siempre la concentración impresa en tu
envase: cambia según el país y la presentación». La autoridad es la caja que el lector tiene en la
mano; la tabla es una comodidad. Añadir una cita por marca seguiría siendo mejor, pero es una
mejora, no una reparación.

## Ya publicadas — no las vuelvas a añadir

`Apiretal` · `Termalgin` · `Gelocatil` · `Efferalgan` · `Doliprane` · `Tachipirina` ·
`Calpol` (incluye la presentación *six plus* 250 mg/5 ml) · `Panadol Children` ·
`Tempra / Tylenol` (MX, AR, CL, CO) · `Tylenol Children's / Infants'` (US, CA) ·
`Tylenol / paracetamol genérico` (BR) · `Ben-u-ron` (DE, PT) ·
`Dalsy` · `Junifen` · `Apirofeno` · `Alivium` (BR) · `Nurofen for Children` (GB, IE, AU, NZ, DE,
IT, PT) · `Advil Children's / Infants'` · `Advil pediátrico / Ibupirac` · `Motrin Children's`

## Lo que sí falta

Poco, y de mercados ya cubiertos por otra marca de la misma familia:

| mercado | candidato | nota |
|---|---|---|
| Francia | Nureflex | el ibuprofeno pediátrico francés; hoy solo está Advil para FR |
| Brasil | Tylenol Bebê / Criança por su nombre propio | el genérico BR ya cubre las dos concentraciones |
| Alemania | Nurofen Junior | «Nurofen for Children» ya incluye DE con 100 mg/5 ml |

**No añadir dipirona/metamizol** (Novalgina en Brasil): no está en la tabla de la AEPap, así que
no hay dosis que citar. Es un fármaco distinto, no una marca más.

## Los alias, que es lo que se añadió el 6-sep

17 nombres comerciales que el motor RECONOCE sin afirmar ninguna concentración — solo dicen de qué
principio activo es cada nombre: ben-u-ron, benuron, paracetamol-ratiopharm, tylenol bebê, tylenol
criança, panadol baby, nureflex, nurofen junior, advil infantil, ibuprofeno pediátrico, brufen,
ibufen, algifor y sus variantes de escritura.

**Descartado a propósito: `perfalgan`.** Es paracetamol **intravenoso**, de hospital. Reconocerlo
haría que a quien pregunta por un vial le respondiéramos con la dosis de un jarabe. Hay un test
que impide que vuelva a entrar (`test_a_hospital_only_product_is_not_recognised`).

## Cómo publicar una cuando esté verificada

1. Añadir la marca en `config/drugs.yaml` bajo su principio activo, con `countries` y `forms`.
2. Comprobar que su concentración en mg/ml está en `strengths_mg_per_ml` del fármaco; si no,
   añadirla ahí también.
3. `uv run pytest tests/test_dose_catalog.py` — comprueba las dos cosas anteriores y unas cuantas
   más (que la marca no cuelgue del fármaco equivocado, que el nombre no apunte a dos).
4. Desplegar. La página se genera sola en los ocho idiomas.
5. Pedir su indexación a mano (ver `ops/INDEXAR.md`).
