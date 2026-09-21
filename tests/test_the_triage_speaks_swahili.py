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
    "drowsy_after_head_injury": "ameanguka kutoka kitandani na sasa anasinzia sana",
    "eye_foreign_body_or_injury": "kibanzi kimeingia jichoni mwake",
    "fall_stairs_or_inconsolable": "ameanguka kutoka ngazi",
    "spreading_skin_infection": "mtoto ana mstari mwekundu unapanda juu ya mkono wake",
    "white_pupil": "mtoto wangu ana mboni nyeupe kwenye picha",
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
    "drowsy_after_head_injury": "aligonga kichwa na sasa haamki vizuri",
    "eye_foreign_body_or_injury": "amepigwa jichoni na mpira",
    "fall_stairs_or_inconsolable": "alianguka na hanyamazi kulia",
    "spreading_skin_infection": "mtoto wangu ameumwa na mdudu na kidonda kinaenea",
    "white_pupil": "jicho la mtoto lina mboni inayoonekana nyeupe",
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


@pytest.mark.parametrize(
    "texto", sorted({*CASOS.values(), *SEGUNDA.values(), *CORRIENTE}), ids=lambda t: t[:30]
)
def test_the_detector_knows_it_is_swahili(texto: str) -> None:
    """Si el detector no lo reconoce, el aviso sale en inglés y el padre no lo lee.

    Se miran las 186, no una muestra: la primera versión miraba veinte y pasaba, y al medirlas
    todas **21 no se reconocían**. Una de ellas, «paka amemuuma mkononi» —le ha mordido el
    gato—, saltaba la alarma correcta y la escribía en inglés, que es la mitad del trabajo.
    """
    assert detect_lang(texto) == "sw", f"«{texto}» → {detect_lang(texto)}"


def test_swahili_does_not_steal_the_other_languages() -> None:
    """Y el otro sentido, que es el que se olvida (L175).

    El suajili se reconoce por su morfología —«ame-» delante del verbo, «-ni» detrás del
    sustantivo— y esas piezas son cortas. « ame» a secas se llevaba «amendoins», que es como un
    padre portugués cuenta un atragantamiento con cacahuetes; por eso la marca lleva ahora la
    consonante siguiente, que en suajili nunca es una ene.
    """
    from test_every_rule_in_every_language import CASOS as OTRAS
    from test_every_rule_in_every_language import CORTO
    from test_every_rule_in_every_language import SEGUNDA as OTRAS_2

    robadas = [
        (lg, f)
        for d in (OTRAS, OTRAS_2, CORTO)
        for frases in d.values()
        for lg, f in frases.items()
        if detect_lang(f) == "sw"
    ]
    assert not robadas, f"el suajili se lleva frases de otras lenguas: {robadas[:5]}"


def test_every_rule_has_a_second_swahili_phrase() -> None:
    import yaml

    reglas = yaml.safe_load((RAIZ / "config" / "red_flags.yaml").read_text(encoding="utf-8"))
    faltan = sorted({r["id"] for r in reglas["rules"]} - set(SEGUNDA))
    assert not faltan, f"reglas sin segunda forma en suajili: {faltan}"


@pytest.mark.parametrize("regla,texto", sorted(SEGUNDA.items()), ids=lambda x: str(x)[:34])
def test_the_rule_also_fires_said_another_way(triaje: Triage, regla: str, texto: str) -> None:
    ids = [m.id for m in triaje.assess(texto).matched]
    assert regla in ids, f"«{texto}» → {ids or 'nada'}"


#: Lo que NO está pasando, en suajili (L176: la señal no basta, hay que leer el marco).
#:
#: El suajili construye la negación, el pasado y la condición DENTRO del verbo, que es justo
#: lo que un guardián escrito para el castellano no puede ver: «ana degedege» es tiene
#: convulsiones, «HAna degedege» es no las tiene, «ALIkuwa na degedege» es las tuvo y
#: «AKIpata degedege» es si le dan. No hay un «no» ni un «si» sueltos que buscar.
#:
#: Medido al escribirlas: **7 de 26 daban alarma**, y cinco eran el aviso rojo de convulsión.
#: Un padre que pregunta «degedege la homa ni nini» —qué es una convulsión febril— recibía
#: «llama ya».
GUARDIANES: list[tuple[str, str]] = [
    ("mtoto wangu hana homa", "negación: no tiene fiebre"),
    ("hana degedege, ni usingizi tu", "negación: no son convulsiones"),
    ("hakuna damu kwenye kinyesi", "negación: no hay sangre"),
    ("hajatapika tangu asubuhi", "negación: no ha vomitado"),
    ("ngozi haina madoa", "negación: la piel no tiene manchas"),
    ("hapumui kwa shida, anapumua vizuri", "negación con corrección"),
    ("alikuwa na degedege mwaka jana na hajarudia", "pasado: hace un año"),
    ("alipata malaria mwaka jana na alipona", "pasado: se curó"),
    ("aliumwa na mbwa miaka miwili iliyopita", "pasado: hace dos años"),
    ("alikuwa amelazwa hospitali mwaka jana", "pasado: ingresó hace un año"),
    ("nifanye nini akipata degedege?", "condicional: si le dan convulsiones"),
    ("akianza kutapika nifanye nini", "condicional: si empieza a vomitar"),
    ("kama atapata homa kali nimpeleke wapi", "condicional: si le sube la fiebre"),
    ("nikimwona amepauka nifanye nini", "condicional: si lo veo pálido"),
    ("nawezaje kuzuia malaria kwa watoto", "prevención: cómo evitar"),
    ("ninawezaje kuzuia degedege la homa", "prevención: convulsión febril"),
    ("nifanye nini kuzuia kuhara", "prevención: evitar la diarrea"),
    ("jinsi ya kuzuia kuungua jikoni", "prevención: quemaduras"),
    ("dalili za homa ya uti wa mgongo ni zipi", "información: cuáles son los signos"),
    ("degedege la homa ni nini", "información: qué es"),
    ("nitajuaje kama ana upungufu wa maji", "información: cómo saber"),
    ("ni dalili zipi za hatari kwa mtoto mchanga", "información: signos de peligro"),
    ("nimeambiwa kwamba degedege la homa si hatari", "referido: me han dicho"),
    ("nimesoma kwamba kuhara kunaweza kusababisha upungufu wa maji", "referido: he leído"),
    ("je chanjo ya surua inaweza kusababisha homa", "pregunta causal: la vacuna"),
    ("je malaria inaweza kusababisha degedege", "pregunta causal: la enfermedad"),
]


