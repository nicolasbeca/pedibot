"""La curva de crecimiento de la OMS, calculada aquí y sin modelo (13-sep-2026).

Dónde está un niño en la curva —peso para la edad, talla para la edad, peso para la talla hasta
los cinco años; talla e IMC para la edad de cinco a diecinueve— con las tablas LMS que publica
la OMS y sus cortes: emaciación, retraso del crecimiento, bajo peso, sobrepeso, delgadez. La
desnutrición aguda grave (peso para la talla por debajo de −3 DE) sale como urgencia, que es lo
que la OMS pide que sea.

El método es el de WHO Anthro: z = ((x/M)^L − 1) / (L·S), y en los indicadores de peso, más allá
de ±3, cada desviación vale lo que va de SD2 a SD3 — la curva LMS no se extrapola.
"""

from __future__ import annotations

import bisect
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

DAYS_PER_MONTH = 30.4375

#: los indicadores de peso llevan la corrección más allá de ±3; los de talla no
_RESTRICTED = {"wfa", "wfh", "bmi"}

#: cortes de la OMS por indicador: (z máximo excluyente, etiqueta), de abajo arriba
_CUTS: dict[str, list[tuple[float, str]]] = {
    "wfa": [(-3, "severely_underweight"), (-2, "underweight"), (math.inf, "normal")],
    "lhfa": [(-3, "severely_stunted"), (-2, "stunted"), (math.inf, "normal")],
    "hfa": [(-3, "severely_stunted"), (-2, "stunted"), (math.inf, "normal")],
    "wfh": [
        (-3, "severely_wasted"),
        (-2, "wasted"),
        (2, "normal"),
        (3, "overweight"),
        (math.inf, "obese"),
    ],
    "bmi": [
        (-3, "severely_thin"),
        (-2, "thin"),
        (1, "normal"),
        (2, "overweight"),
        (math.inf, "obese"),
    ],
}

#: lo que es una urgencia: desnutrición aguda grave (OMS), y cualquier peso por debajo de −3
_URGENT = {"severely_wasted", "severely_underweight", "severely_thin"}

SOURCE_2006 = "WHO Child Growth Standards (2006)"
SOURCE_2007 = "WHO Growth Reference (2007)"
SOURCE_CDC = "CDC Growth Charts (2000)"

#: Con qué se calcula: la OMS en todo el mundo, o como en Estados Unidos, donde el CDC recomienda
#: la OMS hasta los 2 años y sus propias tablas de 2000 desde los 2 hasta los 20.
REFERENCES = ("who", "cdc")


def _cdc_flag(name: str, pct: float, z: float) -> str:
    """Las categorías del CDC van por percentil, no por desviaciones.

    IMC: bajo peso por debajo del 5, sobrepeso del 85 al 95, obesidad desde el 95. Peso y talla no
    tienen categorías en el CDC; se señala lo que queda fuera del 3–97, que es lo que marca la
    propia gráfica. Por debajo de −3 DE se sigue avisando como en la OMS: eso no es una cuestión
    de tablas.
    """
    if name == "bmi":
        if z < -3:
            return "severely_thin"
        if pct < 5:
            return "cdc_underweight"
        if pct >= 95:
            return "cdc_obese"
        if pct >= 85:
            return "cdc_overweight"
        return "normal"
    if z < -3 and name == "wfa":
        return "severely_underweight"
    if pct < 3:
        return "below_p3"
    if pct > 97:
        return "above_p97"
    return "normal"


def lms_z(x: float, L: float, M: float, S: float, restricted: bool = False) -> float:
    """z según LMS. Con `restricted`, más allá de ±3 se mide en tramos SD2→SD3 (WHO Anthro)."""
    z = (math.log(x / M) / S) if abs(L) < 1e-9 else (((x / M) ** L) - 1) / (L * S)
    if not restricted or abs(z) <= 3:
        return z

    def sd(k: float) -> float:
        return M * (1 + L * S * k) ** (1 / L) if abs(L) >= 1e-9 else M * math.exp(S * k)

    if z > 3:
        return 3 + (x - sd(3)) / (sd(3) - sd(2))
    return -3 - (sd(-3) - x) / (sd(-2) - sd(-3))


def percentile(z: float) -> float:
    return 100 * 0.5 * (1 + math.erf(z / math.sqrt(2)))


@dataclass
class Indicator:
    name: str  # wfa | lhfa | wfh | hfa | bmi
    table: str
    value: float
    z: float
    percentile: float
    flag: str


@dataclass
class Assessment:
    indicators: list[Indicator]
    level: str  # routine | urgent
    missing: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)


