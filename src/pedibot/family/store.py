"""La base de las cuentas de familia (19-sep-2026).

Pedida por el operador: «quiero que puedas darte de alta tanto en web como en app para guardar
datos de tus hijos… y poder ir apuntando por nombre de hijo y tener una curva de crecimiento y
tener la edad de cada hijo, para que cuando pregunten cuáles son las vacunas que le tocan a
Laura, les diga cuáles le tocan sabiendo su fecha de nacimiento». Y el cómo lo decidió él
también: **correo y contraseña**, y la cuenta **opcional**.

Las cuatro cosas que decide este fichero y que costaría mucho cambiar después:

1. **Vive en su propia base**, `data/pedibot_familias.db`. La de operación abre su fichero
   diciendo «no personal data» y lo cumple; ésta guarda justo lo contrario. Separarlas es lo que
   permite que aquella frase siga siendo verdad, y da a ésta su propio respaldo y su propio
   borrado.
2. **La contraseña no se guarda.** Se guarda un `scrypt` con sal propia por cuenta. Es de la
   biblioteca estándar: meter una dependencia para esto sería cambiar algo que no se puede
   auditar por algo que sí.
3. **Cada consulta pide de quién es.** No existe `child(id)`; existe `child(user_id, id)`. Un
   fallo de autorización no lanza ninguna excepción ni deja ningún rastro en un registro: sólo
   devuelve los datos de otra familia.
4. **Lo que viaja en la cookie no está aquí.** De la sesión se guarda su huella `sha256`, así que
   quien lea esta base no puede hacerse pasar por nadie.

Lo que NO hace, y hay que saberlo: no verifica el correo ni sabe mandar una contraseña olvidada,
porque el proyecto todavía no tiene por dónde enviar correo. El alta funciona en el acto; la
recuperación llega cuando haya un proveedor de envío.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import re
import secrets
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any

_SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    lang TEXT,
    created TEXT NOT NULL,
    last_seen TEXT,
    newsletter INTEGER NOT NULL DEFAULT 0,
    unsub_token TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS children (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    -- la clave de todo esto: con la fecha de nacimiento, la edad se calcula el día que se
    -- pregunta y nunca envejece mal, cosa que «tiene 14 meses» sí hace
    birth_date TEXT NOT NULL,
    sex TEXT,
    country TEXT,
    created TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS children_user ON children(user_id);
CREATE TABLE IF NOT EXISTS measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    child_id INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    weight_kg REAL,
    height_cm REAL,
    head_cm REAL,
    note TEXT
);
CREATE INDEX IF NOT EXISTS measurements_child ON measurements(child_id, date);
-- La cartilla de vacunación: una fila por visita del calendario que ya se puso.
-- La visita se identifica por la EDAD en meses a la que toca, que es lo que el calendario
-- del país nombra y lo único estable: el nombre de la vacuna cambia de un año para otro
-- cuando el ministerio cambia de producto, y la edad no.
CREATE TABLE IF NOT EXISTS doses (
    child_id INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE,
    age_months REAL NOT NULL,
    given_on TEXT,
    created TEXT NOT NULL,
    PRIMARY KEY (child_id, age_months)
);
CREATE INDEX IF NOT EXISTS doses_child ON doses(child_id);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created TEXT NOT NULL,
    last_seen TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_user ON sessions(user_id);
-- Los intentos de entrar, para poder frenarlos. Se guarda la HUELLA de la IP y no la IP,
-- igual que hace la base de operación: para contar diez intentos no hace falta saber de
-- dónde vienen, sólo que vienen del mismo sitio.
CREATE TABLE IF NOT EXISTS login_attempts (
    ip_hash TEXT NOT NULL,
    ts TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS login_attempts_ip ON login_attempts(ip_hash, ts);
"""

