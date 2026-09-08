"""Una consulta de verdad por el camino de verdad, sin gastar un céntimo.

El watchdog vigilaba nuestra infraestructura —el proceso, el saldo, el disco, las unidades— y
nunca preguntaba lo único que le importa a quien pregunta: si una consulta funciona. El 8-sep-2026
un «112» sin comillas en `synonyms.yaml` tuvo el buscador devolviendo un 500 en inglés durante
quién sabe cuánto, con `/api/health` en verde todo el tiempo, porque el proceso estaba en pie.

Esto recorre el trozo que se rompió —expansión de sinónimos, taxonomía, búsqueda en el índice—
con el modelo desconectado, así que no cuesta nada y se puede ejecutar cada diez minutos. Lo que
NO cubre es la redacción, que sí cuesta; para eso está `ops/smoke.py --ask`, que se lanza a mano
o una vez al día.

Las preguntas son corrientes a propósito. Una consulta rara que no encuentra nada es un resultado
legítimo; una corriente que no encuentra nada es una avería.
"""

from __future__ import annotations

from pathlib import Path

#: Una por idioma, de las que el corpus responde de sobra. Si alguna deja de encontrar fuentes,
#: no es que falte contenido: es que algo se ha roto por el camino.
PREGUNTAS: dict[str, str] = {
    "en": "my 3-year-old has a fever, what should I do?",
    "es": "mi hija de 3 años tiene fiebre, ¿qué hago?",
    "fr": "ma fille de 3 ans a de la fièvre, que faire ?",
    "de": "meine Tochter hat Fieber, was soll ich tun?",
    "ru": "у моей дочери температура, что делать?",
    "ar": "ابنتي عندها حمى، ماذا أفعل؟",
    "pt": "minha filha está com febre, o que faço?",
    "hi": "मेरी बेटी को बुखार है, क्या करूँ?",
}

#: La palabra que tumbó el buscador en inglés. Se queda aquí con nombre y apellidos: era un
#: término de `synonyms.yaml` que el cargador de YAML leía como número.
PREGUNTAS["en_emergency"] = "when should I take my child to the emergency department?"


def revisa(index_db: Path, config_dir: Path) -> list[str]:
    """Los problemas encontrados, vacío si todo va. No lanza: un fallo aquí es un aviso."""
    problemas: list[str] = []
    try:
        from pedibot.bot.retrieval import Retriever, Synonyms
        from pedibot.index.store import Index
        from pedibot.ingest.classify import Taxonomy

        # sin `llm`: la expansión se queda en las tablas locales y esto no cuesta nada
        recuperador = Retriever(
            Index(index_db),
            Synonyms(config_dir / "synonyms.yaml", config_dir / "drugs.yaml"),
            llm=None,
            taxonomy=Taxonomy(config_dir / "taxonomia.yaml"),
        )
    except Exception as e:  # noqa: BLE001
        return [f"🚨 El buscador no se puede ni construir: {type(e).__name__}: {e}"]

    for etiqueta, pregunta in PREGUNTAS.items():
        idioma = etiqueta.split("_")[0]
        try:
            hits, _ = recuperador.search(pregunta, idioma)
        except Exception as e:  # noqa: BLE001 — esto es justo lo que se busca
            problemas.append(
                f"🚨 El buscador revienta en {etiqueta}: {type(e).__name__}: {e} "
                f"(«{pregunta[:40]}…»). Una consulta así devuelve un 500 al padre."
            )
            continue
        if not hits:
            problemas.append(
                f"⚠️ Sin fuentes para una pregunta corriente en {etiqueta}: «{pregunta[:40]}…». "
                "El corpus responde esto de sobra, así que algo se ha roto por el camino."
            )
    return problemas