class Growth:
    def __init__(self, path: Path) -> None:
        raw = json.loads(path.read_text(encoding="utf-8"))
        self._tables: dict[str, list[list[float]]] = {
            k: v["rows"] for k, v in raw["tables"].items()
        }
        self._keys: dict[str, list[float]] = {k: [r[0] for r in v] for k, v in self._tables.items()}
        self.meta = raw.get("meta", {})

    def range(self, table: str) -> tuple[float, float]:
        ks = self._keys[table]
        return ks[0], ks[-1]

    def lms(self, table: str, x: float) -> tuple[float, float, float]:
        """L, M, S en `x`, interpolando linealmente entre las dos filas que lo rodean."""
        ks, rows = self._keys[table], self._tables[table]
        if x < ks[0] or x > ks[-1]:
            raise ValueError(f"{table}: {x} fuera de {ks[0]}–{ks[-1]}")
        i = bisect.bisect_left(ks, x)
        if i < len(ks) and ks[i] == x:
            return rows[i][1], rows[i][2], rows[i][3]
        a, b = rows[i - 1], rows[i]
        t = (x - a[0]) / (b[0] - a[0])
        return tuple(a[j] + t * (b[j] - a[j]) for j in (1, 2, 3))  # type: ignore[return-value]

    def _one(self, name: str, table: str, key: float, value: float) -> Indicator:
        L, M, S = self.lms(table, key)
        if table.startswith("cdc_"):
            # el CDC no aplica la corrección de la OMS más allá de ±3
            z = lms_z(value, L, M, S)
            pct = percentile(z)
            flag = _cdc_flag(name, pct, z)
        else:
            z = lms_z(value, L, M, S, restricted=name in _RESTRICTED)
            pct = percentile(z)
            flag = next(label for top, label in _CUTS[name] if z < top)
        return Indicator(name, table, value, round(z, 2), round(pct, 1), flag)

    def assess(
        self,
        sex: str,
        age_months: float,
        weight_kg: float | None = None,
        height_cm: float | None = None,
        reference: str = "who",
    ) -> Assessment:
        s = sex.lower()[0]
        if s not in ("m", "f"):
            raise ValueError("sex: m | f")
        if reference not in REFERENCES:
            raise ValueError(f"reference: {' | '.join(REFERENCES)}")
        tope = 240 if reference == "cdc" else 228
        if not 0 <= age_months <= tope:
            raise ValueError(f"age: 0–{tope} months")
        if weight_kg is not None and not 0.5 <= weight_kg <= 200:
            raise ValueError("weight_kg: 0.5–200")
        if height_cm is not None and not 30 <= height_cm <= 220:
            raise ValueError("height_cm: 30–220")
        out: list[Indicator] = []
        notes: list[str] = []
        sources: list[str] = []
        days = age_months * DAYS_PER_MONTH
        pequeño = days <= 1856  # los patrones 2006 llegan al día 1856 (5 años)

        def intenta(name: str, table: str, key: float, value: float) -> None:
            try:
                out.append(self._one(name, table, key, value))
            except ValueError:
                notes.append(f"{name}: {key:g} fuera de la tabla {table}")

        if reference == "cdc" and age_months >= 24:
            sources.append(SOURCE_CDC)
            if weight_kg is not None:
                intenta("wfa", f"cdc_wfa_{s}", age_months, weight_kg)
            if height_cm is not None:
                intenta("hfa", f"cdc_hfa_{s}", age_months, height_cm)
            if weight_kg is not None and height_cm is not None:
                intenta("bmi", f"cdc_bmi_{s}", age_months, weight_kg / (height_cm / 100) ** 2)
        elif pequeño:
            sources.append(SOURCE_2006)
            if weight_kg is not None:
                intenta("wfa", f"wfa_{s}", days, weight_kg)
            if height_cm is not None:
                intenta("lhfa", f"lhfa_{s}", days, height_cm)
            if weight_kg is not None and height_cm is not None:
                # tumbado hasta los dos años (longitud), de pie después (talla)
                table = f"wfl_{s}" if age_months < 24 else f"wfh_{s}"
                intenta("wfh", table, round(height_cm, 1), weight_kg)
        else:
            sources.append(SOURCE_2007)
            if weight_kg is not None and age_months <= 120:
                intenta("wfa", f"wfa510_{s}", age_months, weight_kg)
            if height_cm is not None:
                intenta("hfa", f"hfa519_{s}", age_months, height_cm)
            if weight_kg is not None and height_cm is not None:
                intenta("bmi", f"bmi519_{s}", age_months, weight_kg / (height_cm / 100) ** 2)
        missing = [m for m, v in (("weight", weight_kg), ("height", height_cm)) if v is None]
        level = "urgent" if any(i.flag in _URGENT for i in out) else "routine"
        return Assessment(out, level, missing, notes, sources)


