"""Wording for the deterministic tools, one table per language (3-sep-2026).

The dose calculator, the rehydration advice, the vaccination schedules and the photo check were
each written as `es = lang == "es"` with two branches. French therefore got the English branch:
a parent asking "quelle dose de Doliprane pour 14 kg ?" in French was answered in English, by a
tool whose whole point is that a person can read it at three in the morning.

The strings live here instead, keyed by language, with English as the fallback for a language
that has not been written yet. Adding a language means adding a block — the tools themselves do
not change.
"""

from __future__ import annotations

from typing import Any

Table = dict[str, Any]

STRINGS: dict[str, Table] = {
    "en": {
        # --- oral rehydration ---
        "ors_under_1_month": "A baby under one month with vomiting or diarrhoea must be seen by a doctor today; do not give rehydration solution without medical advice.",
        "ors_under_2y": "Under 2 years: contact your paediatrician if vomiting or diarrhoea lasts more than 24 hours or the child refuses fluids.",
        "ors_after_vomit": "After a vomit, offer oral rehydration solution in very small amounts: 5–10 ml (one or two teaspoons, by spoon or syringe) every 10 minutes, increasing gradually if there is no further vomiting.",
        "ors_infant": "Infant over 1 month with diarrhoea: roughly 1–1.5 times the usual feed volume, in small amounts and slowly; breastfeeding does not need to stop.",
        "ors_child": "Child aged 1 year or more: about 200 ml of solution for each loose stool, given as 25–30 ml every 10–15 minutes.",
        "ors_sachet": "Make up the sachet exactly as the leaflet says (one sachet per the stated volume of water); do not make it stronger or weaker. Do not use sports drinks, fizzy drinks or juice.",
        "ors_go_er": "Go to the emergency department if fluids will not stay down, there is very little urine, sunken eyes, unusual drowsiness or blood in the stool.",
        # --- dose calculator ---
        "dose_for": "{name} for {kg:g} kg:",
        "dose_refer": "⚠️ Do not give without medical advice: ",
        "dose_line": "• Dose: {mg_min:g}–{mg_max:g} mg every {h0}–{h1} h (max {max_doses} doses/day).",
        "dose_source": "Source: {source}.",
        "dose_check": "Always check the concentration on the bottle. Under 3 months, ask a doctor before giving anything.",
        "dose_warn": {
            "under_3_months_refer": "under 3 months old",
            "below_min_age": "below the minimum age for this drug",
            "below_min_weight": "below the minimum weight for this drug",
            "capped_single_dose": "dose capped at the maximum per dose",
        },
        # --- vaccination schedules ---
        "vax_source": "Source: ",
        "vax_due": "At this age the official schedule lists:",
        "vax_none": "There is no vaccine scheduled at this exact age in the official calendar.",
        "vax_next": "Next: {label} — ",
        # --- photo check ---
        "photo_poor": "I can't assess this photo (too dark, blurry, or not skin). If in doubt, see your paediatrician today; with breathing difficulty, spots that don't fade when pressed, or swollen lips, go to the emergency department.",
        "photo_emergency": "I can see a possible warning sign ({sign}). According to the SEUP, this needs immediate care: call {number} or go to the emergency department now, especially if breathing is difficult.",
        "photo_sign_cyanosis": "blue/grey lips or skin",
        "photo_sign_swelling": "swollen lips or eyelids",
        "photo_petechiae": "I can see spots that may not fade when pressed. Do the glass test: press a clear glass on the spots; if they stay visible through the glass, according to the SEUP you should go to the emergency department today, without waiting. I can't tell you what is causing them.",
        "photo_clear": "I don't see any of the three warning signs I check for (non-blanching spots, blue colour, swollen lips). That does not tell you what it is — a photo cannot replace an examination. If the rash spreads, there is high fever, or your child seems unwell, see your paediatrician today.",
        "photo_unsure": "I can't tell from this photo. If the spots don't fade when pressed with a glass, or there is lip swelling or blue colour, go to the emergency department; otherwise see your paediatrician today.",
    },
    "es": {
        "ors_under_1_month": "Un bebé de menos de un mes con vómitos o diarrea debe ser valorado por un médico hoy; no se dan sueros sin indicación.",
        "ors_under_2y": "Menores de 2 años: consulta con el pediatra si los vómitos o la diarrea duran más de 24 horas o si rechaza los líquidos.",
        "ors_after_vomit": "Tras un vómito, ofrece suero de rehidratación oral en cantidades muy pequeñas: 5–10 ml (una o dos cucharaditas, con cuchara o jeringa) cada 10 minutos, aumentando poco a poco si no vuelve a vomitar.",
        "ors_infant": "Lactante mayor de 1 mes con diarrea: aproximadamente 1–1,5 veces el volumen de su toma habitual, en pequeñas cantidades y despacio; no hace falta suspender la lactancia.",
        "ors_child": "Niño a partir de 1 año: unos 200 ml de suero por cada deposición diarreica, dándolo en tandas de 25–30 ml cada 10–15 minutos.",
        "ors_sachet": "Prepara el sobre exactamente como dice el prospecto (un sobre por la cantidad de agua indicada); no lo diluyas más ni menos. No uses bebidas isotónicas, refrescos ni zumos.",
        "ors_go_er": "Acude a urgencias si no consigue retener líquidos, orina muy poco, tiene los ojos hundidos, está muy decaído o hay sangre en las heces.",
        "dose_for": "{name} para {kg:g} kg:",
        "dose_refer": "⚠️ No dar sin consultar: ",
        "dose_line": "• Dosis: {mg_min:g}–{mg_max:g} mg cada {h0}–{h1} h (máx. {max_doses} dosis/día).",
        "dose_source": "Fuente: {source}.",
        "dose_check": "Comprueba siempre la concentración del envase. Si tiene menos de 3 meses, consulta antes de dar nada.",
        "dose_warn": {
            "under_3_months_refer": "menor de 3 meses",
            "below_min_age": "por debajo de la edad mínima del fármaco",
            "below_min_weight": "por debajo del peso mínimo del fármaco",
            "capped_single_dose": "dosis limitada al máximo por toma",
        },
        "vax_source": "Fuente: ",
        "vax_due": "A esta edad tocan, según el calendario oficial:",
        "vax_none": "A esta edad no hay ninguna vacuna programada en el calendario oficial.",
        "vax_next": "Siguiente cita: {label} — ",
        "photo_poor": "No puedo valorar esta foto (poca luz, desenfoque o no se ve la piel). Si dudas, consulta hoy con el pediatra; ante dificultad para respirar, manchas que no desaparecen al presionar o hinchazón de labios, acude a urgencias.",
        "photo_emergency": "Veo un posible signo de alarma ({sign}). Según la SEUP, esto requiere atención inmediata: llama al {number} o acude a urgencias ahora, sobre todo si le cuesta respirar.",
        "photo_sign_cyanosis": "labios o piel azulados",
        "photo_sign_swelling": "hinchazón de labios o párpados",
        "photo_petechiae": "Veo manchas que podrían no desaparecer al presionar. Haz la prueba del vaso: aprieta un vaso transparente sobre la mancha; si sigue viéndose a través del cristal, según la SEUP hay que acudir a urgencias hoy, sin esperar. No puedo decirte qué la causa.",
        "photo_clear": "No veo en la foto ninguno de los tres signos de alarma que compruebo (manchas que no desaparecen al presionar, coloración azulada, hinchazón de labios). Eso no me dice qué es: una foto no sustituye a la exploración. Si el sarpullido se extiende, hay fiebre alta, o tu hijo está decaído, consulta con el pediatra hoy.",
        "photo_unsure": "No lo veo claro en esta foto. Si las manchas no desaparecen al presionarlas con un vaso, o hay hinchazón de labios o color azulado, acude a urgencias; si no, consulta hoy con el pediatra.",
    },
    "fr": {
        "ors_under_1_month": "Un bébé de moins d'un mois qui vomit ou qui a la diarrhée doit être vu par un médecin aujourd'hui ; on ne donne pas de soluté de réhydratation sans avis médical.",
        "ors_under_2y": "Avant 2 ans : contactez votre pédiatre si les vomissements ou la diarrhée durent plus de 24 heures, ou si l'enfant refuse de boire.",
        "ors_after_vomit": "Après un vomissement, proposez le soluté de réhydratation orale en très petites quantités : 5 à 10 ml (une ou deux cuillères à café, à la cuillère ou à la seringue) toutes les 10 minutes, en augmentant peu à peu s'il ne revomit pas.",
        "ors_infant": "Nourrisson de plus de 1 mois avec diarrhée : environ 1 à 1,5 fois le volume de sa tétée ou de son biberon habituel, en petites quantités et lentement ; il n'y a pas besoin d'arrêter l'allaitement.",
        "ors_child": "Enfant à partir de 1 an : environ 200 ml de soluté après chaque selle liquide, donnés par 25 à 30 ml toutes les 10 à 15 minutes.",
        "ors_sachet": "Préparez le sachet exactement comme l'indique la notice (un sachet pour la quantité d'eau indiquée) ; ne le diluez ni plus ni moins. N'utilisez pas de boissons pour sportifs, de sodas ni de jus de fruits.",
        "ors_go_er": "Allez aux urgences si l'enfant ne garde pas les liquides, s'il urine très peu, s'il a les yeux creux, s'il est anormalement somnolent ou s'il y a du sang dans les selles.",
        "dose_for": "{name} pour {kg:g} kg :",
        "dose_refer": "⚠️ Ne pas donner sans avis médical : ",
        "dose_line": "• Dose : {mg_min:g}–{mg_max:g} mg toutes les {h0}–{h1} h (max. {max_doses} doses par jour).",
        "dose_source": "Source : {source}.",
        "dose_check": "Vérifiez toujours la concentration inscrite sur le flacon. Avant 3 mois, demandez à un médecin avant de donner quoi que ce soit.",
        "dose_warn": {
            "under_3_months_refer": "moins de 3 mois",
            "below_min_age": "en dessous de l'âge minimum de ce médicament",
            "below_min_weight": "en dessous du poids minimum de ce médicament",
            "capped_single_dose": "dose limitée au maximum par prise",
        },
        "vax_source": "Source : ",
        "vax_due": "À cet âge, le calendrier officiel prévoit :",
        "vax_none": "Aucun vaccin n'est prévu exactement à cet âge dans le calendrier officiel.",
        "vax_next": "Prochain rendez-vous : {label} — ",
        "photo_poor": "Je ne peux pas évaluer cette photo (trop sombre, floue, ou on n'y voit pas la peau). Dans le doute, consultez votre pédiatre aujourd'hui ; en cas de gêne respiratoire, de taches qui ne s'effacent pas à la pression ou de lèvres gonflées, allez aux urgences.",
        "photo_emergency": "Je vois un signe d'alerte possible ({sign}). Selon la SEUP, cela demande une prise en charge immédiate : appelez le {number} ou allez aux urgences maintenant, surtout si la respiration est difficile.",
        "photo_sign_cyanosis": "lèvres ou peau bleutées ou grises",
        "photo_sign_swelling": "lèvres ou paupières gonflées",
        "photo_petechiae": "Je vois des taches qui pourraient ne pas s'effacer à la pression. Faites le test du verre : appuyez un verre transparent sur les taches ; si elles restent visibles à travers le verre, selon la SEUP il faut aller aux urgences aujourd'hui, sans attendre. Je ne peux pas vous dire ce qui les provoque.",
        "photo_clear": "Je ne vois sur la photo aucun des trois signes d'alerte que je vérifie (taches qui ne s'effacent pas à la pression, coloration bleutée, lèvres gonflées). Cela ne dit pas ce que c'est : une photo ne remplace pas un examen. Si l'éruption s'étend, s'il y a une forte fièvre, ou si votre enfant est abattu, consultez votre pédiatre aujourd'hui.",
        "photo_unsure": "Je n'arrive pas à trancher sur cette photo. Si les taches ne s'effacent pas quand on appuie avec un verre, ou s'il y a un gonflement des lèvres ou une coloration bleutée, allez aux urgences ; sinon, consultez votre pédiatre aujourd'hui.",
    },
}


def tool_strings(lang: str) -> Table:
    """The table for this language, falling back to English rather than to a blank string."""
    return STRINGS.get(lang, STRINGS["en"])


def data_lang(node: dict[str, Any], lang: str) -> str:
    """Which language of a translated data node to read.

    The catalogues (vaccines, the warning-signs checklist) carry one key per language. Asking for
    a language the node does not have used to return None and render an empty string; this picks
    English instead, and says so by returning the key it chose.
    """
    return lang if lang in node else "en"
