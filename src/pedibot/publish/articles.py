"""Generate a grounded article for a topic from the index, verify citations, write Markdown.

Output: web/content/<lang>/<slug>.md with YAML frontmatter (Astro content collection later) and
publish/queue/x/<slug>.txt with a hand-postable social text (no X API — operator decision).
"""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path

from pedibot.bot.answer import foreign_service_problem, verify
from pedibot.bot.llm import LLMProvider, LLMResult
from pedibot.bot.retrieval import detect_lang
from pedibot.index.store import Hit, Index
from pedibot.ingest.pipeline import slug as make_slug
from pedibot.lang_markers import foreign_markers

PROMPTS_DIR = Path(__file__).parent / "prompts"
_CIT = re.compile(r"\[(\d{1,2})\]")

# Topic → (leaflet doc_ids to draw from, search query). Curated so every article is anchored on
# parent-facing leaflets first; clinical references only add depth.
TOPIC_PLAN: dict[str, dict[str, object]] = {
    "fiebre": {
        "docs": ["seup_fiebre", "seup_acudir_urgencias"],
        "query": "fiebre niño qué hacer cuándo consultar fever child what to do when to see a doctor",
    },
    "laringitis": {
        "docs": ["seup_laringitis"],
        "query": "laringitis crup tos perruna croup barking cough child",
    },
    "bronquiolitis": {
        "docs": ["seup_bronquiolitis"],
        "query": "bronquiolitis lactante dificultad respiratoria bronchiolitis baby breathing difficulty",
    },
    "gastroenteritis": {
        "docs": ["seup_gastroenteritis", "seup_vomitos"],
        "query": "gastroenteritis diarrea vómitos rehidratación",
    },
    "vomitos": {
        "docs": ["seup_vomitos"],
        "query": "vómitos niño qué hacer vomiting child what to do being sick",
    },
    "otitis": {"docs": ["seup_otitis"], "query": "otitis media dolor de oído"},
    "catarro": {
        "docs": ["seup_catarro"],
        "query": "catarro vías altas mocos tos common cold child runny nose cough",
    },
    "traumatismo_craneal": {
        "docs": ["seup_tce"],
        "query": "traumatismo craneal golpe cabeza vigilar head injury concussion child what to watch for",
    },
    "convulsion_febril": {
        "docs": ["seup_convulsion_febril"],
        "query": "convulsión febril qué hacer",
    },
    "intoxicaciones": {
        "docs": ["seup_intoxicaciones", "seup_toxicos_8_no"],
        "query": "intoxicación ingesta tóxico qué no hacer poisoning child swallowed what to do",
    },
    "anafilaxia": {
        "docs": ["seup_anafilaxia"],
        "query": "anafilaxia reacción alérgica grave adrenalina anaphylaxis severe allergic reaction adrenaline",
    },
    "urticaria": {"docs": ["seup_urticaria"], "query": "urticaria ronchas habones"},
    "dolor_abdominal": {
        "docs": ["seup_dolor_abdominal"],
        "query": "dolor abdominal barriga cuándo consultar stomach ache abdominal pain child when to see a doctor",
    },
    "estrenimiento": {
        "docs": ["seup_estrenimiento"],
        "query": "estreñimiento niño constipation child hard stools",
    },
    "colico_lactante": {
        "docs": ["seup_colico"],
        "query": "cólico del lactante llanto colic crying baby soothing",
    },
    "golpe_calor": {
        "docs": ["seup_golpe_calor"],
        "query": "golpe de calor niño prevención heat exhaustion heatstroke child prevention",
    },
    "cefalea": {"docs": ["seup_cefalea"], "query": "cefalea dolor de cabeza niño headache child"},
    "sincope": {"docs": ["seup_sincope"], "query": "síncope desmayo fainting child"},
    "espasmos_sollozo": {
        "docs": ["seup_espasmos_sollozo"],
        "query": "espasmos del sollozo breath-holding child crying",
    },
    "crisis_asma": {
        "docs": ["seup_crisis_asma"],
        "query": "crisis asmática inhalador asthma attack child inhaler",
    },
    "neumonia": {
        "docs": ["seup_neumonia"],
        "query": "neumonía niño síntomas pneumonia child symptoms",
    },
    "alimentacion_complementaria": {
        "docs": ["aep_alimentacion_complementaria", "who_complementary_feeding"],
        "query": "alimentación complementaria cuándo empezar first solid foods weaning when to start baby",
    },
    "vacunas": {
        "docs": ["msan_calendario_vacunacion_2025"],
        "query": "calendario vacunación infantil vaccination schedule children immunisation",
    },
    "recien_nacido": {
        "docs": ["aep_cuidados_recien_nacido", "andalucia_cuidame_comienzo_vida"],
        "query": "cuidados recién nacido cordón baño caring for a newborn baby umbilical cord bathing",
    },
    "sueno_pantallas": {
        "docs": ["who_physical_activity_under5"],
        "query": "sleep screen time physical activity under 5",
    },
    "ansiedad": {
        "docs": ["seup_ansiedad"],
        "query": "ansiedad niños adolescentes anxiety children adolescents",
    },
    "autolesion": {
        "docs": ["seup_autolesion", "seup_conducta_suicida"],
        "query": "conducta autolesiva adolescente self-harm adolescent",
    },
    "tca": {
        "docs": ["seup_tca"],
        "query": "trastorno conducta alimentaria adolescente eating disorder adolescent",
    },
    # ---- added 25-ago with the international public sources ----
    "chickenpox": {
        "docs": ["nhs_en_chickenpox", "mlp_en_chickenpox", "cdc_en_chickenpox_about_index"],
        "query": "chickenpox varicella symptoms itching when to see doctor",
    },
    "hand_foot_mouth": {
        "docs": ["nhs_en_hand_foot_mouth_disease", "cdc_en_hand_foot_mouth_about_index"],
        "query": "hand foot and mouth disease children",
    },
    "scarlet_fever": {
        "docs": ["nhs_en_scarlet_fever"],
        "query": "scarlet fever rash strawberry tongue",
    },
    "meningitis_signs": {
        "docs": ["nhs_en_meningitis", "mlp_en_meningitis", "nhs_en_sepsis"],
        "query": "meningitis sepsis signs rash glass test children",
    },
    "teething": {"docs": ["nhs_en_baby_teething_symptoms"], "query": "teething symptoms baby"},
    "reflux": {"docs": ["nhs_en_reflux_in_babies"], "query": "reflux babies bringing up milk"},
    "constipation": {
        "docs": ["nhs_en_constipation", "mlp_en_constipation", "seup_estrenimiento"],
        "query": "constipation children hard stools",
    },
    "ear_infection": {
        "docs": ["nhs_en_ear_infections", "mlp_en_earinfections", "cdc_en_ear_infection_about"],
        "query": "ear infection children earache antibiotics",
    },
    "sore_throat": {
        "docs": ["nhs_en_sore_throat", "nhs_en_tonsillitis", "mlp_en_sorethroat"],
        "query": "sore throat tonsillitis children",
    },
    "common_cold": {
        "docs": ["mlp_en_commoncold", "seup_catarro"],
        "query": "common cold children runny nose antibiotics",
    },
    "flu": {
        "docs": ["nhs_en_flu", "cdc_en_children"],
        "query": "flu influenza children symptoms high risk",
    },
    "rsv": {
        "docs": [
            "nhs_en_respiratory_syncytial_virus_rsv",
            "cdc_en_rsv_infants_young_children_index",
            "cdc_en_rsv_about_index",
        ],
        "query": "RSV infants bronchiolitis symptoms",
    },
    "whooping_cough": {
        "docs": ["nhs_en_whooping_cough", "mlp_en_whoopingcough", "cdc_en_pertussis_about_index"],
        "query": "whooping cough pertussis babies vaccine",
    },
    "measles": {
        "docs": ["nhs_en_measles", "mlp_en_measles", "who_en_measles"],
        "query": "measles symptoms rash vaccine",
    },
    "head_injury_en": {
        "docs": [
            "nhs_en_head_injury_and_concussion",
            "mlp_en_headinjuries",
            "cdc_en_heads_up_signs_symptoms_index",
        ],
        "query": "head injury concussion children signs",
    },
    "febrile_seizure": {
        "docs": ["nhs_en_febrile_seizures", "seup_convulsion_febril"],
        "query": "febrile seizure what to do",
    },
    "diarrhoea_vomiting": {
        "docs": ["nhs_en_diarrhoea_and_vomiting", "mlp_en_gastroenteritis", "nhs_en_dehydration"],
        "query": "diarrhoea vomiting children fluids dehydration",
    },
    "burns": {
        "docs": ["nhs_en_burns_and_scalds", "mlp_en_burns"],
        "query": "burns scalds first aid children cool water",
    },
    "poisoning_en": {
        "docs": ["nhs_en_poisoning", "mlp_en_poisoning"],
        "query": "poisoning children swallowed what to do",
    },
    "choking": {
        "docs": ["mlp_en_choking", "mlp_es_choking", "andalucia_cuidame_guia"],
        "query": "choking baby child first aid",
    },
    "anaphylaxis_en": {
        "docs": ["nhs_en_anaphylaxis", "nhs_en_food_allergy", "seup_anafilaxia"],
        "query": "anaphylaxis food allergy adrenaline auto-injector",
    },
    "hives": {"docs": ["nhs_en_hives", "seup_urticaria"], "query": "hives urticaria children"},
    "rashes": {
        "docs": ["nhs_en_rashes_babies_and_children", "mlp_en_rashes"],
        "query": "rashes babies children spots",
    },
    "heat": {
        "docs": ["nhs_en_heat_exhaustion_heatstroke", "mlp_en_heatillness", "seup_golpe_calor"],
        "query": "heat exhaustion heatstroke children",
    },
    "sunburn": {"docs": ["nhs_en_sunburn"], "query": "sunburn children sun protection"},
    "insect_bites": {
        "docs": ["nhs_en_insect_bites_and_stings", "mlp_en_insectbitesandstings"],
        "query": "insect bites stings children",
    },
    "head_lice": {
        "docs": ["nhs_en_head_lice_and_nits", "cdc_en_lice_about_index"],
        "query": "head lice nits treatment",
    },
    "threadworms": {
        "docs": ["nhs_en_threadworms", "mlp_en_pinworms"],
        "query": "threadworms pinworms children",
    },
    "uti": {
        "docs": ["nhs_en_urinary_tract_infections_utis", "mlp_en_urinarytractinfections"],
        "query": "urinary tract infection children symptoms",
    },
    "conjunctivitis": {
        "docs": ["nhs_en_conjunctivitis", "mlp_en_pinkeye"],
        "query": "conjunctivitis pink eye children",
    },
    "nosebleed": {"docs": ["nhs_en_nosebleed"], "query": "nosebleed children how to stop"},
    "headache_en": {
        "docs": ["nhs_en_headaches_in_children", "mlp_en_headache", "seup_cefalea"],
        "query": "headaches children when to worry",
    },
    "bedwetting": {
        "docs": ["nhs_en_bedwetting", "mlp_en_bedwetting"],
        "query": "bedwetting children",
    },
    "growing_pains": {"docs": ["nhs_en_growing_pains"], "query": "growing pains legs night"},
    "cradle_cap": {"docs": ["nhs_en_cradle_cap"], "query": "cradle cap baby scalp"},
    "newborn_care_en": {
        "docs": ["nhs_en_caring_for_a_newborn", "mlp_en_infantandnewborncare"],
        "query": "caring for a newborn first weeks",
    },
    "weaning_en": {
        "docs": [
            "nhs_en_babys_first_solid_foods",
            "who_en_infant_and_young_child_feeding",
            "cdc_en_infant_toddler_nutrition_index",
        ],
        "query": "baby first solid foods weaning 6 months",
    },
    "breastfeeding": {
        "docs": ["mlp_en_breastfeeding", "who_en_infant_and_young_child_feeding"],
        "query": "breastfeeding how often benefits",
    },
    "vaccines_en": {
        "docs": [
            "nhs_en_nhs_vaccinations_and_when_to_have_them",
            "cdc_en_child_easyread",
            "mlp_en_childhoodvaccines",
        ],
        "query": "childhood vaccination schedule when",
    },
    # 13-sep-2026: qué es un percentil y qué tabla usa la cartilla. Las preguntas de la OMS sobre sus
    # patrones de crecimiento y la página del NHS sobre los centiles del Red Book.
    "percentiles_crecimiento": {
        "docs": [
            "who_en_child_growth_standards",
            "nhs_en_baby_height_and_weight",
            "who_es_child_growth_standards",
        ],
        "query": "percentil curva de crecimiento peso talla bebé qué significa percentile growth chart weight height baby",
    },
    "milestones": {
        "docs": ["cdc_en_act_early_milestones_index", "mlp_en_childdevelopment"],
        "query": "developmental milestones baby toddler",
    },
    "screen_sleep": {
        "docs": [
            "who_physical_activity_under5",
            "cdc_en_child_development_positive_parenting_tips_index",
        ],
        "query": "screen time sleep physical activity under 5",
    },
    "asthma_en": {
        "docs": ["nhs_en_asthma", "mlp_en_asthmainchildren", "seup_crisis_asma"],
        "query": "asthma children inhaler attack",
    },
    "paracetamol_en": {
        "docs": ["nhs_en_paracetamol_for_children"],
        "query": "paracetamol for children how to give",
    },
    "ibuprofen_en": {
        "docs": ["nhs_en_ibuprofen_for_children"],
        "query": "ibuprofen for children how to give",
    },
    # ---- comparison guides (idea 5): several organisations on one practical question ----
    "compare_fever_threshold": {
        "compare": True,
        "docs": ["seup_fiebre", "nhs_en_fever_in_children", "mlp_en_fever"],
        "query": "what is a fever temperature threshold 38 when to treat",
    },
    "compare_start_solids": {
        "compare": True,
        "docs": [
            "aep_alimentacion_complementaria",
            "who_en_infant_and_young_child_feeding",
            "nhs_en_babys_first_solid_foods",
            "cdc_en_infant_toddler_nutrition_index",
        ],
        "query": "when to start solid foods 6 months signs of readiness",
    },
    "compare_cough_medicines": {
        "compare": True,
        "docs": ["seup_catarro", "mlp_en_commoncold", "nhs_en_croup"],
        "query": "cough medicines children not recommended honey",
    },
    "compare_fever_medicine": {
        "compare": True,
        "docs": ["seup_fiebre", "nhs_en_paracetamol_for_children", "nhs_en_ibuprofen_for_children"],
        "query": "paracetamol ibuprofen fever when to give alternate",
    },
    "compare_head_injury_watch": {
        "compare": True,
        "docs": [
            "seup_tce",
            "nhs_en_head_injury_and_concussion",
            "cdc_en_heads_up_signs_symptoms_index",
        ],
        "query": "head injury what to watch for 48 hours",
    },
    # ── Lote del 11-sep-2026: los temas que el corpus ya sostenía y el plan no tenía ──────────
    # El plan estaba hecho desde la pediatría española y británica: fiebre, otitis, dentición,
    # piojos, pantallas. Faltaba entero lo que mata y preocupa donde el proyecto quiere llegar,
    # y que las fichas de la OMS llevan indexadas en cinco lenguas desde el 3 de septiembre.
    "desnutricion": {
        # no hay ficha de la OMS en castellano para esto; la recuperación cruza igual
        "docs": [
            "who_en_malnutrition",
            "who_fr_malnutrition",
            "who_ar_malnutrition",
            "who_ru_malnutrition",
        ],
        "query": "desnutrición infantil signos peso talla cuándo consultar malnutrition child",
    },
    "ahogamiento": {
        "docs": ["cdc_en_drowning_prevention_index", "who_ar_drowning", "who_ru_drowning"],
        "query": "prevenir ahogamiento niños agua piscina supervisión drowning prevention",
    },
    "tuberculosis": {
        "docs": ["who_ar_tuberculosis", "who_ru_tuberculosis"],
        "query": "tuberculosis en niños síntomas tos prolongada contacto tuberculosis children symptoms cough",
    },
    "malaria": {
        "docs": ["who_en_malaria"],
        "query": "malaria niño fiebre zona endémica mosquitera urgente malaria child fever",
    },
    "hepatitis_b": {
        "docs": ["who_ar_hepatitis_b", "who_ru_hepatitis_b"],
        "query": "hepatitis B niños transmisión vacuna hepatitis B children vaccine",
    },
    "poliomielitis": {
        # 20-sep-2026: sin la ficha inglesa, la guía inglesa salía citando sólo al RKI
        # alemán, que su lector no puede abrir. La lista de anclas es la que manda aquí:
        # tener el documento en el índice no basta si el plan del tema no lo nombra.
        "docs": [
            "who_en_poliomyelitis",
            "rki_de_ratgeber_poliomyelitis",
            "who_ar_poliomyelitis",
            "who_ru_poliomyelitis",
        ],
        "query": "poliomielitis vacuna parálisis niños polio vaccine paralysis",
    },
    "vacunas_atrasadas": {
        "docs": [
            "who_en_immunization_coverage",
            "who_es_immunization_coverage",
            "who_fr_immunization_coverage",
            "who_ar_immunization_coverage",
            "who_ru_immunization_coverage",
        ],
        "query": "vacunas atrasadas ponerse al día calendario incompleto catch up immunization",
    },
    "hepatitis_a": {
        "docs": ["rki_de_ratgeber_hepatitisa"],
        "query": "hepatitis A niños agua alimentos higiene vacuna hepatitis A children water food hygiene vaccine",
    },
    "senales_autismo": {
        # el informe de la OMS es `citar_solo`: el bot puede citarlo, un artículo no puede
        # reproducirlo. MedlinePlus es dominio público (lo cazó test_publish_licences)
        "docs": ["mlp_en_autismspectrumdisorder"],
        "query": "señales de autismo en niños desarrollo comunicación autism signs children",
    },
    "teen_mental_health": {
        "docs": ["mlp_en_teenmentalhealth", "who_en_adolescent_mental_health"],
        "query": "teen mental health anxiety depression signs",
    },
    # ── 11-sep-2026 ──────────────────────────────────────────────────────────────────────
    # El corpus tenía 24 asuntos de la OMS en cinco lenguas cada uno y NINGUNA guía los
    # escribía: documentos indexados que no lee nadie. Éstos son los que pesan en la India y
    # en los países árabes —la rabia de una mordedura de perro y la mordedura de serpiente
    # son urgencias de horas; el dengue, la tifoidea, la sarna y las lombrices, pediatría
    # diaria; y la anemia afecta a más de la mitad de los niños indios menores de cinco años.
    # Dieciséis temas × ocho lenguas = 128 guías, dos meses de cola para los timers.
    "dengue": {
        "docs": [
            "who_en_dengue_and_severe_dengue",
            "who_ar_dengue_and_severe_dengue",
            "who_es_dengue_and_severe_dengue",
        ],
        "query": "dengue niño fiebre signos de alarma sangrado dolor abdominal dengue child warning signs",
    },
    "mordedura_perro_rabia": {
        "docs": ["who_en_rabies", "who_ar_rabies", "who_es_rabies"],
        "query": "mordedura de perro niño rabia lavar la herida profilaxis dog bite child rabies wound washing",
    },
    "mordedura_serpiente": {
        "docs": [
            "who_en_snakebite_envenoming",
            "who_ar_snakebite_envenoming",
            "who_es_snakebite_envenoming",
        ],
        "query": "mordedura de serpiente niño qué hacer no torniquete snake bite child what to do",
    },
    "tetanos": {
        "docs": ["who_en_tetanus", "who_ar_tetanus", "who_es_tetanus"],
        "query": "tétanos niño herida sucia vacuna espasmos tetanus child wound vaccine",
    },
    "tifoidea": {
        "docs": ["who_en_typhoid", "who_ar_typhoid", "who_es_typhoid"],
        "query": "fiebre tifoidea niño agua contaminada vacuna typhoid fever child water vaccine",
    },
    "sarna": {
        "docs": ["who_en_scabies", "who_ar_scabies", "who_es_scabies"],
        "query": "sarna niño picor por la noche tratamiento familia scabies child itching treatment",
    },
    "lombrices_intestinales": {
        "docs": [
            "who_en_soil_transmitted_helminth_infections",
            "who_ar_soil_transmitted_helminth_infections",
            "who_es_soil_transmitted_helminth_infections",
        ],
        "query": "lombrices intestinales niño desparasitación higiene deworming child intestinal worms",
    },
    # ── África, fase 4 (18-sep-2026) ────────────────────────────────────────────────────────
    # El plan tenía ya malaria, sarampión, neumonía, desnutrición, tétanos y anemia, que son seis
    # de las siete cosas que más matan niños en el continente. Faltaba el cólera —que hasta hoy
    # no tenía ni una ficha en el corpus— y faltaba lo que un padre necesita saber ANTES de que
    # llegue a urgencias: cómo se prepara el suero oral y cómo se cuentan las respiraciones.
    #
    # Las tres se apoyan en documentos que ya están indexados y en ninguna receta nuestra.
    "colera": {
        "docs": ["who_en_cholera", "who_es_cholera", "who_fr_cholera", "who_ar_cholera"],
        "query": (
            "cólera niño diarrea como agua de arroz deshidratación rehidratación cholera child "
            "watery diarrhoea rice water dehydration"
        ),
    },
    "suero_oral": {
        "docs": [
            "who_en_diarrhoeal_disease",
            "who_es_diarrhoeal_disease",
            "nhs_en_diarrhoea_and_vomiting",
        ],
        "query": (
            "suero oral sales de rehidratación cómo se prepara el sobre cuánto dar diarrea "
            "oral rehydration solution ORS how to prepare how much to give"
        ),
    },
    "respiracion_rapida": {
        "docs": ["nhm_in_imnci_chart_booklet", "seup_neumonia", "who_en_pneumonia"],
        "query": (
            "contar respiraciones por minuto niño respiración rápida tiraje neumonía "
            "count breaths per minute fast breathing chest indrawing pneumonia child"
        ),
    },
    "anemia": {
        "docs": ["who_en_anaemia", "who_ar_anaemia", "who_es_anaemia"],
        "query": "anemia niño hierro cansancio palidez anaemia child iron deficiency",
    },
    "diarrea_sro_zinc": {
        "docs": [
            "who_en_diarrhoeal_disease",
            "who_ar_diarrhoeal_disease",
            "who_es_diarrhoeal_disease",
        ],
        "query": "diarrea niño sales de rehidratación oral zinc deshidratación ORS zinc child diarrhoea",
    },
    "agua_segura_bebe": {
        "docs": ["who_en_drinking_water", "who_ar_drinking_water", "who_es_drinking_water"],
        "query": "agua potable segura para el bebé hervir biberón safe drinking water baby boiling",
    },
    "seguridad_alimentaria": {
        "docs": ["who_en_food_safety", "who_ar_food_safety", "who_es_food_safety"],
        "query": "seguridad alimentaria niño preparar la comida higiene food safety child preparing food",
    },
    "difteria": {
        "docs": ["who_en_diphtheria", "who_ar_diphtheria", "who_es_diphtheria"],
        "query": "difteria niño garganta membrana vacuna diphtheria child throat vaccine",
    },
    "sepsis_signos": {
        "docs": ["who_en_sepsis", "who_ar_sepsis", "nhs_en_sepsis"],
        "query": "sepsis niño signos de alarma actuar rápido sepsis child warning signs",
    },
    "prematuro_cuidados": {
        "docs": ["who_en_preterm_birth", "who_ar_preterm_birth", "who_es_preterm_birth"],
        "query": "bebé prematuro cuidados piel con piel método canguro preterm baby kangaroo mother care",
    },
    "epilepsia_infantil": {
        "docs": ["who_en_epilepsy", "who_ar_epilepsy", "who_es_epilepsy"],
        "query": "epilepsia niño crisis qué hacer tratamiento epilepsy child seizure what to do",
    },
    "salud_bucodental": {
        "docs": ["who_en_oral_health", "who_ar_oral_health", "who_es_oral_health"],
        "query": "salud bucodental niño caries flúor cepillado oral health child caries fluoride",
    },
}


