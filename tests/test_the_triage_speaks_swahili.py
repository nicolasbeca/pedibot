"""El triaje en suajili, en los dos sentidos (18-sep-2026).

Fase 3 del plan de África, y el orden lo mandó el propio detector de idioma, que lo lleva escrito
en su docstring desde que existe: «A language only joins here once it has its own triage
patterns». Adivinar el idioma de un mensaje que la capa de seguridad no sabe leer es peor que
quedarse en inglés.

Medido antes de escribir nada: de diez frases de urgencia en suajili, **cero** disparaban nada, y
el detector las tomaba por inglés o portugués. Ahora las 83 reglas tienen patrones en suajili y
aquí está la comprobación de que saltan — que no es lo mismo que estar escritos (L172).

Y la otra mitad, siempre: veinte frases de la vida corriente de un niño, en suajili, que NO pueden
dar ninguna alarma. Entre ellas la trampa que ya conocemos en tres lenguas —«nimempa maji ya
mchele», le he dado agua de arroz— que es una madre haciendo exactamente lo que la OMS recomienda.
"""

from __future__ import annotations

import pathlib

import pytest

from pedibot.bot.retrieval import detect_lang
from pedibot.bot.triage import Triage

RAIZ = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def triaje() -> Triage:
    return Triage(RAIZ / "config" / "red_flags.yaml")


#: Una frase de padre por regla. No es el patrón con otras comas: es una frase entera.
CASOS: dict[str, str] = {

    "not_responding": "mtoto wangu hajitambui kabisa",
    "seizure": "mtoto wangu ana degedege sasa hivi",
    "severe_breathing": "mtoto wangu hapumui vizuri na mbavu zinaingia ndani",
    "anaphylaxis": "midomo imevimba na hapumui vizuri",
    "choking": "amekwama kitu kooni na anasongwa",
    "mottled_skin": "ngozi yake ina madoa na amepauka sana",
    "head_injury_loss_consciousness": "amegonga kichwa na amezimia",
    "severe_bleeding": "jeraha linatoka damu nyingi na damu haikomi",
    "open_fracture": "mfupa umevunjika na unaonekana nje",
    "petechiae_fever": "ana madoa mekundu hayapotei nikibonyeza",
    "infant_fever_under_3_months": "mtoto mchanga ana homa tangu usiku",
    "very_high_fever": "ana homa kali sana tangu asubuhi",
    "moderate_breathing": "mtoto wangu anapumua haraka tangu jana",
    "drowsy_irritable": "amelala sana na hataki kuamka",
    "dehydration": "macho yamebonyea na hakojoi tangu asubuhi",
    "vomiting_headache": "kichwa kinauma sana na anatapika",
    "vomiting_after_head_injury": "amegonga kichwa na sasa anatapika",
    "button_battery": "mtoto wangu amemeza betri ya saa",
    "foreign_body_ingestion": "mtoto wangu amemeza sarafu",
    "poisoning": "mtoto wangu amekunywa sumu ya panya",
    "severe_abdominal_pain": "tumbo linauma sana tangu jana usiku",
    "deformity_fracture": "mkono umepinda baada ya kuanguka",
    "newborn_refusing_feeds": "mchanga anakataa kunyonya tangu jana",
    "burn": "ameungua na maji ya moto mkononi",
    "bilious_or_bloody_vomit": "matapishi yana damu",
    "blood_in_stool": "kuna damu kwenye kinyesi cha mtoto",
    "abdominal_pain_localised_or_worsening": "tumbo linauma upande wa kulia tangu jana",
    "eating_disorder_signs": "binti yangu anajitapisha baada ya kula",
    "neuro_deficit": "hawezi kusogeza mkono wa kulia",
    "headache_warning_signs": "kichwa kinauma na kinamwamsha usiku",
    "suicidal_ideation": "mwanangu anasema atajiua",
    "self_harm": "amejikata mikono kwa wembe",
    "neck_stiffness": "shingo ngumu na ana homa",
    "meningitis_signs": "mwanga unamuumiza machoni na ana homa",
    "deep_wound": "ana jeraha la kina mguuni",
    "cannot_swallow_drooling": "hawezi kumeza na anadondosha mate",
    "mastoiditis": "imevimba nyuma ya sikio",
    "blood_in_urine": "kuna damu kwenye mkojo",
    "fluid_from_ear_or_nose": "amegonga kichwa na damu yanatoka sikioni",
    "cold_extremities_with_fever": "ana homa na mikono baridi",
    "snakebite": "mtoto wangu ameumwa na nyoka shambani",
    "mammal_bite": "mtoto wangu ameumwa na mbwa",
    "stridor": "anapumua kwa sauti ya kukwaruza",
    "intussusception": "analia kwa mawimbi na kukunja miguu",
    "projectile_vomiting_infant": "anatapika kwa nguvu baada ya kunyonya kila mara",
    "new_diabetes_signs": "ananywa maji sana na anakojoa sana na amepungua uzito",
    "inhaled_foreign_body": "kikohozi kimeanza ghafla baada ya karanga",
    "asthma_not_responding": "dawa ya pumzi haifanyi kazi leo",
    "chemical_in_eye": "sabuni imeingia jichoni",
    "omphalitis": "kitovu kimevimba na kinatoka usaha",
    "carbon_monoxide": "wote tunaumwa na kichwa hapa nyumbani na kuna moshi wa mkaa",
    "near_drowning": "mtoto ameanguka majini leo asubuhi",
    "electric_shock": "mtoto amepigwa na umeme",
    "foreign_body_nose_or_ear": "ameingiza shanga puani",
    "spinal_injury": "ameanguka na hasogezi miguu",
    "blunt_abdominal_trauma": "amepigwa tumboni na sasa linauma sana",
    "smoke_inhalation": "amevuta moshi wa moto jikoni",
    "bruising_and_pallor": "ana michubuko bila kugongwa na amepauka",
    "hypoglycaemia": "ana kisukari na anatetemeka na jasho jingi",
    "sickle_cell_crisis": "ana selimundu na maumivu makali ya miguu",
    "newborn_cold": "mchanga ni baridi na hapati joto",
    "unable_to_drink_or_feed": "mtoto wangu hawezi kunywa wala kunyonya",
    "vomits_everything": "anatapika kila anachokunywa",
    "bilateral_oedema": "miguu yote miwili imevimba",
    "sudden_pelvic_pain_adolescent": "msichana wangu ana maumivu makali chini ya tumbo ghafla",
    "visible_severe_wasting": "mtoto amekonda sana na mifupa inaonekana",
    "bulging_fontanelle": "utosi umevimba",
    "testicular_pain": "korodani inauma tangu asubuhi",
    "sudden_pallor": "amepauka ghafla",
    "unusual_cry": "analia kwa sauti ya ajabu",
    "limp_with_fever": "anachechemea na ana homa",
    "bleeding_with_fever": "ana homa na anatokwa damu puani",
    "lockjaw_spasms": "hawezi kufungua mdomo na misuli inakaza",
    "heatstroke": "amepigwa na jua kali na amezimia",
    "neonatal_jaundice": "macho yamenjano kwa mchanga wangu",
    "severe_malaria": "ana malaria na amelala sana hajitambui",
    "malaria_area_fever": "ana homa na tunaishi eneo lenye malaria",
    "palmar_pallor": "viganja vyake vimepauka sana",
    "fast_breathing_for_age": "nimehesabu pumzi 64 kwa dakika moja",
    "cholera_rice_water": "kuhara kwake ni kama maji ya mchele",
    "severe_dehydration_signs": "ngozi hairudi nikibana",
    "measles_complication": "ana surua na macho yanatoka usaha",
    "neonatal_tetanus": "mchanga ameacha kunyonya na amekakamaa",
}