#: Lo mínimo para que una contraseña no se adivine en una tarde. No se piden mayúsculas ni
#: símbolos a propósito: esas reglas producen «Pedro2024!» y no protegen de nada.
MIN_PASSWORD = 8
#: Coste del `scrypt`. 2^14 tarda unas décimas de segundo aquí y multiplica por mucho lo que
#: cuesta probar contraseñas a quien se lleve la base.
_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**14, 8, 1

_EMAIL = re.compile(r"^[^@\s]+@[^@\s.]+\.[^@\s]+$")


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds")


def normaliza_email(email: str) -> str:
    return email.strip().lower()


def aplana_nombre(nombre: str) -> str:
    """El nombre como se teclea: sin tildes, sin mayúsculas y sin espacios de sobra.

    «las vacunas que le tocan a laura» y «a Martin» tienen que encontrar a Laura y a Martín. Es
    la misma normalización que usa el triaje para leer al padre.
    """
    base = unicodedata.normalize("NFD", nombre.strip().lower())
    return "".join(c for c in base if not unicodedata.combining(c))


def hash_password(password: str) -> str:
    sal = secrets.token_bytes(16)
    clave = hashlib.scrypt(
        password.encode("utf-8"), salt=sal, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=32
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${sal.hex()}${clave.hex()}"


def check_password(password: str, guardado: str) -> bool:
    try:
        etiqueta, n, r, p, sal, esperado = guardado.split("$")
        if etiqueta != "scrypt":
            return False
        clave = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(sal),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(esperado) // 2,
        )
    except (ValueError, TypeError):
        return False
    # comparación en tiempo constante: comparar con `==` filtra por dónde empieza a diferir
    return secrets.compare_digest(clave.hex(), esperado)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class FamilyStore:
    """Las cuentas, los hijos y sus medidas. Todo método que toque a un hijo pide el `user_id`."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._con() as con:
            con.executescript(_SCHEMA)

    def _con(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        # sin esto, `ON DELETE CASCADE` es un comentario: SQLite lo ignora salvo que se pida
        con.execute("PRAGMA foreign_keys = ON")
        return con

    # ── el alta y la entrada ──────────────────────────────────────────────────────────────────

    def register(self, email: str, password: str, lang: str | None = None) -> int | None:
        """Devuelve el id de la cuenta nueva, o None si ese correo ya estaba."""
        email = normaliza_email(email)
        if not _EMAIL.match(email):
            raise ValueError("correo no válido")
        if len(password) < MIN_PASSWORD:
            raise ValueError(f"la contraseña necesita al menos {MIN_PASSWORD} caracteres")
        with self._con() as con:
            try:
                cur = con.execute(
                    "INSERT INTO users (email, password_hash, lang, created, unsub_token)"
                    " VALUES (?,?,?,?,?)",
                    (email, hash_password(password), lang, _now(), secrets.token_urlsafe(24)),
                )
            except sqlite3.IntegrityError:
                return None
            return int(cur.lastrowid or 0)

    def login(self, email: str, password: str) -> str | None:
        """La contraseña buena devuelve el testigo de sesión; cualquier otra cosa, None."""
        with self._con() as con:
            fila = con.execute(
                "SELECT id, password_hash FROM users WHERE email = ?", (normaliza_email(email),)
            ).fetchone()
        if fila is None:
            # se gasta el mismo tiempo que con una cuenta que sí existe: si no, el reloj dice
            # cuáles de los correos probados están dados de alta
            hash_password(password)
            return None
        if not check_password(password, fila["password_hash"]):
            return None
        return self.open_session(int(fila["id"]))

    def note_attempt(self, ip: str) -> int:
        """Apunta un intento de entrar y devuelve cuántos van en el último cuarto de hora.

        Una contraseña se adivina probando, y probar es gratis si nadie lleva la cuenta. Se
        apuntan TODOS los intentos, no sólo los fallidos: quien prueba mil contraseñas acierta
        alguna, y esa también hay que contarla.
        """
        ahora = dt.datetime.now(dt.UTC)
        huella = hashlib.sha256(f"login:{ip}".encode()).hexdigest()
        desde = (ahora - dt.timedelta(minutes=15)).isoformat(timespec="seconds")
        with self._con() as con:
            con.execute(
                "INSERT INTO login_attempts (ip_hash, ts) VALUES (?,?)",
                (huella, ahora.isoformat(timespec="seconds")),
            )
            # la limpieza va aquí y no en un temporizador: la tabla sólo crece cuando alguien
            # entra, y así no hay un proceso más que vigilar
            con.execute("DELETE FROM login_attempts WHERE ts < ?", (desde,))
            fila = con.execute(
                "SELECT count(*) FROM login_attempts WHERE ip_hash = ? AND ts >= ?",
                (huella, desde),
            ).fetchone()
        return int(fila[0])

    def open_session(self, user_id: int) -> str:
        token = secrets.token_urlsafe(32)
        with self._con() as con:
            con.execute(
                "INSERT INTO sessions (token_hash, user_id, created, last_seen) VALUES (?,?,?,?)",
                (_token_hash(token), user_id, _now(), _now()),
            )
            con.execute("UPDATE users SET last_seen = ? WHERE id = ?", (_now(), user_id))
        return token

    def user_for(self, token: str) -> dict[str, Any] | None:
        """Quién es el dueño de esta cookie, o None si no lo es de nadie."""
        if not token:
            return None
        with self._con() as con:
            fila = con.execute(
                "SELECT u.id, u.email, u.lang, u.newsletter, u.created FROM sessions s"
                " JOIN users u ON u.id = s.user_id WHERE s.token_hash = ?",
                (_token_hash(token),),
            ).fetchone()
            if fila is None:
                return None
            con.execute(
                "UPDATE sessions SET last_seen = ? WHERE token_hash = ?",
                (_now(), _token_hash(token)),
            )
        return {
            "id": int(fila["id"]),
            "email": fila["email"],
            "lang": fila["lang"],
            "newsletter": bool(fila["newsletter"]),
            "created": fila["created"],
        }

    def logout(self, token: str) -> None:
        with self._con() as con:
            con.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))

    def change_password(self, user_id: int, actual: str, nueva: str) -> bool:
        if len(nueva) < MIN_PASSWORD:
            raise ValueError(f"la contraseña necesita al menos {MIN_PASSWORD} caracteres")
        with self._con() as con:
            fila = con.execute(
                "SELECT password_hash FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            if fila is None or not check_password(actual, fila["password_hash"]):
                return False
            con.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(nueva), user_id)
            )
            # cambiar la contraseña cierra las demás sesiones: es la mitad del motivo por el
            # que uno la cambia
            con.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        return True

    # ── los hijos ─────────────────────────────────────────────────────────────────────────────

    def add_child(
        self,
        user_id: int,
        name: str,
        birth_date: str,
        sex: str | None = None,
        country: str | None = None,
    ) -> int:
        nombre = name.strip()
        if not nombre:
            raise ValueError("el nombre no puede estar vacío")
        dt.date.fromisoformat(birth_date)  # que reviente aquí y no al dibujar la curva
        with self._con() as con:
            cur = con.execute(
                "INSERT INTO children (user_id, name, birth_date, sex, country, created)"
                " VALUES (?,?,?,?,?,?)",
                (user_id, nombre, birth_date, sex, country, _now()),
            )
            return int(cur.lastrowid or 0)

    def children(self, user_id: int) -> list[dict[str, Any]]:
        with self._con() as con:
            filas = con.execute(
                "SELECT * FROM children WHERE user_id = ? ORDER BY birth_date", (user_id,)
            ).fetchall()
        return [self._child_dict(f) for f in filas]

    def child(self, user_id: int, child_id: int) -> dict[str, Any] | None:
        with self._con() as con:
            fila = con.execute(
                "SELECT * FROM children WHERE id = ? AND user_id = ?", (child_id, user_id)
            ).fetchone()
        return self._child_dict(fila) if fila else None

    def child_by_name(self, user_id: int, name: str) -> dict[str, Any] | None:
        """El hijo que se llama así, escrito como se teclea. Sin tildes y sin mayúsculas."""
        buscado = aplana_nombre(name)
        if not buscado:
            return None
        for hijo in self.children(user_id):
            if aplana_nombre(hijo["name"]) == buscado:
                return hijo
        return None

    def update_child(self, user_id: int, child_id: int, **campos: Any) -> bool:
        permitidos = {"name", "birth_date", "sex", "country"}
        cambios = {k: v for k, v in campos.items() if k in permitidos}
        if not cambios:
            return False
        if "birth_date" in cambios:
            dt.date.fromisoformat(str(cambios["birth_date"]))
        sets = ", ".join(f"{k} = ?" for k in cambios)
        with self._con() as con:
            cur = con.execute(
                f"UPDATE children SET {sets} WHERE id = ? AND user_id = ?",
                (*cambios.values(), child_id, user_id),
            )
            return cur.rowcount > 0

    def delete_child(self, user_id: int, child_id: int) -> bool:
        with self._con() as con:
            cur = con.execute(
                "DELETE FROM children WHERE id = ? AND user_id = ?", (child_id, user_id)
            )
            return cur.rowcount > 0

    # ── las medidas, que son la curva ─────────────────────────────────────────────────────────

    def add_measurement(
        self,
        user_id: int,
        child_id: int,
        date: str,
        weight_kg: float | None = None,
        height_cm: float | None = None,
        head_cm: float | None = None,
        note: str | None = None,
    ) -> int | None:
        if self.child(user_id, child_id) is None:
            return None  # ni existe, ni es suyo: la misma respuesta para no decir cuál de las dos
        dt.date.fromisoformat(date)
        if weight_kg is None and height_cm is None and head_cm is None:
            raise ValueError("una medida sin ninguna medida no es nada")
        with self._con() as con:
            cur = con.execute(
                "INSERT INTO measurements (child_id, date, weight_kg, height_cm, head_cm, note)"
                " VALUES (?,?,?,?,?,?)",
                (child_id, date, weight_kg, height_cm, head_cm, note),
            )
            return int(cur.lastrowid or 0)

    def measurements(self, user_id: int, child_id: int) -> list[dict[str, Any]]:
        if self.child(user_id, child_id) is None:
            return []
        with self._con() as con:
            filas = con.execute(
                "SELECT id, date, weight_kg, height_cm, head_cm, note FROM measurements"
                " WHERE child_id = ? ORDER BY date, id",
                (child_id,),
            ).fetchall()
        return [dict(f) for f in filas]

    def delete_measurement(self, user_id: int, child_id: int, measurement_id: int) -> bool:
        if self.child(user_id, child_id) is None:
            return False
        with self._con() as con:
            cur = con.execute(
                "DELETE FROM measurements WHERE id = ? AND child_id = ?",
                (measurement_id, child_id),
            )
            return cur.rowcount > 0

    # ── la cartilla ──────────────────────────────────────────────────────────────────────────

    def mark_dose(
        self, user_id: int, child_id: int, age_months: float, given_on: str | None = None
    ) -> bool:
        """Marca como puesta la visita de esa edad. Volver a marcarla sólo cambia la fecha."""
        if self.child(user_id, child_id) is None:
            return False
        if given_on:
            dt.date.fromisoformat(given_on)
        with self._con() as con:
            con.execute(
                "INSERT INTO doses (child_id, age_months, given_on, created) VALUES (?,?,?,?)"
                " ON CONFLICT(child_id, age_months) DO UPDATE SET given_on = excluded.given_on",
                (child_id, float(age_months), given_on, _now()),
            )
        return True

    def unmark_dose(self, user_id: int, child_id: int, age_months: float) -> bool:
        """Desmarcar tiene que ser tan fácil como marcar: aquí se equivoca uno con el dedo."""
        if self.child(user_id, child_id) is None:
            return False
        with self._con() as con:
            cur = con.execute(
                "DELETE FROM doses WHERE child_id = ? AND age_months = ?",
                (child_id, float(age_months)),
            )
            return cur.rowcount > 0

    def doses(self, user_id: int, child_id: int) -> dict[float, str | None]:
        """Edad de la visita → fecha en que se puso (o None si se marcó sin fecha)."""
        if self.child(user_id, child_id) is None:
            return {}
        with self._con() as con:
            filas = con.execute(
                "SELECT age_months, given_on FROM doses WHERE child_id = ? ORDER BY age_months",
                (child_id,),
            ).fetchall()
        return {float(f["age_months"]): f["given_on"] for f in filas}

    # ── el boletín, y las dos cosas que la ley y el sentido común piden ───────────────────────

    def set_newsletter(self, user_id: int, quiere: bool) -> None:
        with self._con() as con:
            con.execute(
                "UPDATE users SET newsletter = ? WHERE id = ?", (1 if quiere else 0, user_id)
            )

    def newsletter_audience(self) -> list[dict[str, Any]]:
        with self._con() as con:
            filas = con.execute(
                "SELECT email, lang, unsub_token FROM users WHERE newsletter = 1 ORDER BY id"
            ).fetchall()
        return [dict(f) for f in filas]

    def unsubscribe(self, token: str) -> bool:
        """La baja va por un enlace que no pide entrar con la contraseña: quien quiere irse no
        tiene por qué acordarse de nada."""
        if not token:
            return False
        with self._con() as con:
            cur = con.execute(
                "UPDATE users SET newsletter = 0 WHERE unsub_token = ? AND newsletter = 1",
                (token,),
            )
            return cur.rowcount > 0

    def export(self, user_id: int) -> dict[str, Any]:
        """Todo lo suyo, en un JSON. Lo nuestro —el hash de la contraseña— no sale: no es suyo
        y no le sirve para nada."""
        with self._con() as con:
            u = con.execute(
                "SELECT email, lang, created, newsletter, unsub_token FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        if u is None:
            return {}
        hijos = []
        for hijo in self.children(user_id):
            hijos.append({**hijo, "measurements": self.measurements(user_id, hijo["id"])})
        return {
            "email": u["email"],
            "lang": u["lang"],
            "created": u["created"],
            "newsletter": bool(u["newsletter"]),
            "unsubscribe": u["unsub_token"],
            "children": hijos,
        }

    def delete_account(self, user_id: int) -> None:
        """Borrar borra. Los hijos y las medidas se van por cascada, y las sesiones también."""
        with self._con() as con:
            con.execute("DELETE FROM users WHERE id = ?", (user_id,))

    # ── ayuda interna ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _child_dict(fila: sqlite3.Row) -> dict[str, Any]:
        hijo = dict(fila)
        hijo.pop("user_id", None)
        return hijo

    def counts(self) -> dict[str, int]:
        """Cuántas cuentas, hijos y medidas hay. **Sólo números.**

        Lo pidió el operador para el panel —«debe aparecer cuántas cuentas se han creado»— y por
        eso devuelve esto y no las filas: el panel se mira en sitios donde alguien puede estar
        mirando por encima del hombro, y estas tablas tienen dentro el nombre de un niño y su
        fecha de nacimiento. Contar no es enseñar.
        """
        with self._con() as con:
            return {
                "accounts": int(con.execute("SELECT count(*) FROM users").fetchone()[0]),
                "children": int(con.execute("SELECT count(*) FROM children").fetchone()[0]),
                "measurements": int(con.execute("SELECT count(*) FROM measurements").fetchone()[0]),
                "newsletter": int(
                    con.execute("SELECT count(*) FROM users WHERE newsletter = 1").fetchone()[0]
                ),
            }