@dataclass
class Article:
    topic: str
    lang: str
    title: str
    summary: str
    body_md: str
    sources: list[str]
    chunk_ids: list[str]
    llm: LLMResult
    verification: str

    @property
    def slug(self) -> str:
        return make_slug(self.title, max_len=70)

    def frontmatter(self) -> str:
        today = dt.date.today().isoformat()
        srcs = "\n".join(f"  - {json.dumps(s, ensure_ascii=False)}" for s in self.sources)
        return (
            "---\n"
            f"title: {json.dumps(self.title, ensure_ascii=False)}\n"
            f"description: {json.dumps(self.summary, ensure_ascii=False)}\n"
            f"lang: {self.lang}\n"
            f"topic: {self.topic}\n"
            f"date: {today}\n"
            f"prompt_version: {'article_compare_v1' if TOPIC_PLAN.get(self.topic, {}).get('compare') else 'article_v1'}\n"
            f"model: {self.llm.model}\n"
            f"sources:\n{srcs}\n"
            "draft: false\n"
            "---\n"
        )

    def markdown(self) -> str:
        foot = "\n".join(f"{s}" for s in self.sources)
        disclaimer = ARTICLE_DISCLAIMER.get(self.lang, ARTICLE_DISCLAIMER["en"])
        heading = SOURCES_HEADING.get(self.lang, "Sources")
        return f"{self.frontmatter()}\n{self.body_md.strip()}\n\n## {heading}\n\n{foot}\n\n{disclaimer}\n"

    def public_url(self, site_url: str) -> str:
        """English is served from the root of the site; the others carry their /es or /fr prefix."""
        prefix = "" if self.lang == "en" else f"/{self.lang}"
        return f"{site_url}{prefix}/guides/{self.slug}"

    def social_text(self, site_url: str) -> str:
        return f"{self.title}\n\n{self.summary}\n\n{self.public_url(site_url)}\n\nSources: {', '.join(sorted({s.split(' — ')[0].split('] ')[1] for s in self.sources}))}"