@pytest.mark.parametrize("texto,marco", GUARDIANES, ids=lambda x: str(x)[:34])
def test_what_is_not_happening_raises_no_alarm_in_swahili(
    triaje: Triage, texto: str, marco: str
) -> None:
    r = triaje.assess(texto)
    assert r.level == "routine", f"[{marco}] «{texto}» → {r.level} por {[m.id for m in r.matched]}"


def test_the_swahili_past_prefix_is_not_a_remote_past(triaje: Triage) -> None:
    """La corrección que costó dos emergencias silenciadas.

    La primera versión del guardián del pasado metió el prefijo suajili «ali-» por analogía con
    el «hace dos años» castellano, y está mal: **«ali-» no marca distancia**, es el pasado de
    cualquier cosa que ya ocurrió, incluido lo de hace cinco minutos. Con él dentro, estas dos
    frases dejaron de dar alarma. Cuando falla un guardián, el fallo es un silencio.
    """
    for texto, regla in (
        ("alianguka akagonga kichwa na akapoteza fahamu", "head_injury_loss_consciousness"),
        ("alikuwa kwenye moto na anakohoa sana", "smoke_inhalation"),
    ):
        ids = [m.id for m in triaje.assess(texto).matched]
        assert regla in ids, (
            f"«{texto}» → {ids or 'nada'}: el pasado narrativo no es un pasado remoto"
        )


#: 19-sep-2026, encontrado preguntando a lo desplegado el día de MetaDAO. «Mtoto wangu wa miezi
#: 6 midomo yake ni ya bluu na hajibu» —mi bebé de 6 meses tiene los labios azules y no
#: responde— volvió RUTINA y sin ningún aviso. Dos huecos, los dos del día que entró el suajili:
#:
#:   · **la cianosis no existía en suajili**. Ni una sola de las formas de decir «se ha puesto
#:     azul» disparaba nada, teniendo `severe_breathing` cuatro patrones suajilis de respiración;
#:   · «hajibu» a secas tampoco. El patrón pedía un acompañante —«hajibu kabisa», «hajibu
#:     nikimwita»— y un padre asustado escribe la palabra sola.
#:
#: Es exactamente la avería de L172 otra vez: una lengua entra con sus 83 reglas traducidas y la
#: red le queda más estrecha que a las de al lado, porque se traduce lo que uno escribió y no lo
#: que se dice.
AZUL_Y_SIN_RESPUESTA: list[tuple[str, str]] = [
    ("severe_breathing", "mtoto wangu midomo yake ni ya bluu"),
    ("severe_breathing", "midomo yake imekuwa bluu"),
    ("severe_breathing", "ngozi yake imekuwa ya bluu"),
    ("severe_breathing", "midomo yake ni ya samawati"),
    ("severe_breathing", "uso wake umekuwa bluu"),
    ("not_responding", "mtoto wangu hajibu"),
    ("not_responding", "mtoto wangu wa miezi 6 midomo yake ni ya bluu na hajibu"),
]


@pytest.mark.parametrize(("regla", "texto"), AZUL_Y_SIN_RESPUESTA)
def test_blue_and_unresponsive_fire_in_swahili(triaje: Triage, regla: str, texto: str) -> None:
    r = triaje.assess(texto)
    assert r.level == "emergency", f"«{texto}» → {r.level}"
    assert regla in [m.id for m in r.matched], f"«{texto}» → {[m.id for m in r.matched]}"


#: Y lo que no puede saltar por haber ensanchado lo de arriba: el azul es un color y también es
#: la ropa, y «hajibu» es lo que hace un adolescente con el móvil.
AZUL_CORRIENTE = [
    "amevaa nguo ya bluu leo",
    "nimemnunulia mpira wa bluu",
    "hajibu simu yangu",
    "hajibu maswali ya shule",
]


@pytest.mark.parametrize("texto", AZUL_CORRIENTE)
def test_blue_clothes_and_an_unanswered_phone_raise_no_alarm(triaje: Triage, texto: str) -> None:
    r = triaje.assess(texto)
    assert r.level == "routine", f"«{texto}» → {r.level} por {[m.id for m in r.matched]}"