#: Lo que un padre escribe cuando lo que le preocupa es el peso o la talla, no un síntoma.
_GROWTH = re.compile(
    # «المئين» y «पर्सेंटाइल» faltaban: en vivo, el árabe y el hindi no enlazaban la calculadora
    r"percentil|percentile|centile|perzentil|перцентил|процентил|المئوي|مئين|المئين|प्रतिशत"
    r"|पर्सेंटाइल|ग्रोथ चार्ट|منحنى النمو|кривая роста"
    r"|curva de crecimiento|growth chart|courbe de croissance|wachstumskurve"
    # «no gana peso», en las ocho: la negación delante del verbo…
    r"|(?:not|isn'?t|n[aã]o|ne|no|nicht|не|لا|नहीं)\s*(?:\w+\s){0,2}"
    r"(?:gaining|gain|putting on|ganar?|gana|ganha|engorda|grossit|prend pas de poids"
    r"|zunimmt|nimmt|набирает|прибавляет|يزداد|يزيد|बढ़)"
    # …o detrás (alemán), o «mal» en vez de «no» (ruso)
    r"|nimmt (?:nicht|kaum|nichts) zu|плохо (?:набирает|прибавляет)"
    r"|(?:very|too|muy|demasiado|tr[eè]s|trop|sehr|zu|очень|слишком|جدا|بہत|बहुत)\s*"
    r"(?:thin|skinny|underweight|delgad|flac|maigre|d[üu]nn|mager|худ|نحيف|ضعيف|दुबल|पतल)"
    r"|(?:normal|healthy|adecuado|bien|correct|richtig|нормальн|طبيعي|सही|ठीक).{0,20}"
    r"(?:weight|peso|poids|gewicht|вес|وزن|वज़न|वजन)"
    r"|(?:weight|peso|poids|gewicht|вес|وزن|वज़न|वजन).{0,25}"
    r"(?:normal|for (?:his|her|their) age|para su edad|pour son [aâ]ge|f[üu]r sein alter"
    r"|для возраста|لعمره|उम्र के हिसाब)"
    r"|stunt|retraso del crecimiento|retard de croissance|kleinwuchs|низкий рост"
    r"|قصير القامة|قصر القامة|कद नहीं बढ़|लंबाई नहीं बढ़"
    r"|too short|muy bajito|muy bajo para su edad|trop petit|zu klein"
    r"|слишком маленький рост|قصير جدا|बहुत छोटा कद",
    re.I,
)


def is_growth_question(text: str) -> bool:
    return bool(_GROWTH.search(text))


def gives_both_measurements(text: str) -> bool:
    """El peso Y la talla en el mismo mensaje: eso es una pregunta de crecimiento aunque no
    lleve la palabra.

    17-sep-2026, repasando el chat contra lo vivo: «mi hija de 3 años pesa 13 kg y mide 95 cm»
    salía rutina, sin percentil y sin enlace a la curva. Estaban el sexo, la edad, el peso y la
    talla —todo lo que la tabla necesita— y no se disparaba nada porque la frase no decía
    «percentil». Un padre no tiene por qué saber esa palabra; si teclea las dos medidas está
    preguntando justo eso.

    Con UNA medida no basta, y es a propósito: «pesa 13 kg, ¿cuánto paracetamol?» es una dosis,
    y «pesa 7 kg y tiene fiebre» no es un percentil. Las dos juntas casi no tienen otra lectura.
    """
    _, kg, cm = measurements(text)
    return kg is not None and cm is not None