def load_prompt(version: str = "article_v1") -> str:
    return (PROMPTS_DIR / f"{version}.md").read_text(encoding="utf-8")


#: Cuántas fuentes legibles hacen falta para poner las legibles delante. Por debajo de esto se
#: prefiere una guía bien fundada con fuentes que el lector no puede abrir a una guía floja: el
#: material manda sobre la comodidad de comprobarlo. Con tres, la fiebre en hindi pasa de citar
#: cinco hojas del SEUP a abrir con la del NHS.
MIN_LEGIBLES = 3


def _readable_first(hits: list[Hit], lang: str) -> list[Hit]:
    """Las fuentes que ese lector puede abrir, delante — si hay bastantes (16-sep-2026).

    Medido sobre lo publicado: 20 de las 62 guías en hindi y 20 de las 62 en árabe citaban
    ÚNICAMENTE organismos que publican en castellano, porque las anclas de cada tema son
    españolas (el corpus empezó así) y `gather_hits` no sabía en qué lengua se iba a escribir.
    La de la fiebre en hindi llevaba cinco fuentes y las cinco eran la misma hoja del SEUP.

    No se filtra: se reordena. Si no hay material legible suficiente, se escribe con lo que hay,
    que es mejor que una guía pobre — pero el orden decide qué cita el modelo.
    """
    from pedibot.index.store import READABLE_FALLBACK

    legibles_langs = {lang, READABLE_FALLBACK.get(lang, "")}
    if lang == "es" or not legibles_langs:
        return hits
    legibles = [h for h in hits if h.chunk.lang in legibles_langs]
    if len(legibles) < MIN_LEGIBLES:
        return hits
    return legibles + [h for h in hits if h.chunk.lang not in legibles_langs]


