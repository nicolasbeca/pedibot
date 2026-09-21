"""Una pregunta nueva no arrastra la anterior (21-sep-2026).

El operador hizo diez preguntas seguidas en la misma conversación, cada una de una cosa. El chat
las fue sumando:

    «no deja de llorar y ha vomitado 3 veces»  → Motivo: «Vómitos tras un golpe en la cabeza»
                                                  (el golpe era de la pregunta anterior)
    «¿cuánto Dalsy le doy?»                    → «un bebé de dos meses…» (el de antes)
    «cojea y tiene fiebre»                     → «bebé menor de 3 meses con fiebre»
    «tiene los ojos muy rojos»                 → «si tiene menos de 3 meses…», y la ictericia

La conversación se junta a propósito, y tiene que seguir juntándose: «tiene manchas» y en el
mensaje siguiente «no desaparecen al apretar» es el signo del meningococo contado en dos frases.
Lo que faltaba es saber cuándo el padre ha cambiado de tema. Eso lo decide la misma lectura de
IA que ya lee cada pregunta, mirando el mensaje anterior: si es otro problema, se empieza de
cero. Si no lo sabe, o no contesta, se junta como siempre: una alarma de más es mucho menos grave
que una de menos.
"""

from __future__ import annotations

from test_the_ai_reads_the_question_first import _Dice, _json, _motor

from pedibot.bot.interpret import interpret

CAIDA = [
    {"role": "user", "text": "Mi hijo se ha caído de una silla y le ha salido un chichón"},
    {"role": "assistant", "text": "Vigila las primeras 24 horas."},
]
LLORA = "Mi hijo de dos meses no deja de llorar y ha vomitado 3 veces"


def test_the_reading_says_whether_the_topic_changed() -> None:
    i = interpret(_Dice(_json(new_topic=True)), "otra cosa", previous="lo de antes")
    assert i is not None and i.new_topic is True


def test_without_the_key_it_is_the_same_conversation() -> None:
    i = interpret(_Dice(_json()), "x", previous="lo de antes")
    assert i is not None and i.new_topic is False


def test_without_a_previous_message_there_is_no_topic_to_change() -> None:
    i = interpret(_Dice(_json(new_topic=True)), "x")
    assert i is not None and i.new_topic is False


def test_the_model_sees_both_messages() -> None:
    class Mira(_Dice):
        def complete(self, system, user, temperature=0.2, max_tokens=1500):  # noqa: ANN001, ANN201
            self.visto = user
            return super().complete(system, user, temperature, max_tokens)

    m = Mira(_json())
    interpret(m, "ahora tiene fiebre", previous="se ha caído")
    assert "se ha caído" in m.visto and "ahora tiene fiebre" in m.visto


def test_a_new_problem_does_not_inherit_the_old_alarm() -> None:
    motor, visto = _motor(_json(lang="es", lang_name="Spanish", new_topic=True))
    a = motor.ask(LLORA, lang="es", history=CAIDA)
    assert "golpe" not in (a.banner or "").lower(), a.banner
    assert "caído de una silla" not in visto["redactor"][-1]


def test_the_same_problem_still_joins_the_two_messages() -> None:
    """Golpe, y en el mensaje siguiente vómitos: eso SÍ es el aviso del golpe."""
    motor, _ = _motor(_json(lang="es", lang_name="Spanish", new_topic=False))
    a = motor.ask("ahora ha vomitado dos veces", lang="es", history=CAIDA)
    assert "golpe" in (a.banner or "").lower(), a.banner


def test_if_the_reading_fails_the_conversation_is_joined_as_always() -> None:
    motor, _ = _motor(None)
    a = motor.ask("ahora ha vomitado dos veces", lang="es", history=CAIDA)
    assert "golpe" in (a.banner or "").lower(), a.banner


def test_a_single_word_is_not_off_topic() -> None:
    """«Mi» —el padre pulsó enviar sin querer— recibió «eso no es de PediBot», en inglés."""
    motor, _ = _motor(_json(lang="es", lang_name="Spanish", intent="other", query_en=""))
    a = motor.ask("Mi", lang="es")
    assert a.verification != "off_topic"