#: Lo corriente de un niño, en suajili. Ninguna puede dar alarma.
CORRIENTE = [
    "mtoto wangu ana mafua kidogo",
    "anakohoa kidogo lakini anakula vizuri",
    "meno yanaota na anatoa mate mengi",
    "ni lini naweza kuanza kumpa matunda",
    "ana kidonda cha goti kilichoanza kupona",
    "analia jioni, nadhani ni tumbo la kujaa gesi",
    "mtoto wangu hataki kulala mapema",
    "ni chanjo gani anapewa akiwa na miezi tisa",
    "je nimpe dawa gani ya homa",
    "mtoto wangu amepata chanjo leo na sehemu ya sindano imevimba kidogo",
    "anakojoa vizuri na anakula vizuri",
    "ana upele mdogo baada ya joto",
    "nimempa maji ya mchele kwa kuhara kama nilivyoambiwa",
    "ni kawaida mtoto kupumua pumzi ngapi kwa dakika",
    "alikuwa na malaria mwaka jana na alipona vizuri",
    "nawezaje kuzuia malaria kwa watoto wangu",
    "je surua inaweza kusababisha vidonda mdomoni",
    "viganja vyake ni vichafu kwa kucheza mchangani",
    "anapumua haraka akikimbia lakini inaisha haraka",
    "mtoto wangu amefunga choo siku mbili",
]