def gather_hits(index: Index, topic: str, max_chunks: int = 10, lang: str = "es") -> list[Hit]:
    plan = TOPIC_PLAN[topic]
    # Se mira el doble de hondo cuando hay que encontrar material que ese lector pueda abrir: con
    # 40, del NHS sobre la fiebre casaba UN pasaje y la guía hindi salía entera del SEUP.
    hondo = 40 if lang == "es" else 90
    hits = index.search(str(plan["query"]), top_k=hondo, prefer_parent_leaflets=True)
    wanted: list[str] = list(plan["docs"])  # type: ignore[call-overload]
    anchored = [h for h in hits if h.chunk.doc_id in wanted and h.chunk.usage == "publico"]
    topics = {h.chunk.topic for h in anchored}
    others = [
        h
        for h in hits
        if h.chunk.doc_id not in wanted and h.chunk.usage == "publico" and h.chunk.topic in topics
    ]
    if plan.get("compare"):
        # one or two passages per organisation so the table has every voice
        per_org: dict[str, list[Hit]] = {}
        for h in anchored:
            per_org.setdefault(h.chunk.org, []).append(h)
        anchored = [h for hs in per_org.values() for h in hs[:2]]
    return _readable_first(anchored + others, lang)[:max_chunks]


def _format_sources(hits: list[Hit]) -> str:
    lines = []
    for i, h in enumerate(hits, start=1):
        c = h.chunk
        tag = " [DOSE TABLE]" if c.is_dose_table else ""
        tag += " [WARNING SIGNS]" if c.is_red_flag else ""
        lines.append(
            f"[{i}] {c.org} — {c.doc_title} — section: {c.section} (p. {', '.join(map(str, c.pages))}){tag}\n{c.text}"
        )
    return "\n\n".join(lines)


