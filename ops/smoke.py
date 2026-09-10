"""Comprobación del sitio vivo después de desplegar.

El watchdog mira `/api/health` cada diez minutos, que dice si el proceso está en pie. Esto es lo
otro: si cada cosa que un padre puede tocar responde, **en los ocho idiomas**. Son dos preguntas
distintas y la segunda no la hacía nadie — un «112» sin comillas en un fichero de datos tuvo el
buscador devolviendo un 500 en inglés sin que ninguna comprobación se enterara (8-sep-2026).

    python3 ops/smoke.py                      # contra https://pedibot.xyz
    python3 ops/smoke.py --base http://127.0.0.1:8601
    python3 ops/smoke.py --ask                # además, una consulta real por idioma (cuesta ~0,005 $)

Sale con código 1 si algo falla, para poder encadenarlo detrás de `deploy.sh`.
"""

from __future__ import annotations

import argparse
import time

import httpx

IDIOMAS = ("en", "es", "fr", "de", "ru", "ar", "pt", "hi")
CABECERAS = {"x-pedibot-client": "test", "content-type": "application/json"}

#: Una pregunta corriente por idioma. Solo con `--ask`, porque cada una llama al modelo.
PREGUNTAS = {
    "en": "my 3-year-old has a fever of 38.5, what should I do?",
    "es": "mi hija de 3 años tiene 38,5 de fiebre, ¿qué hago?",
    "fr": "ma fille de 3 ans a 38,5 de fièvre, que faire ?",
    "de": "meine 3-jährige Tochter hat 38,5 Fieber, was soll ich tun?",
    "ru": "у моей дочери 3 года температура 38,5, что делать?",
    "ar": "ابنتي عمرها 3 سنوات وحرارتها 38.5، ماذا أفعل؟",
    "pt": "minha filha de 3 anos está com 38,5 de febre, o que faço?",
    "hi": "मेरी 3 साल की बेटी को 38.5 बुखार है, क्या करूँ?",
}