# ── lo que la API devuelve en la lengua del padre ────────────────────────────────────────
#: nombre de cada indicador, y de cada corte de la OMS, en las ocho lenguas. Vive aquí y no
#: en i18n.ts porque lo usan también Telegram y el agente, que no pasan por el sitio.
LABELS: dict[str, dict[str, str]] = {
    "en": {
        "wfa": "Weight for age",
        "lhfa": "Length/height for age",
        "wfh": "Weight for height",
        "hfa": "Height for age",
        "bmi": "BMI for age",
        "normal": "within the normal range",
        "underweight": "underweight (below −2 SD)",
        "severely_underweight": "severely underweight (below −3 SD)",
        "stunted": "short for age — stunting (below −2 SD)",
        "severely_stunted": "severe stunting (below −3 SD)",
        "wasted": "thin for height — wasting (below −2 SD)",
        "severely_wasted": "severe acute malnutrition (below −3 SD)",
        "overweight": "overweight",
        "obese": "obesity",
        "thin": "thinness (below −2 SD)",
        "severely_thin": "severe thinness (below −3 SD)",
        "below_p3": "below the 3rd percentile",
        "above_p97": "above the 97th percentile",
        "cdc_underweight": "underweight (below the 5th percentile)",
        "cdc_overweight": "overweight (85th–95th percentile)",
        "cdc_obese": "obesity (95th percentile or above)",
        "urgent": "The weight is far below what WHO expects for this height or age.",
    },
    "es": {
        "wfa": "Peso para la edad",
        "lhfa": "Longitud/talla para la edad",
        "wfh": "Peso para la talla",
        "hfa": "Talla para la edad",
        "bmi": "IMC para la edad",
        "normal": "dentro de lo normal",
        "underweight": "bajo peso (por debajo de −2 DE)",
        "severely_underweight": "bajo peso grave (por debajo de −3 DE)",
        "stunted": "talla baja para la edad — retraso del crecimiento (por debajo de −2 DE)",
        "severely_stunted": "retraso del crecimiento grave (por debajo de −3 DE)",
        "wasted": "delgado para su talla — emaciación (por debajo de −2 DE)",
        "severely_wasted": "desnutrición aguda grave (por debajo de −3 DE)",
        "overweight": "sobrepeso",
        "obese": "obesidad",
        "thin": "delgadez (por debajo de −2 DE)",
        "severely_thin": "delgadez grave (por debajo de −3 DE)",
        "below_p3": "por debajo del percentil 3",
        "above_p97": "por encima del percentil 97",
        "cdc_underweight": "bajo peso (por debajo del percentil 5)",
        "cdc_overweight": "sobrepeso (percentil 85 a 95)",
        "cdc_obese": "obesidad (percentil 95 o más)",
        "urgent": "El peso está muy por debajo de lo que la OMS espera para esta talla o edad.",
    },
    "fr": {
        "wfa": "Poids pour l'âge",
        "lhfa": "Taille pour l'âge",
        "wfh": "Poids pour la taille",
        "hfa": "Taille pour l'âge",
        "bmi": "IMC pour l'âge",
        "normal": "dans la normale",
        "underweight": "insuffisance pondérale (sous −2 ET)",
        "severely_underweight": "insuffisance pondérale sévère (sous −3 ET)",
        "stunted": "petite taille pour l'âge — retard de croissance (sous −2 ET)",
        "severely_stunted": "retard de croissance sévère (sous −3 ET)",
        "wasted": "maigre pour sa taille — émaciation (sous −2 ET)",
        "severely_wasted": "malnutrition aiguë sévère (sous −3 ET)",
        "overweight": "surpoids",
        "obese": "obésité",
        "thin": "maigreur (sous −2 ET)",
        "severely_thin": "maigreur sévère (sous −3 ET)",
        "below_p3": "sous le 3e percentile",
        "above_p97": "au-dessus du 97e percentile",
        "cdc_underweight": "insuffisance pondérale (sous le 5e percentile)",
        "cdc_overweight": "surpoids (85e à 95e percentile)",
        "cdc_obese": "obésité (95e percentile ou plus)",
        "urgent": (
            "Le poids est très en dessous de ce que l'OMS attend pour cette taille ou cet âge."
        ),
    },
    "de": {
        "wfa": "Gewicht für Alter",
        "lhfa": "Länge/Größe für Alter",
        "wfh": "Gewicht für Größe",
        "hfa": "Größe für Alter",
        "bmi": "BMI für Alter",
        "normal": "im Normalbereich",
        "underweight": "Untergewicht (unter −2 SD)",
        "severely_underweight": "schweres Untergewicht (unter −3 SD)",
        "stunted": "klein für das Alter — Wachstumsverzögerung (unter −2 SD)",
        "severely_stunted": "schwere Wachstumsverzögerung (unter −3 SD)",
        "wasted": "dünn für die Größe — Auszehrung (unter −2 SD)",
        "severely_wasted": "schwere akute Mangelernährung (unter −3 SD)",
        "overweight": "Übergewicht",
        "obese": "Adipositas",
        "thin": "Untergewicht (unter −2 SD)",
        "severely_thin": "schweres Untergewicht (unter −3 SD)",
        "below_p3": "unter der 3. Perzentile",
        "above_p97": "über der 97. Perzentile",
        "cdc_underweight": "Untergewicht (unter der 5. Perzentile)",
        "cdc_overweight": "Übergewicht (85.–95. Perzentile)",
        "cdc_obese": "Adipositas (ab der 95. Perzentile)",
        "urgent": (
            "Das Gewicht liegt weit unter dem, was die WHO für diese Größe oder dieses Alter "
            "erwartet."
        ),
    },
    "ru": {
        "wfa": "Вес к возрасту",
        "lhfa": "Длина/рост к возрасту",
        "wfh": "Вес к росту",
        "hfa": "Рост к возрасту",
        "bmi": "ИМТ к возрасту",
        "normal": "в пределах нормы",
        "underweight": "недостаточный вес (ниже −2 SD)",
        "severely_underweight": "выраженный дефицит веса (ниже −3 SD)",
        "stunted": "низкий рост для возраста — задержка роста (ниже −2 SD)",
        "severely_stunted": "выраженная задержка роста (ниже −3 SD)",
        "wasted": "худой для своего роста — истощение (ниже −2 SD)",
        "severely_wasted": "тяжёлое острое недоедание (ниже −3 SD)",
        "overweight": "избыточный вес",
        "obese": "ожирение",
        "thin": "худоба (ниже −2 SD)",
        "severely_thin": "выраженная худоба (ниже −3 SD)",
        "below_p3": "ниже 3-го перцентиля",
        "above_p97": "выше 97-го перцентиля",
        "cdc_underweight": "недостаточный вес (ниже 5-го перцентиля)",
        "cdc_overweight": "избыточный вес (85–95-й перцентиль)",
        "cdc_obese": "ожирение (95-й перцентиль и выше)",
        "urgent": "Вес намного ниже того, что ВОЗ ожидает для этого роста или возраста.",
    },
    "ar": {
        "wfa": "الوزن للعمر",
        "lhfa": "الطول للعمر",
        "wfh": "الوزن للطول",
        "hfa": "الطول للعمر",
        "bmi": "مؤشر كتلة الجسم للعمر",
        "normal": "ضمن المعدل الطبيعي",
        "underweight": "نقص الوزن (أقل من −2 انحراف معياري)",
        "severely_underweight": "نقص وزن شديد (أقل من −3 انحراف معياري)",
        "stunted": "قصر القامة للعمر — تقزم (أقل من −2 انحراف معياري)",
        "severely_stunted": "تقزم شديد (أقل من −3 انحراف معياري)",
        "wasted": "نحيف بالنسبة لطوله — هزال (أقل من −2 انحراف معياري)",
        "severely_wasted": "سوء تغذية حاد شديد (أقل من −3 انحراف معياري)",
        "overweight": "زيادة الوزن",
        "obese": "سمنة",
        "thin": "نحافة (أقل من −2 انحراف معياري)",
        "severely_thin": "نحافة شديدة (أقل من −3 انحراف معياري)",
        "below_p3": "أقل من المئين الثالث",
        "above_p97": "أعلى من المئين 97",
        "cdc_underweight": "نقص الوزن (أقل من المئين الخامس)",
        "cdc_overweight": "زيادة الوزن (المئين 85 إلى 95)",
        "cdc_obese": "سمنة (المئين 95 فأكثر)",
        "urgent": "الوزن أقل بكثير مما تتوقعه منظمة الصحة العالمية لهذا الطول أو العمر.",
    },
    "pt": {
        "wfa": "Peso para a idade",
        "lhfa": "Comprimento/altura para a idade",
        "wfh": "Peso para a altura",
        "hfa": "Altura para a idade",
        "bmi": "IMC para a idade",
        "normal": "dentro do normal",
        "underweight": "baixo peso (abaixo de −2 DP)",
        "severely_underweight": "baixo peso grave (abaixo de −3 DP)",
        "stunted": "baixa estatura para a idade — atraso de crescimento (abaixo de −2 DP)",
        "severely_stunted": "atraso de crescimento grave (abaixo de −3 DP)",
        "wasted": "magro para a altura — emagrecimento (abaixo de −2 DP)",
        "severely_wasted": "desnutrição aguda grave (abaixo de −3 DP)",
        "overweight": "excesso de peso",
        "obese": "obesidade",
        "thin": "magreza (abaixo de −2 DP)",
        "severely_thin": "magreza grave (abaixo de −3 DP)",
        "below_p3": "abaixo do percentil 3",
        "above_p97": "acima do percentil 97",
        "cdc_underweight": "baixo peso (abaixo do percentil 5)",
        "cdc_overweight": "excesso de peso (percentil 85 a 95)",
        "cdc_obese": "obesidade (percentil 95 ou mais)",
        "urgent": "O peso está muito abaixo do que a OMS espera para esta altura ou idade.",
    },
    "hi": {
        "wfa": "उम्र के हिसाब से वज़न",
        "lhfa": "उम्र के हिसाब से लंबाई",
        "wfh": "लंबाई के हिसाब से वज़न",
        "hfa": "उम्र के हिसाब से लंबाई",
        "bmi": "उम्र के हिसाब से BMI",
        "normal": "सामान्य सीमा में",
        "underweight": "कम वज़न (−2 SD से नीचे)",
        "severely_underweight": "बहुत कम वज़न (−3 SD से नीचे)",
        "stunted": "उम्र के हिसाब से छोटा कद — स्टंटिंग (−2 SD से नीचे)",
        "severely_stunted": "गंभीर स्टंटिंग (−3 SD से नीचे)",
        "wasted": "लंबाई के हिसाब से दुबला — वेस्टिंग (−2 SD से नीचे)",
        "severely_wasted": "गंभीर तीव्र कुपोषण (−3 SD से नीचे)",
        "overweight": "अधिक वज़न",
        "obese": "मोटापा",
        "thin": "दुबलापन (−2 SD से नीचे)",
        "severely_thin": "गंभीर दुबलापन (−3 SD से नीचे)",
        "below_p3": "तीसरे पर्सेंटाइल से नीचे",
        "above_p97": "97वें पर्सेंटाइल से ऊपर",
        "cdc_underweight": "कम वज़न (5वें पर्सेंटाइल से नीचे)",
        "cdc_overweight": "अधिक वज़न (85वें से 95वें पर्सेंटाइल)",
        "cdc_obese": "मोटापा (95वाँ पर्सेंटाइल या उससे ऊपर)",
        "urgent": "वज़न इस लंबाई या उम्र के लिए WHO की अपेक्षा से बहुत कम है।",
    },
}