def parse_output(text: str) -> tuple[str, str, str]:
    m_t = re.search(r"TITLE:\s*(.+)", text)
    m_s = re.search(r"SUMMARY:\s*(.+)", text)
    m_b = re.search(r"BODY:\s*(.+)", text, re.S)
    if not m_b:
        # The model often goes straight from SUMMARY to the first heading and never writes the
        # literal marker. That is a formatting slip, not a bad article: the first "## " is an
        # unambiguous start of the body, and throwing the draft away costs a whole generation.
        m_b = re.search(r"(^##\s.+)", text, re.S | re.M)
    if not (m_t and m_s and m_b):
        # keep a snippet: "missing TITLE/SUMMARY/BODY" alone says nothing about what came back
        head = " ".join(text.split())[:140]
        raise ValueError(f"article output missing TITLE/SUMMARY/BODY — got: {head!r}")
    return m_t.group(1).strip(), m_s.group(1).strip(), m_b.group(1).strip()


# The "common questions" heading of each language, exactly as the article prompt asks for it and
# as web/site/src/guides.ts looks for it. A guide whose FAQ heading drifts loses its structured
# data with no error; a language missing from here would silently stop being checked, which is
# why a test walks SUPPORTED_LANGS against it.
FAQ_HEADING = {
    "en": "Common questions",
    "es": "Preguntas frecuentes",
    "fr": "Questions fréquentes",
    "de": "Häufige Fragen",
    "ru": "Частые вопросы",
    "ar": "أسئلة شائعة",
    "pt": "Perguntas frequentes",
    "hi": "आम सवाल",
}

