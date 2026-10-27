"""Enviar un correo desde pedibot.ai@gmail.com por SMTP (27-oct-2026).

El conector de Gmail cambia cada enlace por una redirección google.com/url que caduca a las 24 h
y luego enseña un aviso de Google: el destinatario la recibía así. Por SMTP los enlaces salen tal
cual, y Gmail guarda el correo en «Enviados» igual.

Se envía DESDE EL SERVIDOR: en el PC, el AVG se mete en el SMTP (587 y 465), añade «analizado
por AVG» al pie y rompe el certificado. La contraseña de aplicación vive fuera del repositorio,
en /root/.pedibot/smtp del servidor (dirección en la primera línea, contraseña en la segunda).

    ssh -i ~/.ssh/multibot_hetzner_auto root@46.225.74.13 \\
      'python3 /opt/pedibot/ops/correo.py --to x@y.org --subject "…" --body -' < cuerpo.txt
    ... --reply-to-id "<id@mail>"   # contestar en hilo
"""

from __future__ import annotations

import argparse
import smtplib
import ssl
import sys
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

CREDENCIALES = Path.home() / ".pedibot" / "smtp"


def enviar(to: str, subject: str, body: str, cc: str = "", reply_to_id: str = "") -> str:
    usuario, clave = CREDENCIALES.read_text(encoding="utf-8").split()[:2]
    msg = EmailMessage()
    msg["From"] = f"Nicolas Beca <{usuario}>"
    msg["To"] = to
    if cc:
        msg["Cc"] = cc
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="gmail.com")
    if reply_to_id:
        msg["In-Reply-To"] = reply_to_id
        msg["References"] = reply_to_id
    msg.set_content(body)
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as s:
        s.starttls(context=ssl.create_default_context())
        s.login(usuario, clave)
        s.send_message(msg)
    return msg["Message-ID"]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--to", required=True)
    p.add_argument("--subject", required=True)
    p.add_argument("--body", required=True, help="fichero con el cuerpo en texto plano, o - para la entrada estándar")
    p.add_argument("--cc", default="")
    p.add_argument("--reply-to-id", default="")
    a = p.parse_args()
    body = sys.stdin.read() if a.body == "-" else Path(a.body).read_text(encoding="utf-8")
    print(enviar(a.to, a.subject, body, a.cc, a.reply_to_id))


if __name__ == "__main__":
    main()