def load_countries(path: Path) -> dict[str, dict[str, object]]:
    """Qué tabla usa la cartilla de cada país (config/growth_charts.yaml), clave en mayúsculas."""
    import yaml

    if not path.exists():
        return {}
    datos = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {str(k).upper(): v for k, v in (datos.get("countries") or {}).items()}


def describe(a: Assessment, lang: str) -> dict[str, object]:
    """La valoración con sus etiquetas en la lengua del padre, lista para la API."""
    t = LABELS.get(lang, LABELS["en"])
    return {
        "level": a.level,
        "indicators": [
            {
                "name": i.name,
                "label": t[i.name],
                "value": round(i.value, 2),
                "z": i.z,
                "percentile": i.percentile,
                "flag": i.flag,
                "flag_label": t[i.flag],
            }
            for i in a.indicators
        ],
        "warnings": [t["urgent"]] if a.level == "urgent" else [],
        "missing": a.missing,
        "notes": a.notes,
        "sources": a.sources,
    }


# ── leer el mensaje del padre ────────────────────────────────────────────────────────────
# 16-sep-2026. Hasta hoy la curva sólo se calculaba en la página: en el chat, «¿qué percentil
# tiene mi niña de 8 meses que pesa 7 kg?» contestaba «no puedo decirte el percentil exacto»
# teniendo delante el sexo, la edad y el peso. Las dosis y las vacunas ya leen el mensaje y
# contestan de su tabla; esto hace lo mismo con la de la OMS.