# Deliberately loose: the question is whether the section EXISTS, not how it is worded. German
# alone writes that heading three ways across the published guides and all three are fine.
DOCTOR_WORDS = {
    "en": ("doctor", "emergency"),
    "es": ("médico", "urgencias"),
    "fr": ("médecin", "urgences"),
    "de": ("arzt", "ärztin", "notaufnahme"),
    "ru": ("врач", "отделение"),
    "ar": ("الطبيب", "الطوارئ"),
    "pt": ("médico", "pronto-socorro", "emergência"),
    "hi": ("डॉक्टर", "इमरजेंसी", "अस्पताल"),
}

# Languages with an alphabet of their own: a heading with none of it is a heading in another
# language. Two Hindi guides shipped with "En qué coinciden" over an article of Devanagari.
OWN_SCRIPT = {
    "ru": ("\u0400", "\u04ff"),
    "ar": ("\u0600", "\u06ff"),
    "hi": ("\u0900", "\u097f"),
}

# German addresses the reader as "Sie" everywhere else on the site (prompt rule 9). A guide that
# switches to "du" reads like a different website; three did.
_DUZEN = re.compile(r"\b(du|dein|deine|deinem|deinen|deiner|deines|dich|dir)\b", re.I)
# What the guide tells a parent to SAY to their child is quoted, and inside those quotes
# the informal form is the correct German: «Sagen Sie: „Ich verstehe, dass dich das
# beschäftigt"». Counting those failed the two guides that handle it best — anxiety and
# self-harm, the topics that exist to give a parent words — while the one that really did
# address the reader as "du" from its first line sat next to them. The rule is about the
# guide's own prose, so the prose is what gets counted.
_QUOTED = re.compile('[„“”"«»][^„“”"«»]{0,400}[“”"»]')


def _structure_problems(body: str, lang: str, compare: bool) -> list[str]:
    """The sections the prompt demands, checked on the draft instead of counted afterwards."""
    out: list[str] = []
    heads = [h.strip() for h in re.findall(r"^## (.+)$", body, re.M)]
    if len(heads) < 3:
        out.append(f"missing_sections (only {len(heads)} headings; the prompt asks for four)")
    words = DOCTOR_WORDS.get(lang, DOCTOR_WORDS["en"])
    if not any(w in h.lower() for h in heads for w in words):
        out.append(
            "no_doctor_section: every guide must end with the section on when to see a doctor"
            " or go to the emergency department, written in the requested language"
        )
    faq = FAQ_HEADING.get(lang)
    if not compare and faq and not any(faq in h for h in heads):
        out.append(f"no_faq_section: the last heading must be exactly '## {faq}'")
    lo, hi = OWN_SCRIPT.get(lang, ("", ""))
    if lo:
        alien = [h for h in heads if not any(lo <= c <= hi for c in h)]
        if alien:
            out.append(
                f"heading_in_another_language ({alien[0]!r}): every heading in the language of"
                " the article, not only the body"
            )
    if lang == "de" and len(_DUZEN.findall(_QUOTED.sub(" ", body))) >= 3:
        out.append("wrong_register: address the reader as 'Sie', never 'du'")
    return out


def _problems(
    title: str, body: str, hits: list[Hit], lang: str, compare: bool = False
) -> list[str]:
    """Verification of the draft: citations and doses (shared with the answer engine) plus the
    language. A Spanish guide written into web/content/en carries `lang: en` in its frontmatter,
    which breaks canonical and hreflang as well as reading wrong."""
    problems = verify(body, hits)
    if detect_lang(f"{title} {body}") != lang:
        want = LANGUAGE_NAME.get(lang, "English")
        problems.append(f"wrong_language (write the WHOLE article in {want})")
    # the sources block quotes documents verbatim, so only the prose is checked
    prose = "\n".join(
        line for line in body.splitlines() if not line.strip().startswith(('- "[', "*", "["))
    )
    found = foreign_service_problem(prose)
    if found:
        problems.append(found)
    # El idioma, línea a línea y no sólo en conjunto. `detect_lang` mira el artículo entero y da
    # portugués a un artículo portugués con un encabezado en castellano: así se publicó «Quando
    # acudir al médico ou a urgencias», y estuvo vivo (16-sep-2026). Se miran el título y los
    # encabezados, que es donde se cuela, con la misma lista que revisa el sitio construido.
    for linea in [title, *re.findall(r"^#+ (.+)$", body, re.M)]:
        fuga = foreign_markers(linea, lang)
        if fuga:
            otra, palabra = fuga[0]
            problems.append(
                f"language_leak ({palabra!r} is {otra}, in {linea.strip()[:60]!r}): every"
                f" heading and the title in {LANGUAGE_NAME.get(lang, 'English')}, not only"
                " the body"
            )
            break
    problems.extend(_structure_problems(body, lang, compare))
    return problems


