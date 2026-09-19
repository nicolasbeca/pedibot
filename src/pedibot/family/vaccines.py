"""El calendario de vacunas de un hijo, con fechas de verdad (19-sep-2026).

Hasta hoy el sitio sabía decir «a los 4 meses toca la segunda de hexavalente». Teniendo la fecha
de nacimiento, eso se convierte en «el 12 de julio de 2024», que es lo único que se puede apuntar
en el calendario del teléfono y lo que van a leer los recordatorios de la app (D-A3 de `APP.md`).

No hay ni un dato nuevo aquí: es el calendario oficial del país —el mismo de `config/vaccines.yaml`
que ya usa el chat— con la fecha de nacimiento sumada. Y tres decisiones que no son técnicas:

- **Lo que ya pasó se marca, no se esconde.** Un padre que llega tarde a una vacuna es justo
  quien más necesita verla.
- **La campaña estacional se queda sin fecha.** «Cada otoño» no es un día del año; ponerle uno
  sería inventárselo, y este proyecto no inventa fechas de calendarios oficiales.
- **La tolerancia es la del propio calendario** —mes y medio en lactantes, seis meses a partir de
  los dos años—, la misma que usa el chat. Una segunda ventana inventada para esta pantalla
  acabaría diciendo cosas distintas en dos sitios del mismo sitio.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from pedibot.bot.growth import DAYS_PER_MONTH
from pedibot.bot.vaccines import Vaccines
from pedibot.settings import ROOT

_VACUNAS: Vaccines | None = None


def _tabla() -> Vaccines:
    global _VACUNAS
    if _VACUNAS is None:
        _VACUNAS = Vaccines(ROOT / "config" / "vaccines.yaml")
    return _VACUNAS


def _cuando(nacimiento: dt.date, meses: float) -> dt.date:
    """La fecha en que el niño cumple esa edad.

    Para los meses enteros del calendario se suman meses de verdad —el 12 de marzo más doce
    meses es el 12 de marzo del año siguiente, no «365 días después»—, porque es así como lo
    lee un padre y como lo cita la cartilla. Sólo se cae en días cuando la edad trae media.
    """
    entero = int(meses)
    if meses != entero:
        return nacimiento + dt.timedelta(days=round(meses * DAYS_PER_MONTH))
    anio = nacimiento.year + (nacimiento.month - 1 + entero) // 12
    mes = (nacimiento.month - 1 + entero) % 12 + 1
    dia = min(
        nacimiento.day,
        [
            31,
            29 if anio % 4 == 0 and (anio % 100 or anio % 400 == 0) else 28,
            31,
            30,
            31,
            30,
            31,
            31,
            30,
            31,
            30,
            31,
        ][mes - 1],
    )
    return dt.date(anio, mes, dia)


def schedule_for_child(
    child: dict[str, Any],
    lang: str = "en",
    today: dt.date | None = None,
    vaccines: Vaccines | None = None,
) -> list[dict[str, Any]]:
    """Las citas del calendario de su país, cada una con su fecha y en qué estado está.

    Estados: `past` (ya tocó), `due` (toca ahora, dentro de la tolerancia del calendario),
    `future` (aún no) y `seasonal` (campaña anual, sin fecha).
    """
    tabla = vaccines or _tabla()
    pais = tabla.resolve_country(str(child.get("country") or "") or None)
    if not pais or not child.get("birth_date"):
        return []
    hoy = today or dt.date.today()
    nacimiento = dt.date.fromisoformat(str(child["birth_date"]))
    edad_meses = max(0.0, (hoy - nacimiento).days / DAYS_PER_MONTH)
    tolerancia = 1.5 if edad_meses < 24 else 6.0

    fuera: list[dict[str, Any]] = []
    for slot in tabla.schedule(pais, lang):
        if slot.every_year:
            fuera.append(
                {
                    "age_months": slot.age_months,
                    "label": slot.label,
                    "vaccines": list(slot.vaccines),
                    "date": None,
                    "every_year": True,
                    "state": "seasonal",
                }
            )
            continue
        cuando = _cuando(nacimiento, slot.age_months)
        if abs(slot.age_months - edad_meses) <= tolerancia:
            estado = "due"
        elif cuando <= hoy:
            estado = "past"
        else:
            estado = "future"
        fuera.append(
            {
                "age_months": slot.age_months,
                "label": slot.label,
                "vaccines": list(slot.vaccines),
                "date": cuando.isoformat(),
                "every_year": False,
                "state": estado,
            }
        )
    return fuera


def next_appointment(citas: list[dict[str, Any]]) -> dict[str, Any] | None:
    """La siguiente cita: la que toca ahora si hay alguna, y si no, la primera que viene."""
    ahora = [c for c in citas if c["state"] == "due"]
    if ahora:
        return ahora[0]
    futuras = sorted(
        (c for c in citas if c["state"] == "future" and c["date"]), key=lambda c: c["date"]
    )
    return futuras[0] if futuras else None


def _escapa_ics(texto: str) -> str:
    """Las cuatro cosas que un `.ics` no admite tal cual, según el RFC 5545."""
    # Escrito con la herramienta de edición y no con un heredoc: es la quinta vez este mes que
    # un heredoc se come una barra invertida, y aquí eso convierte «Hepatitis B, 1.ª dosis» en
    # dos campos distintos del calendario (LESSONS L61).
    return texto.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _pliega(linea: str) -> str:
    """Una línea de `.ics` no pasa de 75 octetos: lo que sobra sigue en la siguiente con un
    espacio delante. Sin esto, un nombre de vacuna largo rompe el fichero en la mitad de los
    calendarios."""
    crudo = linea.encode("utf-8")
    if len(crudo) <= 75:
        return linea
    trozos, actual = [], b""
    for caracter in linea:
        b = caracter.encode("utf-8")
        if len(actual) + len(b) > (75 if not trozos else 74):
            trozos.append(actual.decode("utf-8"))
            actual = b""
        actual += b
    trozos.append(actual.decode("utf-8"))
    return "\r\n ".join(trozos)


def to_ics(child: dict[str, Any], citas: list[dict[str, Any]]) -> str:
    """Las citas que vienen, en el formato que entiende cualquier calendario (19-sep-2026).

    La app avisará con una notificación local; un navegador no puede programar un aviso para
    dentro de cuatro meses. Esto es lo equivalente que la web sí puede hacer: darle el dato al
    calendario del propio teléfono y que avise él.

    Va sólo lo que queda por delante —una cita de hace dos años en el calendario de alguien no
    es un recordatorio— y cada una con un identificador que sale del hijo y de la fecha, para
    que volver a descargarlo no duplique nada.
    """
    nombre = str(child.get("name") or "").strip()
    lineas = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//PediBot//Calendario de vacunas//ES",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    for c in citas:
        if not c.get("date") or c["state"] not in ("due", "future"):
            continue
        dia = str(c["date"]).replace("-", "")
        siguiente = (dt.date.fromisoformat(str(c["date"])) + dt.timedelta(days=1)).strftime(
            "%Y%m%d"
        )
        uid = f"pedibot-{child.get('id', 0)}-{dia}@pedibot.xyz"
        titulo = f"{nombre}: {', '.join(c['vaccines'])}" if nombre else ", ".join(c["vaccines"])
        lineas += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{dt.datetime.now(dt.UTC).strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART;VALUE=DATE:{dia}",
            f"DTEND;VALUE=DATE:{siguiente}",
            _pliega(f"SUMMARY:{_escapa_ics(titulo)}"),
            _pliega(f"DESCRIPTION:{_escapa_ics(str(c['label']))} — pedibot.xyz"),
            # Un aviso el día anterior por la mañana: una vacuna se pide con antelación en casi
            # todos los centros de salud.
            "BEGIN:VALARM",
            "TRIGGER:-P1D",
            "ACTION:DISPLAY",
            _pliega(f"DESCRIPTION:{_escapa_ics(titulo)}"),
            "END:VALARM",
            "END:VEVENT",
        ]
    lineas.append("END:VCALENDAR")
    return "\r\n".join(lineas) + "\r\n"
