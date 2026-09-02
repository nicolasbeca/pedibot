"""Photo check limited to WARNING SIGNS (idea I-10b). Never a diagnosis.

The vision model is asked only whether three signs from the SEUP emergency list are visible:
non-blanching spots (petechiae/purpura), blue/grey lips or skin (cyanosis), swollen lips/eyelids.
Output is a fixed JSON; the wording shown to the parent is ours, sourced, and ends in "go to the
emergency department" or "I can't tell you what it is — ask your paediatrician"."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from pedibot.bot.strings import tool_strings

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
    T = tool_strings(lang)
    if not d or d.get("quality") == "poor":
        return "unsure", T["photo_poor"]
    if d["cyanosis"] == "yes" or d["swelling"] == "yes":
        sign = T["photo_sign_cyanosis"] if d["cyanosis"] == "yes" else T["photo_sign_swelling"]
        return "emergency", T["photo_emergency"].format(sign=sign, number=emergency_number)
    if d["petechiae"] == "yes":
        return "urgent", T["photo_petechiae"]
    if all(d[k] == "no" for k in ("petechiae", "cyanosis", "swelling")):
        return "routine", T["photo_clear"]
    return "unsure", T["photo_unsure"]
