"""PediBot on Telegram: the same Engine, one session per chat (python-telegram-bot, long polling).

Commands: /start, /country XX, /lang <code>, /help. Any other text → engine.ask with the chat's
history. Answers carry 👍/👎 inline buttons (feedback into the ops DB). No personal data stored:
the chat id is hashed into the session token.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from pedibot.bot.answer import SUPPORTED_LANGS, Engine
from pedibot.bot.llm import LLMUnavailable
from pedibot.ops.store import AnswerRecord, OpsStore

_CIT = re.compile(r"\[(\d{1,2})\]")

HELP = {
    "hi": (
        "मैं सिर्फ़ प्रकाशित बाल रोग दिशानिर्देशों से जवाब देता हूँ और हर बात का स्रोत बताता हूँ। "
        "बताइए क्या हो रहा है और बच्चे की उम्र क्या है।\n\n"
        "/country IN — आपातकालीन नंबरों के लिए देश\n/lang en — अंग्रेज़ी\n"
        "/stop — कोई सूचना नहीं (सवाल पूछते रह सकते हैं)\n"
        "यह चिकित्सकीय सलाह नहीं है। आपात स्थिति में अपने देश के नंबर पर कॉल करें।"
    ),
    "pt": (
        "Respondo apenas com diretrizes pediátricas publicadas e digo a fonte em cada frase. "
        "Conte o que está acontecendo e a idade da criança.\n\n"
        "/country BR — país para os números de emergência\n/lang en — inglês\n"
        "/stop — sem avisos (você pode continuar perguntando)\n"
        "Não é aconselhamento médico. Em uma emergência, ligue para o número do seu país."
    ),
    "en": (
        "I answer only from published paediatric guidelines and name the source in every sentence. "
        "Tell me what's happening and your child's age.\n\n"
        "/country ES — set your country for emergency numbers\n/lang es — Spanish\n"
        "/stop — no notices (you can keep asking questions)\n"
        "Not medical advice. In an emergency call your local number."
    ),
    "es": (
        "Respondo solo con guías pediátricas publicadas y nombro la fuente en cada frase. "
        "Cuéntame qué le pasa y la edad.\n\n"
        "/country ES — país para los números de emergencia\n/lang en — inglés\n"
        "/stop — sin avisos (puedes seguir preguntando)\n"
        "No es consejo médico. En una emergencia llama a tu número local."
    ),
    "fr": (
        "Je réponds uniquement à partir de recommandations pédiatriques publiées et je nomme la "
        "source à chaque phrase. Dites-moi ce qui se passe et l'âge de votre enfant.\n\n"
        "/country FR — pays pour les numéros d'urgence\n/lang en — anglais\n"
        "/stop — plus d'avis (vous pouvez continuer à poser des questions)\n"
        "Ce n'est pas un avis médical. En cas d'urgence, appelez votre numéro local."
    ),
    "de": (
        "Ich antworte ausschließlich aus veröffentlichten kinderärztlichen Leitlinien und nenne "
        "in jedem Satz die Quelle. Sagen Sie mir, was los ist, und wie alt Ihr Kind ist.\n\n"
        "/country DE — Land für die Notrufnummern\n/lang en — Englisch\n"
        "/stop — keine Hinweise mehr (Fragen können Sie weiter stellen)\n"
        "Keine medizinische Beratung. Rufen Sie im Notfall Ihre örtliche Nummer an."
    ),
    "ru": (
        "Я отвечаю только по опубликованным педиатрическим рекомендациям и называю источник в "
        "каждой фразе. Расскажите, что случилось, и сколько лет ребёнку.\n\n"
        "/country RU — страна для номеров экстренных служб\n/lang en — английский\n"
        "/stop — без уведомлений (вопросы задавать можно)\n"
        "Это не медицинская консультация. В экстренной ситуации звоните по местному номеру."
    ),
    "ar": (
        "أجيب فقط من إرشادات طب الأطفال المنشورة وأذكر المصدر في كل جملة. "
        "أخبرني بما يحدث وبعمر طفلك.\n\n"
        "/country SA — البلد لأرقام الطوارئ\n/lang en — الإنجليزية\n"
        "/stop — بدون إشعارات (يمكنك الاستمرار في طرح الأسئلة)\n"
        "هذه ليست استشارة طبية. في الحالات الطارئة اتصل برقمك المحلي."
    ),
}

# What the bot says back when the language changes — in the language it changed to, which is the
# only way the user can tell it worked.
LANG_SET = {
    "en": "Language set to English.",
    "es": "Idioma: español.",
    "fr": "Langue : français.",
    "de": "Sprache: Deutsch.",
    "ru": "Язык: русский.",
    "ar": "اللغة: العربية.",
    "pt": "Idioma: português.",
    "hi": "भाषा: हिन्दी।",
}


@dataclass
class ChatPrefs:
    country: str | None = None
    lang: str | None = None


class TelegramFront:
    """Transport-agnostic core so it can be unit-tested without Telegram."""

    def __init__(
        self,
        engine: Engine,
        ops: OpsStore,
        salt: str = "pedibot-tg",
        max_daily_usd: float | None = None,
    ):
        self.engine = engine
        self.ops = ops
        self.salt = salt
        # El tope de gasto del día. Hasta el 7-sep-2026 **solo existía en el API**: por Telegram
        # se seguía llamando al modelo con el presupuesto agotado, así que el freno de gasto tenía
        # una puerta abierta al lado. Es el mismo número, leído de la misma configuración.
        self.max_daily_usd = max_daily_usd
        self.prefs: dict[int, ChatPrefs] = {}

    def session_for(self, chat_id: int) -> str:
        return "tg_" + hashlib.sha256(f"{self.salt}:{chat_id}".encode()).hexdigest()[:20]

    def handle_command(self, chat_id: int, text: str) -> str | None:
        p = self.prefs.setdefault(chat_id, ChatPrefs())
        cmd, _, arg = text.strip().partition(" ")
        cmd = cmd.lower().split("@")[0]
        if cmd in ("/start", "/help"):
            self.ops.touch_tg_user(chat_id, p.lang, p.country)
            self.ops.set_tg_opt_out(chat_id, False)
            # .get, not [...]: a language without its own help text must fall back, not crash
            return HELP.get(p.lang or "en", HELP["en"])
        if cmd == "/stop":
            self.ops.set_tg_opt_out(chat_id, True)
            return (
                "Listo: no recibirás avisos. Puedes seguir preguntando cuando quieras."
                if (p.lang or "en") == "es"
                else "Done: you will not receive notices. You can still ask questions any time."
            )
        if cmd == "/country":
            arg = arg.strip().upper()[:2]
            if len(arg) == 2:
                p.country = arg
                return f"Country set to {arg}." if (p.lang or "en") == "en" else f"País: {arg}."
            return "Usage: /country ES"
        if cmd == "/lang":
            arg = arg.strip().lower()[:2]
            if arg in SUPPORTED_LANGS:
                p.lang = arg
                return LANG_SET.get(arg, LANG_SET["en"])
            return "Usage: /lang " + " | /lang ".join(SUPPORTED_LANGS)
        return None

    def handle_message(self, chat_id: int, text: str) -> tuple[str, int]:
        """Returns (rendered answer, answer_id)."""
        p = self.prefs.setdefault(chat_id, ChatPrefs())
        session = self.session_for(chat_id)
        self.ops.touch_tg_user(chat_id, p.lang, p.country)
        hist = self.ops.history(session)
        if self.max_daily_usd is not None and self.ops.cost_today_usd() >= self.max_daily_usd:
            a = self.engine.answer_without_model(text, p.country, p.lang, "degraded")
        else:
            try:
                a = self.engine.ask(text, country=p.country, lang=p.lang, history=hist)
            except LLMUnavailable:
                # El modelo no contesta. Antes esto subía hasta `run_polling`, que respondía
                # «Something went wrong on our side» —en inglés, dijera el chat lo que dijera— y
                # tiraba el triaje ya hecho. Se contesta con las guías y la alarma, como la web.
                a = self.engine.answer_without_model(text, p.country, p.lang, "no_model")
        rec = AnswerRecord(
            session=session,
            lang=a.lang,
            country=p.country,
            question=text,
            answer=a.render_debug(),
            level=a.level,
            verification=a.verification,
            chunk_ids=a.chunk_ids,
            prompt_version=a.prompt_version,
            model=a.llm.model if a.llm else None,
            tokens_in=a.llm.tokens_in if a.llm else 0,
            tokens_out=a.llm.tokens_out if a.llm else 0,
            cost_usd=a.llm.cost_usd if a.llm else 0.0,
            latency_ms=0,
            source="telegram",
        )
        answer_id = self.ops.log_answer(rec)
        self.ops.add_turn(session, "user", text)
        self.ops.add_turn(session, "assistant", a.text)
        text = a.render()
        if a.verification == "clarify" and a.options:
            text += "\n\n" + "\n".join(f"• {o}" for o in a.options)
        return text, answer_id

    def feedback(self, chat_id: int, answer_id: int, value: int) -> bool:
        return self.ops.set_feedback(answer_id, self.session_for(chat_id), value)


def run_polling(front: TelegramFront, token: str) -> None:
    """Blocking long-polling loop (production entrypoint: `pedibot telegram`)."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
    from telegram.ext import (
        Application,
        CallbackQueryHandler,
        CommandHandler,
        ContextTypes,
        MessageHandler,
        filters,
    )

    async def on_command(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message and update.message.text and update.effective_chat:
            reply = front.handle_command(update.effective_chat.id, update.message.text)
            if reply:
                await update.message.reply_text(reply)

    async def on_text(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not (update.message and update.message.text and update.effective_chat):
            return
        chat_id = update.effective_chat.id
        await update.message.chat.send_action("typing")
        try:
            text, answer_id = front.handle_message(chat_id, update.message.text)
        except Exception:  # noqa: BLE001
            await update.message.reply_text(
                "Something went wrong on our side. If this is urgent, call your local emergency number."
            )
            return
        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("👍", callback_data=f"fb:{answer_id}:1"),
                    InlineKeyboardButton("👎", callback_data=f"fb:{answer_id}:-1"),
                ]
            ]
        )
        # Telegram messages max 4096 chars
        for i in range(0, len(text), 4000):
            chunk = text[i : i + 4000]
            await update.message.reply_text(
                chunk, reply_markup=kb if i + 4000 >= len(text) else None
            )

    async def on_callback(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        q = update.callback_query
        if not q or not q.data or not update.effective_chat:
            return
        _, aid, val = q.data.split(":")
        ok = front.feedback(update.effective_chat.id, int(aid), int(val))
        await q.answer("Thanks!" if ok else "Not found")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler(["start", "help", "country", "lang", "stop"], on_command))
    app.add_handler(CallbackQueryHandler(on_callback, pattern=r"^fb:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.run_polling(allowed_updates=Update.ALL_TYPES)


def front_from_settings() -> TelegramFront:
    from pedibot.bot.answer import EmergencyNumbers
    from pedibot.bot.drugs import DrugCatalog
    from pedibot.bot.llm import provider_from_settings
    from pedibot.bot.retrieval import Retriever, Synonyms
    from pedibot.bot.triage import Triage
    from pedibot.bot.vaccines import Vaccines
    from pedibot.index.store import Index
    from pedibot.ingest.classify import Taxonomy
    from pedibot.settings import get_settings

    s = get_settings()
    llm = provider_from_settings()
    engine = Engine(
        Retriever(
            Index(s.index_db_path),
            Synonyms(s.config_dir / "synonyms.yaml"),
            llm=llm,
            top_k=s.retrieval_top_k,
            taxonomy=Taxonomy(s.config_dir / "taxonomia.yaml"),
        ),
        Triage(s.config_dir / "red_flags.yaml"),
        llm,
        EmergencyNumbers(s.config_dir / "emergency_numbers.yaml"),
        drugs=DrugCatalog(s.config_dir / "drugs.yaml"),
        vaccines=Vaccines(s.config_dir / "vaccines.yaml"),
    )
    return TelegramFront(engine, OpsStore(s.ops_db_path), max_daily_usd=s.max_daily_llm_usd)
