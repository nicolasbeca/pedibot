"""El antibiótico recetado: ninguna cifra, el resto de la pregunta sí (26-oct-2026).

Consulta real 1075: amoxicilina recetada para una otitis, 14 kg, jarabe de 125 mg/5 ml. La tabla
autorizada de la AEPap da 25-50 mg/kg/día; en la otitis se recetan 80-90. Con la cifra general
delante, una receta correcta parece una sobredosis y el padre da de menos: el redactor no da
ninguna, ni de la tabla. Decisión del operador (26-oct).
Ver tests/test_the_prescribed_antibiotic.py.
"""

from __future__ import annotations

import re

#: un antibiótico, por su nombre o por la palabra, en las lenguas del sitio
ANTIBIOTICO = re.compile(
    r"antibi[oó]tic|antibiotique|antibiotikum|antibiotika"
    r"|amoxic|amoxyc|augmentin|clamoxyl|clavul|azitromic|azithromyc|zithromax|cefuroxim"
    r"|cefalexin|cephalexin|cefadroxil|penicil|eritromic|erythromyc|claritromic|clarithromyc"
    r"|антибиотик|амоксицил|аугментин|азитромиц"
    r"|مضاد حيوي|مضادات حيوية|أموكسيسيلين"
    r"|एंटीबायोटिक|एमोक्सिसिलिन",
    re.IGNORECASE,
)

NOTA_ANTIBIOTICO = (
    "PRESCRIBED ANTIBIOTIC: the parent asks about an antibiotic. Give NO dose for it in mg or ml, "
    "not even from a DOSE TABLE, and do not calculate one: the dose depends on the infection, and "
    "for an ear infection doctors often prescribe more than a table's general range, so a table "
    "could make a correct prescription look wrong. Say to give exactly what the prescription or "
    "the label says, and that if they are unsure how many ml that is with their bottle, the "
    "pharmacist can check it with them. Then answer the rest of the question from the sources: "
    "the illness they name (what helps with the pain, how long it usually takes, when to go back "
    "to the doctor), and how to give the medicine.\n"
)


#: una dosis del antibiótico: miligramos por kilo, o mililitros que no son la concentración del
#: frasco («125 mg/5 ml», «125 mg en 5 ml» la dicen el NHS y la receta, y no es una dosis)
_CIFRA = re.compile(
    r"\bmg\s*/\s*kg\b|\bmg (por|per|pro|par) (kg|kilo)"
    r"|(?<!/)(?<!/ )(?<!en )(?<!in )(?<!em )(?<!dans )(?<![\d.,])\d+(?:[.,]\d+)?\s*ml\b(?!\s*/)",
    re.IGNORECASE,
)

PONE_CIFRA = (
    "antibiotic_dose: you gave a dose of the prescribed antibiotic. Remove every mg/kg figure and "
    "every amount in ml; say to follow the prescription and that the pharmacist can check the ml"
)


def da_cifra_del_antibiotico(texto: str) -> bool:
    return bool(_CIFRA.search(texto))


def pregunta_por_antibiotico(texto: str) -> bool:
    return bool(ANTIBIOTICO.search(texto))


def nota_antibiotico(texto: str) -> str:
    return NOTA_ANTIBIOTICO if pregunta_por_antibiotico(texto) else ""