def test_every_rule_has_a_swahili_phrase() -> None:
    """Una regla sin frase suajili aquí es una regla que nadie ha comprobado en suajili."""
    import yaml

    reglas = yaml.safe_load((RAIZ / "config" / "red_flags.yaml").read_text(encoding="utf-8"))
    faltan = sorted({r["id"] for r in reglas["rules"]} - set(CASOS))
    assert not faltan, f"reglas sin frase de padre en suajili: {faltan}"


@pytest.mark.parametrize("regla,texto", sorted(CASOS.items()), ids=lambda x: str(x)[:34])
def test_the_rule_fires_in_swahili(triaje: Triage, regla: str, texto: str) -> None:
    ids = [m.id for m in triaje.assess(texto).matched]
    assert regla in ids, f"«{texto}» → {ids or 'nada'}"


@pytest.mark.parametrize("texto", CORRIENTE, ids=lambda t: t[:34])
def test_an_ordinary_swahili_sentence_raises_no_alarm(triaje: Triage, texto: str) -> None:
    r = triaje.assess(texto)
    assert r.level == "routine", f"«{texto}» → {r.level} por {[m.id for m in r.matched]}"


@pytest.mark.parametrize("texto", sorted(CASOS.values())[:20], ids=lambda t: t[:30])
def test_the_detector_knows_it_is_swahili(texto: str) -> None:
    """Si el detector no lo reconoce, el aviso sale en inglés y el padre no lo lee."""
    assert detect_lang(texto) == "sw", f"«{texto}» → {detect_lang(texto)}"


