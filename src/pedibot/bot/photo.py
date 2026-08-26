"""Photo check limited to WARNING SIGNS (idea I-10b). Never a diagnosis.

The vision model is asked only whether three signs from the SEUP emergency list are visible:
non-blanching spots (petechiae/purpura), blue/grey lips or skin (cyanosis), swollen lips/eyelids.
Output is a fixed JSON; the wording shown to the parent is ours, sourced, and ends in "go to the
emergency department" or "I can't tell you what it is — ask your paediatrician"."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

VISION_SYSTEM = (
    "You look at a photo of a child's skin, lips or face and report ONLY whether these warning "
    "signs are visible: (1) non-blanching red or purple spots (petechiae/purpura), (2) blue or grey "
    "lips or skin (cyanosis), (3) swollen lips, tongue or eyelids. Output ONLY JSON: "
    '{"petechiae":"yes|no|unsure","cyanosis":"yes|no|unsure","swelling":"yes|no|unsure",'
    '"quality":"ok|poor","note":"<=20 words"}. Never name a disease or a cause. If the image is not '
    "skin/face or is too dark or blurry, set quality to poor and everything else to unsure."
)
_JSON = re.compile(r"\{.*\}", re.S)
SOURCE = "SEUP — ¿Debo acudir a urgencias? (signos de alarma: piel, coloración, hinchazón)"


@dataclass
class PhotoResult:
    petechiae: str
    cyanosis: str
    swelling: str
    quality: str
    note: str
    level: str  # emergency | urgent | routine | unsure
    text: str
    cost_usd: float


def parse(raw: str) -> dict[str, str]:
    m = _JSON.search(raw)
    if not m:
        return {}
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}
    ok = ("yes", "no", "unsure")
    return {
        "petechiae": d.get("petechiae") if d.get("petechiae") in ok else "unsure",
        "cyanosis": d.get("cyanosis") if d.get("cyanosis") in ok else "unsure",
        "swelling": d.get("swelling") if d.get("swelling") in ok else "unsure",
        "quality": "poor" if d.get("quality") == "poor" else "ok",
        "note": str(d.get("note", ""))[:160],
    }


def interpret(d: dict[str, str], lang: str, emergency_number: str) -> tuple[str, str]:
    es = lang == "es"
    if not d or d.get("quality") == "poor":
        return "unsure", (
            "No puedo valorar esta foto (poca luz, desenfoque o no se ve la piel). Si dudas, consulta hoy con el pediatra; ante dificultad para respirar, manchas que no desaparecen al presionar o hinchazón de labios, acude a urgencias."
            if es
            else "I can't assess this photo (too dark, blurry, or not skin). If in doubt, see your paediatrician today; with breathing difficulty, spots that don't fade when pressed, or swollen lips, go to the emergency department."
        )
    if d["cyanosis"] == "yes" or d["swelling"] == "yes":
        return "emergency", (
            f"Veo un posible signo de alarma ({'labios o piel azulados' if d['cyanosis'] == 'yes' else 'hinchazón de labios o párpados'}). Según la SEUP, esto requiere atención inmediata: llama al {emergency_number} o acude a urgencias ahora, sobre todo si le cuesta respirar."
            if es
            else f"I can see a possible warning sign ({'blue/grey lips or skin' if d['cyanosis'] == 'yes' else 'swollen lips or eyelids'}). According to the SEUP, this needs immediate care: call {emergency_number} or go to the emergency department now, especially if breathing is difficult."
        )
    if d["petechiae"] == "yes":
        return "urgent", (
            "Veo manchas que podrían no desaparecer al presionar. Haz la prueba del vaso: aprieta un vaso transparente sobre la mancha; si sigue viéndose a través del cristal, según la SEUP hay que acudir a urgencias hoy, sin esperar. No puedo decirte qué la causa."
            if es
            else "I can see spots that may not fade when pressed. Do the glass test: press a clear glass on the spots; if they stay visible through the glass, according to the SEUP you should go to the emergency department today, without waiting. I can't tell you what is causing them."
        )
    if all(d[k] == "no" for k in ("petechiae", "cyanosis", "swelling")):
        return "routine", (
            "No veo en la foto ninguno de los tres signos de alarma que compruebo (manchas que no desaparecen al presionar, coloración azulada, hinchazón de labios). Eso no me dice qué es: una foto no sustituye a la exploración. Si el sarpullido se extiende, hay fiebre alta, o tu hijo está decaído, consulta con el pediatra hoy."
            if es
            else "I don't see any of the three warning signs I check for (non-blanching spots, blue colour, swollen lips). That does not tell you what it is — a photo cannot replace an examination. If the rash spreads, there is high fever, or your child seems unwell, see your paediatrician today."
        )
    return "unsure", (
        "No lo veo claro en esta foto. Si las manchas no desaparecen al presionarlas con un vaso, o hay hinchazón de labios o color azulado, acude a urgencias; si no, consulta hoy con el pediatra."
        if es
        else "I can't tell from this photo. If the spots don't fade when pressed with a glass, or there is lip swelling or blue colour, go to the emergency department; otherwise see your paediatrician today."
    )