PAGINAS = (
    "/", "/es", "/fr", "/de", "/ru", "/ar", "/pt", "/hi",
    "/dose", "/vaccines", "/guides", "/emergency", "/legal", "/support",
    "/kit", "/diary", "/sources", "/llms.txt", "/rss.xml", "/robots.txt",
    "/sitemap-index.xml",
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://pedibot.xyz")
    ap.add_argument("--ask", action="store_true", help="además, una consulta real por idioma")
    a = ap.parse_args()
    base, fallos = a.base.rstrip("/"), []

    def pide(metodo: str, ruta: str, **kw: object) -> tuple[bool, object, object]:
        # Un reintento para los fallos de RED, no para los códigos de error. Esto se lanza
        # inmediatamente después de reiniciar el API, y la primera petición se cruza a veces con
        # el arranque: el 9-sep-2026 dio un `RemoteProtocolError` en un idioma suelto que a la
        # segunda estaba perfecto. Un comprobador que avisa en falso se acaba ignorando, que es
        # justo lo que no puede pasarle a éste. Un 500 o un 404 NO se reintentan: eso no es un
        # hipo, es el fallo que se busca.
        ultimo: object = "?"
        for intento in (1, 2):
            try:
                r = httpx.request(metodo, base + ruta, headers=CABECERAS, timeout=90, **kw)  # type: ignore[arg-type]
                if r.status_code != 200:
                    return False, r.status_code, None
                tipo = r.headers.get("content-type", "")
                return True, 200, r.json() if tipo.startswith("application/json") else r.text
            except Exception as e:  # noqa: BLE001 — un fallo de red es un fallo del sitio
                ultimo = type(e).__name__
                if intento == 1:
                    time.sleep(2)
        return False, ultimo, None

    ok, code, salud = pide("GET", "/api/health")
    print(f"salud: {salud if ok else code}")
    if not ok:
        fallos.append(("/api/health", code))

    for nombre, plantilla in (
        ("drugs", "/api/drugs?lang={lg}"),
        ("vaccines", "/api/vaccines?country=ES&age_months=3&lang={lg}"),
        ("checklist", "/api/checklist?lang={lg}"),
        ("ors", "/api/ors?age_months=24&vomiting=true&lang={lg}"),
    ):
        linea = []
        for lg in IDIOMAS:
            ok, code, cuerpo = pide("GET", plantilla.format(lg=lg))
            # una respuesta vacía cuenta como fallo: el 200 no dice nada por sí solo
            bien = ok and bool(cuerpo)
            if not bien:
                fallos.append((f"{nombre}[{lg}]", code))
            linea.append(f"{lg}:{'ok' if bien else code}")
        print(f"{nombre:10} " + "  ".join(str(x) for x in linea))

    linea = []
    for lg in IDIOMAS:
        ok, code, cuerpo = pide(
            "POST", "/api/dose", json={"drug": "paracetamol", "weight_kg": 14, "lang": lg}
        )
        bien = bool(ok and isinstance(cuerpo, dict) and cuerpo.get("mg") and cuerpo.get("ml_by_form"))
        if not bien:
            fallos.append((f"dose[{lg}]", code))
        linea.append(f"{lg}:{'ok' if bien else code}")
    print("dose       " + "  ".join(str(x) for x in linea))

    # el fármaco que no es para este niño: la respuesta NO puede traer una cifra
    ok, code, cuerpo = pide(
        "POST", "/api/dose", json={"drug": "ibuprofen", "weight_kg": 5, "age_months": 2, "lang": "en"}
    )
    seguro = bool(
        ok
        and isinstance(cuerpo, dict)
        and cuerpo.get("refer") is True
        and cuerpo.get("mg") is None
        and cuerpo.get("ml_by_form") == []
    )
    print(f"dose(refer, sin cifra): {'ok' if seguro else 'MAL ' + str(code)}")
    if not seguro:
        fallos.append(("dose refer", code))

    malas = [p for p in PAGINAS if not pide("GET", p)[0]]
    print(f"páginas: {len(PAGINAS) - len(malas)}/{len(PAGINAS)}")
    fallos += [(p, "no responde") for p in malas]

    if a.ask:
        linea = []
        for lg, q in PREGUNTAS.items():
            ok, code, cuerpo = pide("POST", "/api/ask", json={"question": q})
            bien = bool(ok and isinstance(cuerpo, dict) and cuerpo.get("lang") == lg)
            if not bien:
                fallos.append((f"ask[{lg}]", code if not ok else f"contestó en {cuerpo.get('lang') if isinstance(cuerpo, dict) else '?'}"))
            linea.append(f"{lg}:{'ok' if bien else 'MAL'}")
        print("ask        " + "  ".join(linea))

    print()
    if fallos:
        print(f"FALLOS: {len(fallos)}")
        for f in fallos:
            print("   ", f)
    else:
        print("todo en pie")
    # La firma del final. Un código de salida no distingue «he mirado y está mal» de «me he
    # muerto por el camino»: el 10-sep-2026 un choque de OpenSSL en Windows mató el proceso antes
    # de que corriera ningún `except`, el sistema devolvió 1, y el despliegue lo contó como que el
    # sitio respondía mal — estando perfecto. Un proceso que se muere no deja escrito por qué, así
    # que la señal tiene que ser algo que sólo se escribe al llegar hasta aquí.
    print(f"{FIRMA} fallos={len(fallos)}")
    return 1 if fallos else 0


#: La firma que `deploy.sh` busca para saber que la comprobación llegó al final. Si no está, no
#: se ha comprobado nada, diga lo que diga el código de salida.
FIRMA = "SMOKE-FIN"

#: Lo que significa cada código de salida. `deploy.sh` los distingue, y tiene que hacerlo:
#: «he mirado y está mal» pide arreglar el sitio, «no he podido mirar» pide arreglar esto —y
#: saber que el despliegue ha ido a ciegas.
OK, SITIO_MAL, NO_PUDE = 0, 1, 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as e:  # noqa: BLE001 — cualquier cosa que impida comprobar
        # Incluye lo que no es un fallo del sitio: sin red, sin certificados, una biblioteca que
        # no carga. El 10-sep-2026 fue un choque de OpenSSL en Windows y el despliegue lo contó
        # como que el sitio respondía mal.
        print(f"NO HE PODIDO COMPROBAR: {type(e).__name__}: {e}")
        raise SystemExit(NO_PUDE) from e
