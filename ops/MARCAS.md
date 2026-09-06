# Ampliar las marcas por país — lo hecho y lo que falta

6-sep-2026. La única demanda no de marca que nos alcanza en Google son consultas de dosis por
medicamento («calculadora apiretal», «apirofeno 40 mg calculadora»), y compiten contra blogs en
vez de contra el NHS. Ampliar el catálogo de marcas es meterse justo en el nicho que ya funciona.

Pero hay un límite duro que decide cómo se hace.

## El límite: una sola fuente de dosis, y es española

En todo el corpus hay **exactamente un documento marcado `dose_source: true`**: la *Guía rápida de
dosificación práctica en pediatría* de la AEPap. La **dosis por kilo** sale de ahí y es la misma
en todos los países. Lo que cambia de un mercado a otro es la **concentración del envase**, y eso
la guía española no lo cubre.

Publicar «ben-u-ron Saft 200 mg/5 ml» sería afirmar una cifra que no podemos citar, en la única
parte de la web donde una cifra equivocada se convierte en una dosis equivocada. Así que no se
publica hasta verificarla.

## Hecho hoy: los alias, que no afirman ninguna cifra

Un alias solo dice «esto es paracetamol» o «esto es ibuprofeno». No dice cuánto lleva el bote, así
que no hay nada que verificar más allá del principio activo, que es público y no discutible.

Añadidos a `config/drugs.yaml` (17):

- **paracetamol** — ben-u-ron, ben u ron, benuron, paracetamol-ratiopharm, tylenol bebe,
  tylenol bebê, tylenol criança, tylenol crianca, panadol baby
- **ibuprofeno** — nureflex, nurofen junior, advil infantil, ibuprofeno pediatrico,
  ibuprofeno pediátrico, brufen, ibufen, algifor

Con eso, «cuánto ben-u-ron le doy» encuentra el paracetamol en vez de no encontrar nada.

**Descartado a propósito: `perfalgan`.** Es paracetamol **intravenoso**, de hospital. Reconocerlo
haría que a quien pregunta por un vial le respondiéramos con la dosis de un jarabe. Hay un test
que impide que vuelva a entrar (`test_a_hospital_only_product_is_not_recognised`).

## Pendiente: las páginas de marca, una por una

Para que un nombre tenga su propia página con tabla hace falta su lista de presentaciones. Estos
son los candidatos por mercado. **Cada concentración hay que leerla del prospecto del producto
antes de escribirla aquí** — el buscador no vale, el prospecto sí.

| mercado | marca | principio activo | presentaciones a verificar |
|---|---|---|---|
| Alemania | ben-u-ron | paracetamol | Saft; supositorios por peso |
| Alemania | Nurofen Junior | ibuprofeno | suspensión 2 % y 4 % |
| Brasil | Tylenol Bebê | paracetamol | gotas |
| Brasil | Tylenol Criança | paracetamol | suspensión |
| Brasil | Alivium | ibuprofeno | gotas y suspensión *(ya está el nombre, faltan formas)* |
| Francia | Nureflex | ibuprofeno | suspensión pediátrica |
| Portugal | Ben-u-ron | paracetamol | xarope |
| Reino Unido | Calpol Six Plus | paracetamol | suspensión *(distinta del Calpol infantil ya publicado)* |
| Italia | Nurofen febbre e dolore | ibuprofeno | sospensione |

**No añadir dipirona/metamizol** (muy común en Brasil como Novalgina): no está en la tabla de la
AEPap, así que no tenemos dosis que citar para ella. Es un fármaco distinto, no una marca más.

## Cómo publicar una cuando esté verificada

1. Añadir la marca en `config/drugs.yaml` bajo su principio activo, con `countries` y `forms`.
2. Comprobar que su concentración en mg/ml está en `strengths_mg_per_ml` del fármaco; si no,
   añadirla ahí también.
3. `uv run pytest tests/test_dose_catalog.py` — comprueba las dos cosas anteriores y unas cuantas
   más (que la marca no cuelgue del fármaco equivocado, que el nombre no apunte a dos).
4. Desplegar. La página se genera sola en los ocho idiomas.
5. Pedir su indexación a mano (ver `ops/INDEXAR.md`).