# How much room a draft gets, by writing system. A guide is 500-800 words in every language, but
# a tokenizer does not charge the same for them: Devanagari costs roughly twice what Latin does
# for the same article, and the flat 1800 that fits an English guide cut eight Hindi ones off
# mid-sentence — one of them in the middle of a list of anaphylaxis warning signs.
# This is a ceiling, not a spend: the model is asked for 500-800 words and stops there.
DRAFT_TOKENS = {"hi": 3200, "ru": 2400, "ar": 2400}
DRAFT_TOKENS_DEFAULT = 1800


def generate_article(index: Index, llm: LLMProvider, topic: str, lang: str = "en") -> Article:
    hits = gather_hits(index, topic, lang=lang)
    if not hits:
        raise ValueError(f"no sources for topic {topic}")
    compare = bool(TOPIC_PLAN[topic].get("compare"))
    system = load_prompt("article_compare_v1" if compare else "article_v1")
    # The language is named at the top AND repeated after the sources: the sources are thousands
    # of words in another language sitting at the end of the prompt, which is where a model
    # weighs hardest. With the instruction only at the top, drafts came back in the sources'
    # language and without the TITLE/SUMMARY header at all (3-sep-2026).
    name = LANGUAGE_NAME.get(lang, "English")
    user = (
        f"LANGUAGE: {name}\n"
        f"TOPIC: {topic}\n\nSOURCES:\n{_format_sources(hits)}\n\n"
        f"REMINDER: write the article in {name}, whatever language the sources above are in, "
        f"and start your answer with the line 'TITLE:' followed by 'SUMMARY:' and the sections."
    )
    room = DRAFT_TOKENS.get(lang, DRAFT_TOKENS_DEFAULT)
    result = llm.complete(system, user, temperature=0.3, max_tokens=room)
    title, summary, body = parse_output(result.text)
    problems = _problems(title, body, hits, lang, compare)
    verification = "ok"
    if problems:
        retry = llm.complete(
            system
            + "\n\nYour previous draft failed verification: "
            + ", ".join(problems)
            + ". Fix it.",
            user,
            temperature=0.0,
            max_tokens=room,
        )
        title, summary, body = parse_output(retry.text)
        if _problems(title, body, hits, lang, compare):
            raise ValueError(f"article for {topic} failed verification twice: {problems}")
        result, verification = retry, "regenerated"
    cited = sorted({int(n) for n in _CIT.findall(body)})
    sources = [
        f"[{n}] {localise_citation(hits[n - 1].chunk.citation(), lang)}"
        + (f" — {hits[n - 1].chunk.source_url}" if hits[n - 1].chunk.source_url else "")
        for n in cited
    ]
    return Article(
        topic,
        lang,
        title,
        summary,
        body,
        sources,
        [h.chunk.chunk_id for h in hits],
        result,
        verification,
    )


def redirects_path(content_dir: Path) -> Path:
    return content_dir / "_redirects.json"


