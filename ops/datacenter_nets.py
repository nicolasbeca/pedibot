"""Rehace config/datacenter_nets.txt: las redes que anuncian los centros de datos (15-oct-2026).

El recuento de visitas descarta lo que llega desde aquí (src/pedibot/ops/report.py): el escáner de
enlaces de Outlook cargaba la página entera desde Microsoft y contaba como persona. Una casa no
navega desde la nube. Fuera de la lista, a propósito: Apple (Private Relay, AS714 y AS36183) y
Cloudflare (WARP, AS13335), porque por ellas pasan personas de verdad.

    uv run python ops/datacenter_nets.py

Datos de RIPEstat (announced-prefixes), públicos y sin clave. Las redes cambian poco: con
rehacerlo cuando el panel vuelva a ver un pico raro basta.
"""

from __future__ import annotations

import ipaddress
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "config" / "datacenter_nets.txt"

#: Los que vimos en el registro de la semana del 8 al 15-oct, más los grandes de siempre.
ASNS = {
    8075: "Microsoft",
    14618: "Amazon",
    16509: "Amazon",
    396982: "Google Cloud",
    14061: "DigitalOcean",
    24940: "Hetzner",
    16276: "OVH",
    63949: "Akamai Connected Cloud (Linode)",
    31898: "Oracle Cloud",
    132203: "Tencent Cloud",
    45090: "Tencent Cloud",
    137718: "Volcano Engine (ByteDance)",
    45102: "Alibaba Cloud",
    20473: "Vultr",
    400940: "Railway",
}


def _prefijos(asn: int) -> list[str]:
    url = f"https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS{asn}"
    with urllib.request.urlopen(url, timeout=60) as r:
        data = json.load(r)
    return [p["prefix"] for p in data["data"]["prefixes"]]


def main() -> int:
    lineas = [
        "# Redes de centros de datos: una visita desde aquí no es una persona.",
        "# Generado por ops/datacenter_nets.py desde RIPEstat. No editar a mano.",
    ]
    total = 0
    for asn, nombre in ASNS.items():
        todos = _prefijos(asn)
        nets = sorted(
            ipaddress.collapse_addresses(ipaddress.ip_network(p) for p in todos if ":" not in p),
            key=lambda n: int(n.network_address),
        )
        v6 = sorted(
            ipaddress.collapse_addresses(ipaddress.ip_network(p) for p in todos if ":" in p),
            key=lambda n: int(n.network_address),
        )
        lineas.append(f"# AS{asn} {nombre}: {len(nets)} IPv4, {len(v6)} IPv6")
        lineas += [str(n) for n in nets + v6]
        total += len(nets) + len(v6)
        print(f"AS{asn} {nombre}: {len(nets) + len(v6)}", file=sys.stderr)
    OUT.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"{total} redes en {OUT.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
