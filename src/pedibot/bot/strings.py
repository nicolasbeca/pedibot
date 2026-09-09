"""Wording for the deterministic tools, one table per language (3-sep-2026).

The dose calculator, the rehydration advice, the vaccination schedules and the photo check were
each written as `es = lang == "es"` with two branches. French therefore got the English branch:
a parent asking "quelle dose de Doliprane pour 14 kg ?" in French was answered in English, by a
tool whose whole point is that a person can read it at three in the morning.

The strings live here instead, keyed by language, with English as the fallback for a language
that has not been written yet. Adding a language means adding a block — the tools themselves do
not change.
"""

from __future__ import annotations

from typing import Any

Table = dict[str, Any]

STRINGS: dict[str, Table] = {
    "en": {
        # --- oral rehydration ---
        "ors_under_1_month": "A baby under one month with vomiting or diarrhoea must be seen by a doctor today; do not give rehydration solution without medical advice.",
        "ors_under_2y": "Under 2 years: contact your paediatrician if vomiting or diarrhoea lasts more than 24 hours or the child refuses fluids.",
        "ors_after_vomit": "After a vomit, offer oral rehydration solution in very small amounts: 5–10 ml (one or two teaspoons, by spoon or syringe) every 10 minutes, increasing gradually if there is no further vomiting.",
        "ors_infant": "Infant over 1 month with diarrhoea: roughly 1–1.5 times the usual feed volume, in small amounts and slowly; breastfeeding does not need to stop.",
        "ors_child": "Child aged 1 year or more: about 200 ml of solution for each loose stool, given as 25–30 ml every 10–15 minutes.",
        "ors_sachet": "Make up the sachet exactly as the leaflet says (one sachet per the stated volume of water); do not make it stronger or weaker. Do not use sports drinks, fizzy drinks or juice.",
        "ors_go_er": "Go to the emergency department if fluids will not stay down, there is very little urine, sunken eyes, unusual drowsiness or blood in the stool.",
        # --- dose calculator ---
        "dose_for": "{name} for {kg:g} kg:",
        "dose_refer": "⚠️ Do not give without medical advice: ",
        "dose_line": "• Dose: {mg:g} mg every {h0}–{h1} h (max {max_doses} doses/day).",
        "dose_band": "The guide allows {mg_min:g}–{mg_max:g} mg; this is the usual dose for fever.",
        "dose_source": "Source: {source}.",
        "dose_check": "Always check the concentration on the bottle. Under 3 months, ask a doctor before giving anything.",
        "dose_warn": {
            "under_3_months_refer": "under 3 months old",
            "below_min_age": "below the minimum age for this drug",
            "below_min_weight": "below the minimum weight for this drug",
            "capped_single_dose": "dose capped at the maximum per dose",
            "age_unknown": "no age given, and this medicine is not for babies under 3 months or under 5 kg",
        },
        # --- vaccination schedules ---
        "vax_source": "Source: ",
        "vax_due": "At this age the official schedule lists:",
        "vax_none": "There is no vaccine scheduled at this exact age in the official calendar.",
        "vax_next": "Next: {label} — ",
        # --- photo check ---
        "photo_poor": "I can't assess this photo (too dark, blurry, or not skin). If in doubt, see your paediatrician today; with breathing difficulty, spots that don't fade when pressed, or swollen lips, go to the emergency department.",
        "photo_emergency": "I can see a possible warning sign ({sign}). According to the SEUP, this needs immediate care: call {number} or go to the emergency department now, especially if breathing is difficult.",
        "photo_sign_cyanosis": "blue/grey lips or skin",
        "photo_sign_swelling": "swollen lips or eyelids",
        "photo_petechiae": "I can see spots that may not fade when pressed. Do the glass test: press a clear glass on the spots; if they stay visible through the glass, according to the SEUP you should go to the emergency department today, without waiting. I can't tell you what is causing them.",
        "photo_clear": "I don't see any of the three warning signs I check for (non-blanching spots, blue colour, swollen lips). That does not tell you what it is — a photo cannot replace an examination. If the rash spreads, there is high fever, or your child seems unwell, see your paediatrician today.",
        "photo_unsure": "I can't tell from this photo. If the spots don't fade when pressed with a glass, or there is lip swelling or blue colour, go to the emergency department; otherwise see your paediatrician today.",
    },
    "es": {
        "ors_under_1_month": "Un bebé de menos de un mes con vómitos o diarrea debe ser valorado por un médico hoy; no se dan sueros sin indicación.",
        "ors_under_2y": "Menores de 2 años: consulta con el pediatra si los vómitos o la diarrea duran más de 24 horas o si rechaza los líquidos.",
        "ors_after_vomit": "Tras un vómito, ofrece suero de rehidratación oral en cantidades muy pequeñas: 5–10 ml (una o dos cucharaditas, con cuchara o jeringa) cada 10 minutos, aumentando poco a poco si no vuelve a vomitar.",
        "ors_infant": "Lactante mayor de 1 mes con diarrea: aproximadamente 1–1,5 veces el volumen de su toma habitual, en pequeñas cantidades y despacio; no hace falta suspender la lactancia.",
        "ors_child": "Niño a partir de 1 año: unos 200 ml de suero por cada deposición diarreica, dándolo en tandas de 25–30 ml cada 10–15 minutos.",
        "ors_sachet": "Prepara el sobre exactamente como dice el prospecto (un sobre por la cantidad de agua indicada); no lo diluyas más ni menos. No uses bebidas isotónicas, refrescos ni zumos.",
        "ors_go_er": "Acude a urgencias si no consigue retener líquidos, orina muy poco, tiene los ojos hundidos, está muy decaído o hay sangre en las heces.",
        "dose_for": "{name} para {kg:g} kg:",
        "dose_refer": "⚠️ No dar sin consultar: ",
        "dose_line": "• Dosis: {mg:g} mg cada {h0}–{h1} h (máx. {max_doses} dosis/día).",
        "dose_band": "La guía admite de {mg_min:g} a {mg_max:g} mg; esta es la dosis habitual para la fiebre.",
        "dose_source": "Fuente: {source}.",
        "dose_check": "Comprueba siempre la concentración del envase. Si tiene menos de 3 meses, consulta antes de dar nada.",
        "dose_warn": {
            "under_3_months_refer": "menor de 3 meses",
            "below_min_age": "por debajo de la edad mínima del fármaco",
            "below_min_weight": "por debajo del peso mínimo del fármaco",
            "capped_single_dose": "dosis limitada al máximo por toma",
            "age_unknown": "no has indicado la edad, y este medicamento no es para menores de 3 meses ni de 5 kg",
        },
        "vax_source": "Fuente: ",
        "vax_due": "A esta edad tocan, según el calendario oficial:",
        "vax_none": "A esta edad no hay ninguna vacuna programada en el calendario oficial.",
        "vax_next": "Siguiente cita: {label} — ",
        "photo_poor": "No puedo valorar esta foto (poca luz, desenfoque o no se ve la piel). Si dudas, consulta hoy con el pediatra; ante dificultad para respirar, manchas que no desaparecen al presionar o hinchazón de labios, acude a urgencias.",
        "photo_emergency": "Veo un posible signo de alarma ({sign}). Según la SEUP, esto requiere atención inmediata: llama al {number} o acude a urgencias ahora, sobre todo si le cuesta respirar.",
        "photo_sign_cyanosis": "labios o piel azulados",
        "photo_sign_swelling": "hinchazón de labios o párpados",
        "photo_petechiae": "Veo manchas que podrían no desaparecer al presionar. Haz la prueba del vaso: aprieta un vaso transparente sobre la mancha; si sigue viéndose a través del cristal, según la SEUP hay que acudir a urgencias hoy, sin esperar. No puedo decirte qué la causa.",
        "photo_clear": "No veo en la foto ninguno de los tres signos de alarma que compruebo (manchas que no desaparecen al presionar, coloración azulada, hinchazón de labios). Eso no me dice qué es: una foto no sustituye a la exploración. Si el sarpullido se extiende, hay fiebre alta, o tu hijo está decaído, consulta con el pediatra hoy.",
        "photo_unsure": "No lo veo claro en esta foto. Si las manchas no desaparecen al presionarlas con un vaso, o hay hinchazón de labios o color azulado, acude a urgencias; si no, consulta hoy con el pediatra.",
    },
    "fr": {
        "ors_under_1_month": "Un bébé de moins d'un mois qui vomit ou qui a la diarrhée doit être vu par un médecin aujourd'hui ; on ne donne pas de soluté de réhydratation sans avis médical.",
        "ors_under_2y": "Avant 2 ans : contactez votre pédiatre si les vomissements ou la diarrhée durent plus de 24 heures, ou si l'enfant refuse de boire.",
        "ors_after_vomit": "Après un vomissement, proposez le soluté de réhydratation orale en très petites quantités : 5 à 10 ml (une ou deux cuillères à café, à la cuillère ou à la seringue) toutes les 10 minutes, en augmentant peu à peu s'il ne revomit pas.",
        "ors_infant": "Nourrisson de plus de 1 mois avec diarrhée : environ 1 à 1,5 fois le volume de sa tétée ou de son biberon habituel, en petites quantités et lentement ; il n'y a pas besoin d'arrêter l'allaitement.",
        "ors_child": "Enfant à partir de 1 an : environ 200 ml de soluté après chaque selle liquide, donnés par 25 à 30 ml toutes les 10 à 15 minutes.",
        "ors_sachet": "Préparez le sachet exactement comme l'indique la notice (un sachet pour la quantité d'eau indiquée) ; ne le diluez ni plus ni moins. N'utilisez pas de boissons pour sportifs, de sodas ni de jus de fruits.",
        "ors_go_er": "Allez aux urgences si l'enfant ne garde pas les liquides, s'il urine très peu, s'il a les yeux creux, s'il est anormalement somnolent ou s'il y a du sang dans les selles.",
        "dose_for": "{name} pour {kg:g} kg :",
        "dose_refer": "⚠️ Ne pas donner sans avis médical : ",
        "dose_line": "• Dose : {mg:g} mg toutes les {h0}–{h1} h (max. {max_doses} doses par jour).",
        "dose_band": "Le guide admet {mg_min:g}–{mg_max:g} mg ; c'est la dose habituelle contre la fièvre.",
        "dose_source": "Source : {source}.",
        "dose_check": "Vérifiez toujours la concentration inscrite sur le flacon. Avant 3 mois, demandez à un médecin avant de donner quoi que ce soit.",
        "dose_warn": {
            "under_3_months_refer": "moins de 3 mois",
            "below_min_age": "en dessous de l'âge minimum de ce médicament",
            "below_min_weight": "en dessous du poids minimum de ce médicament",
            "capped_single_dose": "dose limitée au maximum par prise",
            "age_unknown": "l'âge n'est pas indiqué, et ce médicament n'est pas pour les moins de 3 mois ni de 5 kg",
        },
        "vax_source": "Source : ",
        "vax_due": "À cet âge, le calendrier officiel prévoit :",
        "vax_none": "Aucun vaccin n'est prévu exactement à cet âge dans le calendrier officiel.",
        "vax_next": "Prochain rendez-vous : {label} — ",
        "photo_poor": "Je ne peux pas évaluer cette photo (trop sombre, floue, ou on n'y voit pas la peau). Dans le doute, consultez votre pédiatre aujourd'hui ; en cas de gêne respiratoire, de taches qui ne s'effacent pas à la pression ou de lèvres gonflées, allez aux urgences.",
        "photo_emergency": "Je vois un signe d'alerte possible ({sign}). Selon la SEUP, cela demande une prise en charge immédiate : appelez le {number} ou allez aux urgences maintenant, surtout si la respiration est difficile.",
        "photo_sign_cyanosis": "lèvres ou peau bleutées ou grises",
        "photo_sign_swelling": "lèvres ou paupières gonflées",
        "photo_petechiae": "Je vois des taches qui pourraient ne pas s'effacer à la pression. Faites le test du verre : appuyez un verre transparent sur les taches ; si elles restent visibles à travers le verre, selon la SEUP il faut aller aux urgences aujourd'hui, sans attendre. Je ne peux pas vous dire ce qui les provoque.",
        "photo_clear": "Je ne vois sur la photo aucun des trois signes d'alerte que je vérifie (taches qui ne s'effacent pas à la pression, coloration bleutée, lèvres gonflées). Cela ne dit pas ce que c'est : une photo ne remplace pas un examen. Si l'éruption s'étend, s'il y a une forte fièvre, ou si votre enfant est abattu, consultez votre pédiatre aujourd'hui.",
        "photo_unsure": "Je n'arrive pas à trancher sur cette photo. Si les taches ne s'effacent pas quand on appuie avec un verre, ou s'il y a un gonflement des lèvres ou une coloration bleutée, allez aux urgences ; sinon, consultez votre pédiatre aujourd'hui.",
    },
    "de": {
        "ors_under_1_month": "Ein Baby unter einem Monat, das erbricht oder Durchfall hat, muss heute von einer Ärztin oder einem Arzt gesehen werden; Rehydratationslösung wird ohne ärztlichen Rat nicht gegeben.",
        "ors_under_2y": "Unter 2 Jahren: Melden Sie sich bei Ihrer Kinderärztin oder Ihrem Kinderarzt, wenn Erbrechen oder Durchfall länger als 24 Stunden dauern oder das Kind nichts trinken will.",
        "ors_after_vomit": "Nach dem Erbrechen die orale Rehydratationslösung in sehr kleinen Mengen anbieten: 5–10 ml (ein bis zwei Teelöffel, mit Löffel oder Spritze) alle 10 Minuten, langsam steigern, wenn das Kind nicht erneut erbricht.",
        "ors_infant": "Säugling über 1 Monat mit Durchfall: etwa das 1- bis 1,5-Fache der üblichen Trinkmenge, in kleinen Portionen und langsam; abstillen ist nicht nötig.",
        "ors_child": "Kind ab 1 Jahr: etwa 200 ml Lösung nach jedem dünnen Stuhl, in Portionen von 25–30 ml alle 10–15 Minuten.",
        "ors_sachet": "Bereiten Sie den Beutel genau nach Packungsbeilage zu (ein Beutel auf die angegebene Wassermenge); nicht stärker und nicht schwächer ansetzen. Keine Sportgetränke, Limonaden oder Säfte verwenden.",
        "ors_go_er": "Fahren Sie in die Notaufnahme, wenn das Kind nichts bei sich behält, sehr wenig Urin ausscheidet, eingesunkene Augen hat, auffallend schläfrig ist oder Blut im Stuhl hat.",
        "dose_for": "{name} für {kg:g} kg:",
        "dose_refer": "⚠️ Nicht ohne ärztlichen Rat geben: ",
        "dose_line": "• Dosis: {mg:g} mg alle {h0}–{h1} h (höchstens {max_doses} Dosen pro Tag).",
        "dose_band": "Die Leitlinie erlaubt {mg_min:g}–{mg_max:g} mg; dies ist die übliche Dosis bei Fieber.",
        "dose_source": "Quelle: {source}.",
        "dose_check": "Prüfen Sie immer die auf Ihrer Flasche angegebene Konzentration. Unter 3 Monaten nichts ohne ärztlichen Rat geben.",
        "dose_warn": {
            "under_3_months_refer": "unter 3 Monate alt",
            "below_min_age": "unter dem Mindestalter für dieses Medikament",
            "below_min_weight": "unter dem Mindestgewicht für dieses Medikament",
            "capped_single_dose": "Dosis auf das Maximum pro Gabe begrenzt",
            "age_unknown": "kein Alter angegeben, und dieses Medikament ist nicht für Kinder unter 3 Monaten oder unter 5 kg",
        },
        "vax_source": "Quelle: ",
        "vax_due": "In diesem Alter sieht der offizielle Impfkalender vor:",
        "vax_none": "In genau diesem Alter ist im offiziellen Impfkalender keine Impfung vorgesehen.",
        "vax_next": "Nächster Termin: {label} — ",
        "photo_poor": "Dieses Foto kann ich nicht beurteilen (zu dunkel, unscharf, oder es ist keine Haut zu sehen). Im Zweifel gehen Sie heute zur Kinderärztin oder zum Kinderarzt; bei Atemnot, Flecken, die auf Druck nicht verschwinden, oder geschwollenen Lippen fahren Sie in die Notaufnahme.",
        "photo_emergency": "Ich sehe ein mögliches Warnzeichen ({sign}). Laut SEUP braucht das sofortige Hilfe: Rufen Sie {number} an oder fahren Sie jetzt in die Notaufnahme, besonders wenn die Atmung schwerfällt.",
        "photo_sign_cyanosis": "bläuliche oder graue Lippen oder Haut",
        "photo_sign_swelling": "geschwollene Lippen oder Augenlider",
        "photo_petechiae": "Ich sehe Flecken, die auf Druck möglicherweise nicht verschwinden. Machen Sie den Glastest: Drücken Sie ein durchsichtiges Glas auf die Flecken; bleiben sie durch das Glas sichtbar, sollten Sie laut SEUP heute in die Notaufnahme fahren, ohne zu warten. Woher sie kommen, kann ich Ihnen nicht sagen.",
        "photo_clear": "Auf dem Foto sehe ich keines der drei Warnzeichen, auf die ich achte (Flecken, die auf Druck nicht verschwinden, bläuliche Färbung, geschwollene Lippen). Das sagt aber nicht, was es ist — ein Foto ersetzt keine Untersuchung. Wenn der Ausschlag sich ausbreitet, hohes Fieber dazukommt oder Ihr Kind matt wirkt, gehen Sie heute zur Kinderärztin oder zum Kinderarzt.",
        "photo_unsure": "Auf diesem Foto kann ich es nicht sicher sagen. Wenn die Flecken beim Draufdrücken mit einem Glas nicht verschwinden, oder wenn Lippen geschwollen oder bläulich sind, fahren Sie in die Notaufnahme; sonst gehen Sie heute zur Kinderärztin oder zum Kinderarzt.",
    },
    "ru": {
        "ors_under_1_month": "Ребёнка младше месяца с рвотой или поносом должен осмотреть врач сегодня; раствор для регидратации без назначения врача не дают.",
        "ors_under_2y": "До 2 лет: обратитесь к педиатру, если рвота или понос длятся больше 24 часов или ребёнок отказывается пить.",
        "ors_after_vomit": "После рвоты давайте раствор для оральной регидратации очень маленькими порциями: 5–10 мл (одна-две чайные ложки, ложкой или шприцем без иглы) каждые 10 минут, постепенно увеличивая, если рвоты больше нет.",
        "ors_infant": "Грудной ребёнок старше 1 месяца с поносом: примерно 1–1,5 объёма обычного кормления, маленькими порциями и медленно; грудное вскармливание прекращать не нужно.",
        "ors_child": "Ребёнок от 1 года: около 200 мл раствора после каждого жидкого стула, порциями по 25–30 мл каждые 10–15 минут.",
        "ors_sachet": "Разводите пакетик строго по инструкции (один пакетик на указанный объём воды); не делайте раствор крепче или слабее. Не используйте спортивные напитки, газировку и соки.",
        "ors_go_er": "Поезжайте в приёмное отделение, если ребёнок не удерживает жидкость, мало мочится, у него запавшие глаза, необычная сонливость или кровь в стуле.",
        "dose_for": "{name} для {kg:g} кг:",
        "dose_refer": "⚠️ Не давать без назначения врача: ",
        "dose_line": "• Доза: {mg:g} мг каждые {h0}–{h1} ч (не более {max_doses} доз в сутки).",
        "dose_band": "Руководство допускает {mg_min:g}–{mg_max:g} мг; это обычная доза при температуре.",
        "dose_source": "Источник: {source}.",
        "dose_check": "Всегда проверяйте концентрацию, указанную на вашем флаконе. До 3 месяцев ничего не давайте без назначения врача.",
        "dose_warn": {
            "under_3_months_refer": "младше 3 месяцев",
            "below_min_age": "младше минимального возраста для этого препарата",
            "below_min_weight": "меньше минимального веса для этого препарата",
            "capped_single_dose": "доза ограничена максимумом на один приём",
            "age_unknown": "возраст не указан, а это лекарство не дают детям до 3 месяцев и легче 5 кг",
        },
        "vax_source": "Источник: ",
        "vax_due": "В этом возрасте по официальному календарю положены:",
        "vax_none": "Ровно в этом возрасте в официальном календаре прививок нет.",
        "vax_next": "Следующий визит: {label} — ",
        "photo_poor": "По этой фотографии я не могу ничего сказать (слишком темно, размыто или не видно кожи). Если сомневаетесь, обратитесь к педиатру сегодня; при затруднённом дыхании, пятнах, которые не бледнеют при надавливании, или отёке губ — в приёмное отделение.",
        "photo_emergency": "Вижу возможный тревожный признак ({sign}). По данным SEUP, это требует немедленной помощи: звоните {number} или везите ребёнка в приёмное отделение сейчас, особенно если дыхание затруднено.",
        "photo_sign_cyanosis": "синюшные или серые губы либо кожа",
        "photo_sign_swelling": "отёк губ или век",
        "photo_petechiae": "Вижу пятна, которые, возможно, не бледнеют при надавливании. Сделайте пробу стаканом: прижмите прозрачный стакан к пятнам; если они видны сквозь стекло, по данным SEUP нужно ехать в приёмное отделение сегодня, не откладывая. Причину назвать я не могу.",
        "photo_clear": "На фотографии я не вижу ни одного из трёх тревожных признаков, которые проверяю (пятна, не бледнеющие при надавливании, синюшность, отёк губ). Это не говорит, что именно у ребёнка: фотография не заменяет осмотра. Если сыпь распространяется, есть высокая температура или ребёнок вялый, обратитесь к педиатру сегодня.",
        "photo_unsure": "По этой фотографии я не могу решить. Если пятна не бледнеют при надавливании стаканом или есть отёк губ либо синюшность — в приёмное отделение; в остальных случаях обратитесь к педиатру сегодня.",
    },
    "ar": {
        "ors_under_1_month": "الرضيع الذي عمره أقل من شهر ويتقيأ أو لديه إسهال يجب أن يفحصه طبيب اليوم؛ ولا يُعطى محلول معالجة الجفاف دون إرشاد طبي.",
        "ors_under_2y": "تحت سنتين: اتصل بطبيب طفلك إذا استمر القيء أو الإسهال أكثر من 24 ساعة أو إذا رفض الطفل الشرب.",
        "ors_after_vomit": "بعد القيء، قدّم محلول معالجة الجفاف بكميات صغيرة جدا: 5 إلى 10 مل (ملعقة صغيرة أو اثنتين، بالملعقة أو بحقنة بدون إبرة) كل 10 دقائق، مع الزيادة تدريجيا إذا لم يتكرر القيء.",
        "ors_infant": "الرضيع الأكبر من شهر مع إسهال: نحو 1 إلى 1٫5 ضعف كمية رضعته المعتادة، بكميات صغيرة وببطء؛ ولا داعي لإيقاف الرضاعة الطبيعية.",
        "ors_child": "الطفل من عمر سنة فأكثر: نحو 200 مل من المحلول بعد كل براز سائل، تُعطى على دفعات من 25 إلى 30 مل كل 10 إلى 15 دقيقة.",
        "ors_sachet": "حضّر الكيس تماما كما تقول النشرة (كيس واحد لكمية الماء المذكورة)؛ لا تجعله أقوى ولا أضعف. ولا تستخدم مشروبات الرياضيين أو المشروبات الغازية أو العصائر.",
        "ors_go_er": "توجّه إلى قسم الطوارئ إذا لم يحتفظ الطفل بالسوائل، أو تبوّل قليلا جدا، أو غارت عيناه، أو كان نعسانا بشكل غير معتاد، أو ظهر دم في البراز.",
        "dose_for": "{name} لوزن {kg:g} كغ:",
        "dose_refer": "⚠️ لا يُعطى دون إرشاد طبي: ",
        "dose_line": "• الجرعة: {mg:g} ملغ كل {h0}–{h1} ساعة (بحد أقصى {max_doses} جرعات في اليوم).",
        "dose_band": "يسمح الدليل بـ {mg_min:g}–{mg_max:g} ملغ؛ وهذه هي الجرعة المعتادة للحرارة.",
        "dose_source": "المصدر: {source}.",
        "dose_check": "تحقق دائما من التركيز المطبوع على عبوتك. وقبل عمر 3 أشهر لا تعطِ أي دواء دون وصفة.",
        "dose_warn": {
            "under_3_months_refer": "أقل من 3 أشهر",
            "below_min_age": "أقل من العمر الأدنى لهذا الدواء",
            "below_min_weight": "أقل من الوزن الأدنى لهذا الدواء",
            "capped_single_dose": "الجرعة محدودة بالحد الأقصى للجرعة الواحدة",
            "age_unknown": "لم يُذكر العمر، وهذا الدواء لا يُعطى لمن هم دون 3 أشهر أو أقل من 5 كجم",
        },
        "vax_source": "المصدر: ",
        "vax_due": "في هذا العمر يحدد التقويم الرسمي:",
        "vax_none": "لا يوجد لقاح مقرر في هذا العمر بالضبط في التقويم الرسمي.",
        "vax_next": "الموعد التالي: {label} — ",
        "photo_poor": "لا أستطيع تقييم هذه الصورة (إضاءة ضعيفة أو تشويش أو لا يظهر فيها الجلد). إذا كنت في شك فراجع طبيب طفلك اليوم؛ ومع صعوبة التنفس أو بقع لا تختفي عند الضغط أو تورم الشفتين توجّه إلى قسم الطوارئ.",
        "photo_emergency": "أرى علامة تحذير محتملة ({sign}). وفقا لـ SEUP يحتاج هذا عناية فورية: اتصل بـ {number} أو توجّه إلى قسم الطوارئ الآن، خاصة إذا كان التنفس صعبا.",
        "photo_sign_cyanosis": "شفاه أو جلد بلون أزرق أو رمادي",
        "photo_sign_swelling": "تورم في الشفتين أو الجفون",
        "photo_petechiae": "أرى بقعا قد لا تختفي عند الضغط. جرّب اختبار الكوب: اضغط كوبا شفافا على البقع؛ فإن بقيت ظاهرة من خلال الزجاج فوفقا لـ SEUP يجب التوجه إلى قسم الطوارئ اليوم دون انتظار. ولا أستطيع أن أخبرك بسببها.",
        "photo_clear": "لا أرى في الصورة أيا من علامات التحذير الثلاث التي أتحقق منها (بقع لا تختفي عند الضغط، ازرقاق، تورم الشفتين). وهذا لا يعني أنني أعرف ما هو: الصورة لا تغني عن الفحص. وإذا انتشر الطفح أو ارتفعت الحرارة كثيرا أو بدا طفلك متعبا فراجع طبيبه اليوم.",
        "photo_unsure": "لا أستطيع الجزم من هذه الصورة. إذا لم تختفِ البقع عند الضغط عليها بكوب، أو كان هناك تورم في الشفتين أو ازرقاق، فتوجّه إلى قسم الطوارئ؛ وإلا فراجع طبيب طفلك اليوم.",
    },
    "pt": {
        "ors_under_1_month": "Um bebê com menos de um mês que vomita ou tem diarreia precisa ser avaliado por um médico hoje; não se dá soro sem orientação médica.",
        "ors_under_2y": "Menores de 2 anos: procure o pediatra se os vômitos ou a diarreia durarem mais de 24 horas ou se a criança recusar líquidos.",
        "ors_after_vomit": "Depois de um vômito, ofereça soro de reidratação oral em quantidades bem pequenas: 5–10 ml (uma ou duas colheres de chá, com colher ou seringa) a cada 10 minutos, aumentando aos poucos se não vomitar de novo.",
        "ors_infant": "Bebê com mais de 1 mês com diarreia: cerca de 1–1,5 vez o volume da mamada habitual, em pequenas quantidades e devagar; não é preciso interromper a amamentação.",
        "ors_child": "Criança a partir de 1 ano: cerca de 200 ml de soro a cada evacuação diarreica, dados em porções de 25–30 ml a cada 10–15 minutos.",
        "ors_sachet": "Prepare o sachê exatamente como diz a bula (um sachê para a quantidade de água indicada); não dilua mais nem menos. Não use bebidas isotônicas, refrigerantes nem sucos.",
        "ors_go_er": "Vá ao pronto-socorro se a criança não conseguir reter líquidos, urinar muito pouco, estiver com os olhos fundos, muito abatida, ou se houver sangue nas fezes.",
        "dose_for": "{name} para {kg:g} kg:",
        "dose_refer": "⚠️ Não dar sem consultar: ",
        "dose_line": "• Dose: {mg:g} mg a cada {h0}–{h1} h (máx. {max_doses} doses/dia).",
        "dose_band": "O guia admite de {mg_min:g} a {mg_max:g} mg; esta é a dose habitual para a febre.",
        "dose_source": "Fonte: {source}.",
        "dose_check": "Confira sempre a concentração impressa na embalagem. Com menos de 3 meses, não dê nada sem orientação médica.",
        "dose_warn": {
            "under_3_months_refer": "menor de 3 meses",
            "below_min_age": "abaixo da idade mínima do medicamento",
            "below_min_weight": "abaixo do peso mínimo do medicamento",
            "capped_single_dose": "dose limitada ao máximo por tomada",
            "age_unknown": "a idade não foi indicada, e este medicamento não é para menores de 3 meses nem de 5 kg",
        },
        "vax_source": "Fonte: ",
        "vax_due": "Nesta idade estão previstas, segundo o calendário oficial:",
        "vax_next": "Próxima: {label} — ",
        "vax_none": "Nesta idade não há nenhuma vacina prevista no calendário oficial.",
        "photo_poor": "Não consigo avaliar esta foto (pouca luz, desfoque ou a pele não aparece). Na dúvida, procure o pediatra hoje; se houver dificuldade para respirar, manchas que não somem ao pressionar ou inchaço nos lábios, vá ao pronto-socorro.",
        "photo_emergency": "Vejo um possível sinal de alarme ({sign}). Segundo a SEUP, isso exige atendimento imediato: ligue para {number} ou vá ao pronto-socorro agora, principalmente se estiver com dificuldade para respirar.",
        "photo_sign_cyanosis": "lábios ou pele arroxeados",
        "photo_sign_swelling": "inchaço nos lábios ou nas pálpebras",
        "photo_petechiae": "Vejo manchas que podem não sumir ao pressionar. Faça o teste do copo: pressione um copo transparente sobre a mancha; se ela continuar visível através do vidro, segundo a SEUP é preciso ir ao pronto-socorro hoje, sem esperar. Não posso dizer o que a causa.",
        "photo_clear": "Não vejo na foto nenhum dos três sinais de alarme que eu verifico (manchas que não somem ao pressionar, coloração arroxeada, inchaço nos lábios). Isso não me diz o que é: uma foto não substitui o exame. Se a erupção se espalhar, houver febre alta ou a criança estiver abatida, procure o pediatra hoje.",
        "photo_unsure": "Não consigo ter certeza por esta foto. Se as manchas não sumirem ao pressioná-las com um copo, ou se houver inchaço nos lábios ou coloração arroxeada, vá ao pronto-socorro; caso contrário, procure o pediatra hoje.",
    },
    "hi": {
        "ors_under_1_month": "एक महीने से छोटे शिशु को उल्टी या दस्त हो तो आज ही डॉक्टर को दिखाएँ; बिना डॉक्टर की सलाह के ओआरएस न दें।",
        "ors_under_2y": "दो साल से छोटे बच्चे: अगर उल्टी या दस्त 24 घंटे से ज़्यादा चले, या बच्चा पीना ही मना कर दे, तो डॉक्टर से मिलें।",
        "ors_after_vomit": "उल्टी के बाद ओआरएस बहुत थोड़ा-थोड़ा दें: हर 10 मिनट में 5 से 10 मिली (एक-दो चम्मच, चम्मच या सिरिंज से), और उल्टी न हो तो धीरे-धीरे बढ़ाएँ।",
        "ors_infant": "एक महीने से बड़ा शिशु, दस्त के साथ: उसकी आम फ़ीड का लगभग 1 से 1.5 गुना, थोड़ा-थोड़ा और धीरे-धीरे; स्तनपान रोकने की ज़रूरत नहीं।",
        "ors_child": "एक साल या बड़ा बच्चा: हर पतले दस्त के बाद लगभग 200 मिली ओआरएस, हर 10 से 15 मिनट में 25 से 30 मिली करके।",
        "ors_sachet": "पैकेट को ठीक वैसे ही घोलें जैसे उस पर लिखा है (एक पैकेट, बताए हुए पानी में); न ज़्यादा गाढ़ा, न ज़्यादा पतला। स्पोर्ट्स ड्रिंक, कोल्ड ड्रिंक या जूस न दें।",
        "ors_go_er": "अगर बच्चा कुछ भी अंदर न रोक पाए, बहुत कम पेशाब करे, आँखें धँसी हों, बहुत सुस्त हो, या मल में खून आए, तो इमरजेंसी ले जाएँ।",
        "dose_for": "{kg:g} किलो के लिए {name}:",
        "dose_refer": "⚠️ डॉक्टर से पूछे बिना न दें: ",
        "dose_line": "• खुराक: {mg:g} मिग्रा, हर {h0}–{h1} घंटे में (दिन में ज़्यादा से ज़्यादा {max_doses} खुराक)।",
        "dose_band": "दिशानिर्देश {mg_min:g} से {mg_max:g} मिग्रा तक मानता है; बुखार के लिए यही आम खुराक है।",
        "dose_source": "स्रोत: {source}।",
        "dose_check": "डिब्बे पर लिखी ताक़त हमेशा जाँच लें। तीन महीने से छोटे बच्चे को डॉक्टर की सलाह के बिना कुछ न दें।",
        "dose_warn": {
            "under_3_months_refer": "तीन महीने से छोटा",
            "below_min_age": "दवा की कम से कम उम्र से छोटा",
            "below_min_weight": "दवा के कम से कम वज़न से हल्का",
            "capped_single_dose": "एक बार की अधिकतम खुराक तक सीमित",
            "age_unknown": "उम्र नहीं बताई गई है, और यह दवा 3 महीने से छोटे या 5 किलो से कम वज़न वाले बच्चों को नहीं दी जाती",
        },
        "vax_source": "स्रोत: ",
        "vax_due": "इस उम्र पर आधिकारिक कैलेंडर के अनुसार ये टीके हैं:",
        "vax_next": "अगली बार: {label} — ",
        "vax_none": "आधिकारिक कैलेंडर में ठीक इस उम्र पर कोई टीका नहीं है।",
        "photo_poor": "इस तस्वीर से मैं कुछ नहीं कह सकता (कम रोशनी, धुँधली, या त्वचा दिख नहीं रही)। शक हो तो आज ही डॉक्टर को दिखाएँ; साँस लेने में दिक्कत, दबाने पर न मिटने वाले दाने, या होंठ सूजे हों तो इमरजेंसी जाएँ।",
        "photo_emergency": "मुझे एक चेतावनी का निशान दिख रहा है ({sign})। SEUP के अनुसार इसे तुरंत देखना चाहिए: अभी {number} पर कॉल करें या इमरजेंसी जाएँ, ख़ासकर अगर साँस लेने में दिक्कत हो।",
        "photo_sign_cyanosis": "होंठ या त्वचा का नीला पड़ना",
        "photo_sign_swelling": "होंठ या पलकों की सूजन",
        "photo_petechiae": "मुझे ऐसे दाने दिख रहे हैं जो दबाने पर शायद न मिटें। गिलास वाली जाँच करें: एक साफ़ गिलास दानों पर दबाएँ; अगर वे काँच के आर-पार भी दिखते रहें, तो SEUP के अनुसार आज ही, बिना रुके, इमरजेंसी जाना चाहिए। इनका कारण मैं नहीं बता सकता।",
        "photo_clear": "तस्वीर में मुझे वे तीनों चेतावनी के निशान नहीं दिख रहे जो मैं जाँचता हूँ (दबाने पर न मिटने वाले दाने, नीलापन, होंठों की सूजन)। इसका मतलब यह नहीं कि मुझे पता है यह क्या है: तस्वीर जाँच की जगह नहीं लेती। दाने फैलें, तेज़ बुखार हो, या बच्चा सुस्त लगे, तो आज ही डॉक्टर को दिखाएँ।",
        "photo_unsure": "इस तस्वीर से मैं पक्का नहीं कह सकता। अगर गिलास से दबाने पर दाने न मिटें, या होंठ सूजे हों या नीलापन हो, तो इमरजेंसी जाएँ; वरना आज ही डॉक्टर को दिखाएँ।",
    },
}