#: Las cifras arábigo-índicas y devanagari, que es lo que sale de un teclado árabe o hindi.
DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹०१२३४५६७८९", "01234567890123456789" + "0123456789")

WEIGHT = re.compile(
    r"(\d{1,3}(?:[.,]\d)?)\s*"
    r"(?:(?:kg|kilos?|kilogramos?|kgs|quilos?)\b"
    r"|кг|килограмм\w*|кило\w*"
    r"|كيلوغرام|كيلوجرام|كيلو|كجم|كغ"
    r"|किलोग्राम|किलो|किग्रा)",
    re.I,
)

#: La talla en centímetros, y también en metros («mide 1,05 m»), que es como se dice a partir
#: del año en castellano, francés y portugués.
HEIGHT_CM = re.compile(
    r"(\d{2,3}(?:[.,]\d)?)\s*"
    r"(?:cm\b|cms\b|cent[íi]metros?|centim[eè]tres?|zentimeter|см|سم|سنتيمتر|सेमी|सेंटीमीटर)",
    re.I,
)
HEIGHT_M = re.compile(
    r"\b([01][.,]\d{1,2})\s*(?:m\b|metros?|m[èe]tres?|meter\b|м\b|متر|मीटर)",
    re.I,
)

#: El sexo, que es lo único sin lo que no hay percentil: la curva de una niña no es la de un
#: niño. Palabras enteras, con prefijo donde la lengua declina («дочь/дочка», «बेटी/बेटे»).
_FEMALE = re.compile(
    r"\b(?:ni[ñn]a|nena|hija|chica|muchacha|girl|daughter|fille|m[äa]dchen|tochter"
    r"|menina|filha|garota)\b|дочь|доч[кеи]\w*|девочк\w*|بنتي|ابنتي|طفلتي|بنت"
    r"|बेटी|लड़की|बच्ची",
    re.I,
)
_MALE = re.compile(
    r"\b(?:ni[ñn]o|nene|hijo|chico|muchacho|var[óo]n|boy|son|gar[çc]on|junge|sohn"
    r"|menino|filho|garoto)\b|сын\w*|мальчик\w*|ابني|ولدي|طفلي|ولد"
    r"|बेटा|बेटे|लड़का|बच्चा",
    re.I,
)


