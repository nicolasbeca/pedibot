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