LANGUAGE_NAME = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "ru": "Russian",
    "ar": "Arabic",
    "pt": "Brazilian Portuguese",
    "hi": "Hindi",
}
"""What the model is told to write in. Kept here, in one place, because this exact mapping was
written inline twice — in the answer prompt and in the article prompt — and both times a new
language silently fell back to English. The article generator asked for "Spanish" when it meant
French, and the answer engine replied in English to a German question."""


#: The two words that hold a citation together. The document's title and its section stay in the
#: language the document is written in — translating those would break the verification they
#: exist for — but "section" and "p." are ours, and they were English on every page.
CITATION_WORDS: dict[str, tuple[str, str]] = {
    "en": ("section", "p."),
    "es": ("sección", "pág."),
    "fr": ("section", "p."),
    "de": ("Abschnitt", "S."),
    "ru": ("раздел", "с."),
    "ar": ("قسم", "ص."),
    # Brazilian spelling: Portugal writes "secção"
    "pt": ("seção", "p."),
    "hi": ("खंड", "पृ."),
}


def localise_citation(text: str, lang: str) -> str:
    """Swap the scaffolding of a citation into `lang`, leaving the quoted document alone."""
    section, page = CITATION_WORDS.get(lang, CITATION_WORDS["en"])
    return text.replace(', section "', f', {section} "').replace(", p. ", f", {page} ")


def tool_strings(lang: str) -> Table:
    """The table for this language, falling back to English rather than to a blank string."""
    return STRINGS.get(lang, STRINGS["en"])


def data_lang(node: dict[str, Any], lang: str) -> str:
    """Which language of a translated data node to read.

    The catalogues (vaccines, the warning-signs checklist) carry one key per language. Asking for
    a language the node does not have used to return None and render an empty string; this picks
    English instead, and says so by returning the key it chose.
    """
    return lang if lang in node else "en"
