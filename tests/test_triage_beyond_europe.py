"""Los signos de alarma de lo que se acaba de indexar (11-sep-2026).

El corpus creció un 44 % con las enfermedades que pesan fuera de Europa —malaria, dengue,
mordedura de serpiente, rabia, tétanos—. Medido entonces lo que importa de verdad, que no es si
hay documento sino si **la capa de seguridad reconoce sus urgencias**: 17 de 25 preguntas salían
como rutina.

Tres categorías no tenían **ninguna** regla:

- **Mordedura de serpiente.** Emergencia en cualquier sitio, y *la* emergencia en la India rural
  y buena parte del mundo árabe.
- **Mordedura de mamífero.** En India es rabia: una vez hay síntomas es mortal casi siempre, y la
  profilaxis post-exposición se cuenta en horas. Un perro que muerde no es una picadura.
- **Sangrado con fiebre.** Es el signo de dengue grave que la OMS enumera —encías, nariz, vómito
  con sangre—, y el sitio ya publica la ficha de dengue en cinco idiomas.

Y una a medias: el **trismo** del tétanos («no puede abrir la boca») saltaba en castellano, árabe
y portugués, y no en inglés ni en hindi.

Esto fija que las cuatro se reconozcan en las ocho lenguas, y —tan importante como eso— que no
se disparen con lo que se les parece: una picadura de mosquito no es una mordedura de perro, y
unas encías que sangran al cepillarse no son dengue.
"""

from __future__ import annotations

import pytest

from pedibot.bot.triage import Triage
from pedibot.settings import ROOT


@pytest.fixture(scope="module")
def triaje() -> Triage:
    return Triage(ROOT / "config" / "red_flags.yaml")


ALARMAS: dict[str, dict[str, str]] = {
    "mordedura de serpiente": {
        "en": "my child was bitten by a snake",
        "es": "a mi hijo le ha mordido una serpiente",
        "fr": "mon enfant a été mordu par un serpent",
        "de": "meinen Sohn hat eine Schlange gebissen",
        "ru": "моего ребёнка укусила змея",
        "ar": "لدغت أفعى ابني",
        "pt": "o meu filho foi picado por uma cobra",
        "hi": "मेरे बच्चे को साँप ने काट लिया",
    },
    "mordedura de mamífero": {
        "en": "a dog bit my child on the hand",
        "es": "un perro ha mordido a mi hijo en la mano",
        "fr": "un chien a mordu mon enfant à la main",
        "de": "ein Hund hat mein Kind in die Hand gebissen",
        "ru": "собака укусила моего ребёнка за руку",
        "ar": "عضّ كلب ابني في يده",
        "pt": "um cão mordeu o meu filho na mão",
        "hi": "मेरे बच्चे को कुत्ते ने हाथ पर काट लिया",
    },
    "sangrado con fiebre": {
        "en": "my child has a fever and his gums are bleeding",
        "es": "mi hijo tiene fiebre y le sangran las encías",
        "fr": "mon enfant a de la fièvre et ses gencives saignent",
        "de": "mein Kind hat Fieber und das Zahnfleisch blutet",
        "ru": "у ребёнка температура и кровоточат дёсны",
        "ar": "طفلي مصاب بالحمى ولثته تنزف",
        "pt": "o meu filho tem febre e as gengivas estão a sangrar",
        "hi": "मेरे बच्चे को बुखार है और मसूड़ों से खून आ रहा है",
    },
    "trismo": {
        "en": "my child has muscle spasms and cannot open his mouth",
        "es": "mi hijo tiene espasmos y no puede abrir la boca",
        "fr": "mon enfant a des spasmes et ne peut pas ouvrir la bouche",
        "de": "mein Kind hat Krämpfe und kann den Mund nicht öffnen",
        "ru": "у ребёнка спазмы и он не может открыть рот",
        "ar": "طفلي يعاني من تشنجات ولا يستطيع فتح فمه",
        "pt": "o meu filho tem espasmos e não consegue abrir a boca",
        "hi": "मेरे बच्चे को ऐंठन है और वह मुँह नहीं खोल पा रहा",
    },
}