#: La segunda forma de decirlo (L174: una manera no es cobertura).
#:
#: Al medirla saltaron CATORCE huecos de 83, y la causa se repetía: el suajili mete el
#: posesivo entre las dos palabras —«mwili WAKE unatetemeka», «uso WAKE umevimba», «miguu
#: NI baridi»— y cambia el PRINCIPIO del verbo según el tiempo: ame-, aka-, ali-, ka-.
#: Un patrón que sólo conoce una de esas formas no existe para las otras tres.
SEGUNDA: dict[str, str] = {
    "not_responding": "mwanangu hajibu kabisa, nimemwita mara nyingi",
    "seizure": "mwili wake unatetemeka na macho yamekodoka",
    "severe_breathing": "anashindwa kupumua na kifua kinaingia ndani",
    "anaphylaxis": "uso wake umevimba baada ya kula karanga na anashindwa kupumua",
    "choking": "chakula kimemkwama kooni, anasongwa",
    "mottled_skin": "ngozi yake imebadilika rangi, ni ya bluu",
    "head_injury_loss_consciousness": "alianguka akagonga kichwa na akapoteza fahamu",
    "severe_bleeding": "damu inatoka nyingi na haikomi hata nikibana",
    "open_fracture": "mfupa umetoka nje kwenye jeraha",
    "petechiae_fever": "ana madoa mekundu na hayapotei nikibonyeza glasi",
    "infant_fever_under_3_months": "mtoto wa miezi miwili ana homa tangu jana",
    "very_high_fever": "joto limepanda sana, homa kali sana tangu usiku",
    "moderate_breathing": "anapumua haraka na anakoroma kifuani tangu jana",
    "drowsy_irritable": "hana nguvu kabisa na hataki kuamka tangu asubuhi",
    "dehydration": "mdomo umekauka na hakojoi tangu jana",
    "vomiting_headache": "kichwa kinauma mno na anatapika tangu usiku",
    "vomiting_after_head_injury": "baada ya kugonga kichwa ametapika mara mbili",
    "button_battery": "amemeza betri ndogo ya saa ya ukutani",
    "foreign_body_ingestion": "kameza kifungo cha shati",
    "poisoning": "amekunywa kemikali ya kusafishia",
    "severe_abdominal_pain": "maumivu makali ya tumbo hayaishi tangu jana",
    "deformity_fracture": "mguu umepinda baada ya kuanguka kutoka kitandani",
    "newborn_refusing_feeds": "mchanga amekataa kunyonya tangu usiku",
    "burn": "ameungua na maji ya moto mgongoni",
    "bilious_or_bloody_vomit": "ametapika damu asubuhi hii",
    "blood_in_stool": "anaharisha damu tangu jana",
    "abdominal_pain_localised_or_worsening": "maumivu ya tumbo yanazidi tangu jana",
    "eating_disorder_signs": "binti yangu anaogopa kunenepa na amekataa kula kabisa",
    "neuro_deficit": "hawezi kuongea vizuri tangu asubuhi",
    "headache_warning_signs": "maumivu ya kichwa yanamwamsha usiku",
    "suicidal_ideation": "mwanangu hataki kuishi tena",
    "self_harm": "anajidhuru kwa kisu",
    "neck_stiffness": "shingo imekakamaa na hawezi kuinamisha kichwa",
    "meningitis_signs": "hawezi kuangalia mwanga na ana homa",
    "deep_wound": "jeraha la kina limefunguka mguuni",
    "cannot_swallow_drooling": "anadondosha mate na hawezi kumeza chakula",
    "mastoiditis": "sikio limesukumwa mbele na kuna uvimbe nyuma ya sikio",
    "blood_in_urine": "mkojo una damu tangu asubuhi",
    "fluid_from_ear_or_nose": "baada ya kugonga kichwa maji yanatoka puani",
    "cold_extremities_with_fever": "ana homa lakini miguu ni baridi",
    "snakebite": "nyoka amemuuma mguuni shambani",
    "mammal_bite": "paka amemuuma mkononi",
    "stridor": "anapumua kwa sauti ya kukwaruza tangu usiku",
    "intussusception": "kinyesi kama ute na damu na analia kwa mawimbi",
    "projectile_vomiting_infant": "matapishi yanaruka kwa nguvu kila anaponyonya",
    "new_diabetes_signs": "anakojoa sana na amekonda licha ya kula",
    "inhaled_foreign_body": "amekohoa ghafla akicheza na kitu kidogo",
    "asthma_not_responding": "inhaler haisaidii, pumu haijatulia",
    "chemical_in_eye": "petroli imeingia machoni",
    "omphalitis": "kitovu kinatoka usaha na kina harufu",
    "carbon_monoxide": "moshi wa mkaa umejaa na wote tunaumwa na kichwa",
    "near_drowning": "amezama majini kwenye ndoo",
    "electric_shock": "umeme umemshika akiwa anacheza",
    "foreign_body_nose_or_ear": "punje imeingia sikioni",
    "spinal_injury": "ameanguka kutoka mtini na hasogezi miguu",
    "blunt_abdominal_trauma": "amegongwa tumbo na sasa amepauka",
    "smoke_inhalation": "alikuwa kwenye moto na anakohoa sana",
    "bruising_and_pallor": "ana michubuko pasipo kugongwa na amechoka sana",
    "hypoglycaemia": "sukari imeshuka, ana kisukari na anatetemeka",
    "sickle_cell_crisis": "anaumwa sana na ana selimundu",
    "newborn_cold": "mwili wa mchanga ni baridi na hapati joto",
    "unable_to_drink_or_feed": "hanywi chochote tangu jana",
    "vomits_everything": "hakibaki chochote tumboni, anatapika kila kitu",
    "bilateral_oedema": "amevimba miguu yote miwili tangu jana",
    "sudden_pelvic_pain_adolescent": "msichana wa miaka kumi na mitatu ana maumivu makali chini ya tumbo ghafla",
    "visible_severe_wasting": "mifupa inaonekana kwa kukonda",
    "bulging_fontanelle": "sehemu laini ya kichwa imevimba",
    "testicular_pain": "pumbu linauma tangu usiku",
    "sudden_pallor": "amebadilika rangi ghafla",
    "unusual_cry": "analia kwa sauti ya juu isiyo ya kawaida",
    "limp_with_fever": "ana homa na hawezi kukanyaga mguu",
    "bleeding_with_fever": "ana homa na anatokwa damu fizi",
    "lockjaw_spasms": "taya limekaza na misuli inakaza",
    "heatstroke": "jua kali limemzidi na amezimia",
    "neonatal_jaundice": "mchanga ana njano machoni",
    "severe_malaria": "ana malaria na hajitambui",
    "malaria_area_fever": "tunaishi sehemu yenye malaria na ana homa",
    "palmar_pallor": "kiganja chake kimepauka sana",
    "fast_breathing_for_age": "nimehesabu pumzi 66 kwa dakika",
    "cholera_rice_water": "kinyesi chake ni maji ya mchele",
    "severe_dehydration_signs": "macho yamebonyea na hawezi kunywa",
    "measles_complication": "ana surua na mdomoni kuna vidonda",
    "neonatal_tetanus": "mchanga hanyonyi na mwili mgumu",
}


def test_every_rule_has_a_second_swahili_phrase() -> None:
    import yaml

    reglas = yaml.safe_load((RAIZ / "config" / "red_flags.yaml").read_text(encoding="utf-8"))
    faltan = sorted({r["id"] for r in reglas["rules"]} - set(SEGUNDA))
    assert not faltan, f"reglas sin segunda forma en suajili: {faltan}"


@pytest.mark.parametrize("regla,texto", sorted(SEGUNDA.items()), ids=lambda x: str(x)[:34])
def test_the_rule_also_fires_said_another_way(triaje: Triage, regla: str, texto: str) -> None:
    ids = [m.id for m in triaje.assess(texto).matched]
    assert regla in ids, f"«{texto}» → {ids or 'nada'}"