def _number(m: re.Match[str] | None, factor: float = 1.0) -> float | None:
    return round(float(m.group(1).replace(",", ".")) * factor, 1) if m else None


def measurements(text: str) -> tuple[str | None, float | None, float | None]:
    """(sexo, peso en kg, talla en cm) tal y como vienen escritos en el mensaje.

    La edad NO se lee aquí: la saca el triaje, que ya la entiende en ocho lenguas y en meses,
    semanas y años, y es la misma que usan las dosis."""
    t = text.translate(DIGITS)
    female, male = _FEMALE.search(t), _MALE.search(t)
    sex = None
    if female and not male:
        sex = "f"
    elif male and not female:
        sex = "m"
    elif female and male:  # las dos palabras en la misma frase: manda la primera
        sex = "f" if female.start() < male.start() else "m"
    cm = _number(HEIGHT_CM.search(t))
    if cm is None:
        cm = _number(HEIGHT_M.search(t), 100)
    return sex, _number(WEIGHT.search(t)), cm


# ── la respuesta escrita, sin modelo ─────────────────────────────────────────────────────
#: Las frases que rodean a los números. Viven aquí, con LABELS, porque las usan el chat,
#: Telegram y el agente de ACP, y ninguno de los tres pasa por el sitio.
SENTENCES: dict[str, dict[str, str]] = {
    "en": {
        "head": "According to the WHO growth standards ({who}, {age}):",
        "line": "• {label}: {value} → {percentile}th percentile (z {z}), {flag}.",
        "girl": "girl",
        "boy": "boy",
        "ask_height": "Tell me the height too and I can also work out weight for height.",
        "curve": "One measurement says little on its own: what matters is the curve over time, "
        "and your paediatrician has it.",
        "source": "Source: {sources}.",
        "see": "⚠️ {warning} See a doctor soon.",
    },
    "es": {
        "head": "Según los patrones de crecimiento de la OMS ({who}, {age}):",
        "line": "• {label}: {value} → percentil {percentile} (z {z}), {flag}.",
        "girl": "niña",
        "boy": "niño",
        "ask_height": "Dime también la talla y calculo el peso para la talla.",
        "curve": "Un solo dato dice poco: lo que importa es la curva a lo largo del tiempo, y esa "
        "la tiene tu pediatra.",
        "source": "Fuente: {sources}.",
        "see": "⚠️ {warning} Consulta con un médico pronto.",
    },
    "fr": {
        "head": "D'après les standards de croissance de l'OMS ({who}, {age}) :",
        "line": "• {label} : {value} → {percentile}e percentile (z {z}), {flag}.",
        "girl": "fille",
        "boy": "garçon",
        "ask_height": "Donnez-moi aussi la taille et je calcule le poids pour la taille.",
        "curve": "Une seule mesure dit peu de chose : ce qui compte est la courbe dans le temps, "
        "et votre pédiatre l'a.",
        "source": "Source : {sources}.",
        "see": "⚠️ {warning} Consultez un médecin rapidement.",
    },
    "de": {
        "head": "Nach den WHO-Wachstumsstandards ({who}, {age}):",
        "line": "• {label}: {value} → {percentile}. Perzentile (z {z}), {flag}.",
        "girl": "Mädchen",
        "boy": "Junge",
        "ask_height": "Nennen Sie mir auch die Größe, dann berechne ich Gewicht für Größe.",
        "curve": "Ein einzelner Wert sagt wenig: Es zählt die Kurve über die Zeit, und die hat "
        "Ihre Kinderärztin oder Ihr Kinderarzt.",
        "source": "Quelle: {sources}.",
        "see": "⚠️ {warning} Suchen Sie bald ärztlichen Rat.",
    },
    "ru": {
        "head": "По стандартам роста ВОЗ ({who}, {age}):",
        "line": "• {label}: {value} → {percentile}-й перцентиль (z {z}), {flag}.",
        "girl": "девочка",
        "boy": "мальчик",
        "ask_height": "Скажите ещё рост, и я посчитаю вес по росту.",
        "curve": "Одно измерение говорит мало: важна кривая во времени, и она есть у вашего "
        "педиатра.",
        "source": "Источник: {sources}.",
        "see": "⚠️ {warning} Покажите ребёнка врачу в ближайшее время.",
    },
    "ar": {
        "head": "وفق معايير النمو لمنظمة الصحة العالمية ({who}، {age}):",
        "line": "• {label}: {value} ← المئين {percentile} (z {z})، {flag}.",
        "girl": "بنت",
        "boy": "ولد",
        "ask_height": "أخبرني بالطول أيضا وأحسب الوزن حسب الطول.",
        "curve": "قياس واحد لا يكفي: المهم هو المنحنى عبر الوقت، وهو موجود عند طبيب الأطفال.",
        "source": "المصدر: {sources}.",
        "see": "⚠️ {warning} راجع طبيبا قريبا.",
    },
    "pt": {
        "head": "Segundo os padrões de crescimento da OMS ({who}, {age}):",
        "line": "• {label}: {value} → percentil {percentile} (z {z}), {flag}.",
        "girl": "menina",
        "boy": "menino",
        "ask_height": "Diga-me também a altura e calculo o peso para a altura.",
        "curve": "Uma única medida diz pouco: o que importa é a curva ao longo do tempo, e o seu "
        "pediatra tem-na.",
        "source": "Fonte: {sources}.",
        "see": "⚠️ {warning} Consulte um médico em breve.",
    },
    "hi": {
        "head": "डब्ल्यूएचओ के ग्रोथ स्टैंडर्ड के अनुसार ({who}, {age}):",
        "line": "• {label}: {value} → {percentile}वाँ पर्सेंटाइल (z {z}), {flag}।",
        "girl": "बच्ची",
        "boy": "बच्चा",
        "ask_height": "लंबाई भी बताइए तो मैं लंबाई के हिसाब से वजन भी निकाल दूँगा।",
        "curve": "एक बार का माप बहुत कुछ नहीं कहता: मायने रखता है समय के साथ का वक्र, जो आपके "
        "बाल रोग विशेषज्ञ के पास होता है।",
        "source": "स्रोत: {sources}।",
        "see": "⚠️ {warning} जल्द किसी डॉक्टर को दिखाएँ।",
    },
}