def remember_redirect(content_dir: Path, lang: str, viejo: str, nuevo: str) -> None:
    """La dirección vieja de una guía renombrada, para que el sitio la redirija (16-sep-2026).

    Regenerar una guía le cambia el título y, con él, el nombre del fichero — y eso es a
    propósito: así se arreglaron slugs mal transliterados como «was_tun_bei_einer_erk_ltung».
    Lo que no puede pasar es que la dirección vieja muera: es lo único de una guía que no se
    puede rehacer, y es exactamente lo que Google tiene indexado. Al regenerar la guía inglesa
    de la cefalea su dirección se quedó en nada y hubo que escribir la redirección a mano.

    El sitio lee este fichero al construirse (`web/site/astro.config.mjs`).
    """
    import json as _json

    prefijo = "" if lang == "en" else f"/{lang}"
    destino = f"{prefijo}/guides/{nuevo}"
    ruta = redirects_path(content_dir)
    datos: dict[str, str] = {}
    if ruta.exists():
        try:
            datos = _json.loads(ruta.read_text(encoding="utf-8"))
        except _json.JSONDecodeError:
            datos = {}
    datos[f"{prefijo}/guides/{viejo}"] = destino
    # una cadena vieja→media→nueva se aplana: nadie quiere dos saltos
    for origen, actual in list(datos.items()):
        if actual == f"{prefijo}/guides/{viejo}":
            datos[origen] = destino
    datos.pop(destino, None)  # la dirección viva nunca se redirige a sí misma
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(
        _json.dumps(datos, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8"
    )


def write_article(
    a: Article, content_dir: Path, queue_dir: Path, site_url: str
) -> tuple[Path, Path]:
    out = content_dir / a.lang / f"{a.slug}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    # A slug that collapses writes every guide of that language to one filename, and each new
    # guide costs money and deletes the last one — fifty-five Hindi guides went into hi/s.md
    # before anyone looked. Regenerating the same topic is fine and overwrites on purpose;
    # a different topic at the same path is a slug bug and has to stop the run.
    if out.exists():
        previous = out.read_text(encoding="utf-8")
        for line in previous.splitlines():
            if line.startswith("topic: ") and line[7:].strip() != a.topic:
                raise ValueError(
                    f"colisión de slug en {out.name}: ya es «{line[7:].strip()}» y ahora "
                    f"«{a.topic}». El slug de este idioma no distingue títulos."
                )
    out.write_text(a.markdown(), encoding="utf-8")
    # The filename comes from the title, and a regenerated guide gets a new title — so without
    # this the old file stays and the language ends up with two guides on one subject, competing
    # for the same search. One topic, one language, one guide.
    for other in sorted(out.parent.glob("*.md")):
        if other == out:
            continue
        for line in other.read_text(encoding="utf-8").splitlines()[:12]:
            if line.startswith("topic: "):
                if line[7:].strip() == a.topic:
                    # la dirección vieja no muere: queda redirigida a la nueva
                    remember_redirect(content_dir, a.lang, other.stem, a.slug)
                    other.unlink()
                break
    q = queue_dir / "x" / f"{a.lang}-{a.slug}.txt"
    q.parent.mkdir(parents=True, exist_ok=True)
    q.write_text(a.social_text(site_url), encoding="utf-8")
    return out, q


def seasonal_first(
    topics: list[str], month: int | None = None, hemisphere: str = "north"
) -> list[str]:
    """Reorder pending topics so this month's seasonal ones (config/seasonal.yaml) come first."""
    import datetime as _dt

    import yaml

    from pedibot.settings import get_settings

    m = month or _dt.date.today().month
    if hemisphere == "south":
        m = (m + 6 - 1) % 12 + 1
    try:
        cal = yaml.safe_load(
            (get_settings().config_dir / "seasonal.yaml").read_text(encoding="utf-8")
        )
        first = [t for t in cal["north"].get(m, []) if t in topics]
    except Exception:  # noqa: BLE001
        first = []
    return first + [t for t in topics if t not in first]


# What each language is called when the model is told which one to write in, and how its
# sources section is headed. Adding a language here is not enough on its own: it also needs its
# triage patterns, or the guides would exist without a safety layer behind the chat.
from pedibot.bot.strings import (  # noqa: E402 — one mapping, not two
    LANGUAGE_NAME,
    localise_citation,
)

SOURCES_HEADING = {
    "en": "Sources",
    "es": "Fuentes",
    "fr": "Sources",
    "de": "Quellen",
    "ru": "Источники",
    "ar": "المصادر",
    "pt": "Fontes",
    "hi": "स्रोत",
}
ARTICLE_DISCLAIMER = {
    "en": "*This guide summarises published paediatric guidelines. It is not medical advice and does not replace your paediatrician. In an emergency, call your local emergency number.*",
    "es": "*Esta guía resume guías pediátricas publicadas. No es consejo médico y no sustituye a tu pediatra. En una emergencia, llama a tu número de emergencias.*",
    "fr": "*Ce guide résume des recommandations pédiatriques publiées. Ce n'est pas un avis médical et cela ne remplace pas votre pédiatre. En cas d'urgence, appelez votre numéro d'urgence.*",
    "de": "*Dieser Ratgeber fasst veröffentlichte kinderärztliche Leitlinien zusammen. Er ist keine medizinische Beratung und ersetzt nicht Ihre Kinderärztin oder Ihren Kinderarzt. Rufen Sie im Notfall Ihre Notrufnummer an.*",
    "ru": "*Эта статья обобщает опубликованные педиатрические рекомендации. Это не медицинская консультация, и она не заменяет вашего педиатра. В экстренной ситуации звоните по местному номеру экстренной службы.*",
    "ar": "*يلخّص هذا الدليل إرشادات طب أطفال منشورة. وهو ليس استشارة طبية ولا يغني عن طبيب طفلك. وفي الحالات الطارئة اتصل برقم الطوارئ المحلي لديك.*",
    "pt": "*Este guia resume diretrizes pediátricas publicadas. Não é orientação médica e não substitui o seu pediatra. Em uma emergência, ligue para o número de emergência da sua região.*",
    "hi": "*यह गाइड प्रकाशित बाल रोग दिशानिर्देशों का सार देती है। यह चिकित्सकीय सलाह नहीं है और आपके बाल रोग विशेषज्ञ की जगह नहीं लेती। आपात स्थिति में अपने इलाक़े के आपातकालीन नंबर पर फ़ोन कीजिए।*",
}


# Topic keys that are two names for the same subject, one Spanish and one English. Publishing
# both gives two nearly identical guides in the same language that split the ranking between
# them. This is an explicit list and not a heuristic on purpose: measuring the overlap of their
# source documents flagged pairs that are genuinely different subjects (breastfeeding vs starting
# solids, asthma vs an asthma attack, gastroenteritis vs vomiting), and losing one of those costs
# a real guide. The rule for adding a pair here: the two keys are the same word in two languages.
SAME_SUBJECT: tuple[frozenset[str], ...] = tuple(
    frozenset(pair)
    for pair in (
        ("anafilaxia", "anaphylaxis_en"),
        ("catarro", "common_cold"),
        ("cefalea", "headache_en"),
        ("constipation", "estrenimiento"),
        ("convulsion_febril", "febrile_seizure"),
        ("golpe_calor", "heat"),
        ("hives", "urticaria"),
        ("head_injury_en", "traumatismo_craneal"),
        ("intoxicaciones", "poisoning_en"),
        ("newborn_care_en", "recien_nacido"),
        ("screen_sleep", "sueno_pantallas"),
        ("vacunas", "vaccines_en"),
        # 18-sep-2026: el suero oral y la gastroenteritis se rozan, pero no son lo mismo: uno
        # explica la enfermedad y el otro cómo se prepara el sobre. Se dejan separados a
        # propósito y esta lista queda como recordatorio de que se miró.
        ("alimentacion_complementaria", "weaning_en"),
        ("diarrhoea_vomiting", "gastroenteritis"),
        ("otitis", "ear_infection"),
    )
)


def same_subject_as(topic: str) -> set[str]:
    """The other keys naming the same subject as this one."""
    return {t for pair in SAME_SUBJECT if topic in pair for t in pair} - {topic}


def pending_topics(content_dir: Path, lang: str) -> list[str]:
    """Topics without an article yet in this language (by frontmatter `topic:`)."""
    done: set[str] = set()
    for f in (content_dir / lang).glob("*.md") if (content_dir / lang).exists() else []:
        m = re.search(r"^topic:\s*(\S+)", f.read_text(encoding="utf-8"), re.M)
        if m:
            done.add(m.group(1))
    # a `_en` suffix means the topic is anchored on English-speaking material (the NHS and CDC
    # vaccination schedules, for instance): in Spanish it only produces a near-duplicate guide
    pending = [t for t in TOPIC_PLAN if t not in done and (lang == "en" or not t.endswith("_en"))]
    return seasonal_first([t for t in pending if not _already_covered(t, done)])


def _already_covered(topic: str, done: set[str]) -> bool:
    """True if a published guide already speaks about this same subject (see SAME_SUBJECT)."""
    return bool(same_subject_as(topic) & done)