#: lo que se les parece y NO puede disparar: el coste de un falso positivo es que el aviso
#: se deja de leer, y entonces no sirve la vez que acierta
PARECIDOS = [
    "my child has a mosquito bite on his arm",
    "a mí me picó un mosquito en el brazo de mi hijo",
    "le sangran un poco las encías cuando se cepilla los dientes",
    "my child's gums bleed a little when he brushes his teeth",
    "mon enfant a une piqûre de moustique",
    "मेरे बच्चे को मच्छर ने काटा है",
    "o meu filho tem uma picada de mosquito",
]


@pytest.mark.parametrize(
    ("alarma", "lang"),
    [(a, lg) for a, langs in ALARMAS.items() for lg in langs],
)
def test_la_alarma_salta_en_cada_lengua(triaje: Triage, alarma: str, lang: str):
    r = triaje.assess(ALARMAS[alarma][lang])
    assert "routine" not in str(r.level).lower(), (
        f"«{ALARMAS[alarma][lang]}» ({lang}) sale como rutina; es {alarma}"
    )


@pytest.mark.parametrize("texto", PARECIDOS)
def test_lo_que_se_le_parece_no_dispara(triaje: Triage, texto: str):
    r = triaje.assess(texto)
    assert "routine" in str(r.level).lower(), (
        f"falso positivo: «{texto}» sale como {r.level} por {r.matched}"
    )


#: El dolor abdominal intenso es el PRIMER signo de alarma de dengue grave que enumera la OMS, y
#: la regla existente (`severe_abdominal_pain`, escrita desde la hoja de la SEUP) pedía en
#: castellano «muy fuerte», «insoportable», «no para» o «empeora» — y no reconocía la palabra que
#: de verdad usa un padre cuando traduce la ficha: «intenso». Medido en las ocho lenguas:
#: fallaba en castellano, francés y ruso, y acertaba en las otras cinco.
ABDOMEN: dict[str, str] = {
    "en": "my child has severe abdominal pain and a fever",
    "es": "mi hijo tiene dolor abdominal intenso y fiebre",
    "fr": "mon enfant a une douleur abdominale intense et de la fièvre",
    "de": "mein Kind hat starke Bauchschmerzen und Fieber",
    "ru": "у ребёнка сильная боль в животе и температура",
    "ar": "طفلي لديه ألم شديد في البطن وحمى",
    "pt": "o meu filho tem dor abdominal intensa e febre",
    "hi": "मेरे बच्चे को पेट में तेज़ दर्द और बुखार है",
}

#: Y como lo dice un padre, no una ficha clínica
ABDOMEN_COMO_SE_DICE = [
    "le duele mucho el abdomen desde ayer",
    "mon enfant a très mal au ventre",
]

#: Un dolor de barriga sin más es lo más común de la consulta: no puede salir con alarma
ABDOMEN_RUTINA = [
    "a mi hijo le duele un poco la barriga",
    "my child has a mild tummy ache",
    "mon enfant a un peu mal au ventre",
]


@pytest.mark.parametrize("lang", sorted(ABDOMEN))
def test_el_dolor_abdominal_intenso_salta_en_cada_lengua(triaje: Triage, lang: str):
    r = triaje.assess(ABDOMEN[lang])
    assert "routine" not in str(r.level).lower(), (
        f"«{ABDOMEN[lang]}» ({lang}) sale como rutina; es el primer signo de dengue grave"
    )


@pytest.mark.parametrize("texto", ABDOMEN_COMO_SE_DICE)
def test_tambien_como_lo_dice_un_padre(triaje: Triage, texto: str):
    r = triaje.assess(texto)
    assert "routine" not in str(r.level).lower(), f"«{texto}» sale como rutina"


@pytest.mark.parametrize("texto", ABDOMEN_RUTINA)
def test_un_dolor_de_barriga_cualquiera_no_dispara(triaje: Triage, texto: str):
    r = triaje.assess(texto)
    assert "routine" in str(r.level).lower(), (
        f"falso positivo: «{texto}» sale como {r.level} por {r.matched}"
    )