#: Cómo se dice la edad en cada lengua: sólo meses y años, que es lo que hace falta aquí.
_AGE_WORDS: dict[str, tuple[str, str]] = {
    "en": ("months", "years"),
    "es": ("meses", "años"),
    "fr": ("mois", "ans"),
    "de": ("Monate", "Jahre"),
    "ru": ("мес.", "лет"),
    "ar": ("شهرا", "سنوات"),
    "pt": ("meses", "anos"),
    "hi": ("महीने", "साल"),
}


def _age_text(age_months: float, lang: str) -> str:
    meses, anios = _AGE_WORDS.get(lang, _AGE_WORDS["en"])
    if age_months < 24:
        return f"{age_months:g} {meses}"
    return f"{age_months / 12:g} {anios}"


def _value_text(i: Indicator) -> str:
    """Lo medido, con su unidad: kg para el peso, cm para la talla, nada para el IMC."""
    unit = {"wfa": "kg", "wfh": "kg", "lhfa": "cm", "hfa": "cm", "bmi": ""}.get(i.name, "")
    return f"{i.value:g} {unit}".strip()


def explain(a: Assessment, lang: str, sex: str, age_months: float) -> str:
    """La valoración escrita para un padre, sin pasar por el modelo."""
    t = LABELS.get(lang, LABELS["en"])
    s = SENTENCES.get(lang, SENTENCES["en"])
    who = s["girl"] if sex.lower().startswith("f") else s["boy"]
    partes = [s["head"].format(who=who, age=_age_text(age_months, lang))]
    for i in a.indicators:
        partes.append(
            s["line"].format(
                label=t[i.name],
                value=_value_text(i),
                percentile=f"{i.percentile:g}",
                z=f"{i.z:g}".replace("-", "−"),
                flag=t[i.flag],
            )
        )
    if a.level == "urgent":
        partes.append(s["see"].format(warning=t["urgent"]))
    if "height" in a.missing:
        partes.append(s["ask_height"])
    partes.append(s["curve"])
    partes.append(s["source"].format(sources="; ".join(a.sources)))
    return "\n".join(partes)
