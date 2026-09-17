"""Cada regla de alarma, en los ocho idiomas, con una frase de padre (17-sep-2026).

El operador encontró a la primera que «mi hijo cojea y tiene fiebre» salía rutina, y dijo lo que
había que decir: *«me preocupa que a la primera haya detectado algo tan grave. Además, debe estar
en todos los idiomas»*.

Ya había un candado que exigía patrones en los tres alfabetos, y las 51 reglas lo pasaban. Pero
ese candado mide que los patrones estén ESCRITOS, no que sirvan — la L47, otra vez. Así que se
midió de la única manera que vale: **una frase por regla y por idioma, escrita como la teclearía
un padre**, y a ver cuál salta.

De 408 casos, 72 no saltaban. Uno de cada seis. Y no eran reglas menores:

    very_high_fever        fallaba en SEIS idiomas de ocho: todos los patrones pedían el símbolo
                           de grados y un padre escribe «tiene 41 de fiebre»
    self_harm              fallaba en SEIS: cada lengua lo dice con otro verbo
    heatstroke             fallaba en los OCHO: la regla esperaba la palabra «golpe de calor» y
                           un padre describe la escena (al sol, confuso, sin sudar)
    neck_stiffness         fallaba en cuatro, y es la meningitis
    infant_fever_...       fallaba en ruso, porque «двухмесячный» no se leía como una edad
    suicidal_ideation      fallaba en inglés por una contracción: cubría «doesn't» y no «does not»

Y dos reglas se disparaban de MÁS, que es la otra cara: la del golpe en la cabeza saltaba con la
palabra «cabeza» a secas —un dolor de cabeza con vómitos salía como traumatismo craneal— y la del
líquido por la nariz saltaba con cualquier sangrado nasal, sin golpe.

Este fichero es el que impide que vuelva a pasar: si alguien añade un idioma o toca un patrón, la
frase de un padre tiene que seguir saltando. Las frases NO se copian de los patrones a propósito;
están escritas como se habla.
"""

from __future__ import annotations

import unicodedata

import pytest

from pedibot.bot.triage import Triage
from pedibot.settings import ROOT

IDIOMAS = ("es", "en", "fr", "de", "ru", "ar", "pt", "hi")


@pytest.fixture(scope="module")
def triaje() -> Triage:
    return Triage(ROOT / "config" / "red_flags.yaml")


#: regla → la misma situación contada por un padre en cada idioma
CASOS: dict[str, dict[str, str]] = {
    "not_responding": {
        "es": 'mi hijo no responde, no reacciona a nada',
        "en": 'my son is not responding to me at all',
        "fr": 'mon fils ne réagit à rien, il ne répond pas',
        "de": 'mein sohn reagiert auf nichts, er antwortet nicht',
        "ru": 'сын не реагирует ни на что, не отвечает',
        "ar": 'ابني لا يستجيب ولا يرد على شيء',
        "pt": 'o meu filho não responde nem reage a nada',
        "hi": 'मेरा बेटा कोई प्रतिक्रिया नहीं दे रहा',
    },
    "seizure": {
        "es": 'le ha dado una convulsión, le temblaba todo el cuerpo',
        "en": 'he had a seizure, his whole body was shaking',
        "fr": 'il a fait une convulsion, tout son corps tremblait',
        "de": 'er hatte einen krampfanfall, der ganze körper zitterte',
        "ru": 'у него были судороги, всё тело тряслось',
        "ar": 'أصيب بتشنج واهتز جسمه كله',
        "pt": 'teve uma convulsão, o corpo todo a tremer',
        "hi": 'उसे दौरा पड़ा, पूरा शरीर काँप रहा था',
    },
    "severe_breathing": {
        "es": 'respira muy rápido y se le marcan las costillas al respirar',
        "en": 'he is breathing very fast and his ribs are pulling in',
        "fr": 'il respire très vite et ses côtes se creusent',
        "de": 'er atmet sehr schnell und die rippen ziehen sich ein',
        "ru": 'он дышит очень часто, рёбра втягиваются',
        "ar": 'يتنفس بسرعة كبيرة وتنسحب أضلاعه',
        "pt": 'respira muito depressa e as costelas afundam',
        "hi": 'वह बहुत तेज़ साँस ले रहा है और पसलियाँ अंदर धँस रही हैं',
    },
    "anaphylaxis": {
        "es": 'se le han hinchado los labios y le cuesta respirar',
        "en": 'his lips are swollen and he is struggling to breathe',
        "fr": 'ses lèvres ont gonflé et il a du mal à respirer',
        "de": 'seine lippen sind geschwollen und er bekommt schlecht luft',
        "ru": 'у него опухли губы и тяжело дышать',
        "ar": 'انتفخت شفتاه ويصعب عليه التنفس',
        "pt": 'os lábios incharam e custa-lhe respirar',
        "hi": 'उसके होंठ सूज गए हैं और साँस लेने में दिक्कत है',
    },
    "choking": {
        "es": 'se está atragantando y no puede respirar',
        "en": 'she is choking and cannot breathe',
        "fr": "elle s'étouffe et n'arrive pas à respirer",
        "de": 'sie erstickt und bekommt keine luft',
        "ru": 'она подавилась и не может дышать',
        "ar": 'اختنقت ولا تستطيع التنفس',
        "pt": 'está engasgada e não consegue respirar',
        "hi": 'उसका दम घुट रहा है और साँस नहीं ले पा रही',
    },
    "mottled_skin": {
        "es": 'tiene la piel moteada y los labios azulados',
        "en": 'her skin is mottled and her lips look blue',
        "fr": 'sa peau est marbrée et ses lèvres sont bleues',
        "de": 'ihre haut ist marmoriert und die lippen sind blau',
        "ru": 'кожа мраморная, губы синие',
        "ar": 'جلدها مبقع وشفتاها زرقاوان',
        "pt": 'a pele está marmoreada e os lábios azulados',
        "hi": 'उसकी त्वचा चितकबरी है और होंठ नीले हैं',
    },
    "head_injury_loss_consciousness": {
        "es": 'se dio un golpe en la cabeza y perdió el conocimiento',
        "en": 'he hit his head and lost consciousness',
        "fr": "il s'est cogné la tête et a perdu connaissance",
        "de": 'er hat sich den kopf gestoßen und das bewusstsein verloren',
        "ru": 'он ударился головой и потерял сознание',
        "ar": 'ضرب رأسه وفقد الوعي',
        "pt": 'bateu com a cabeça e perdeu a consciência',
        "hi": 'उसने सिर पर चोट खाई और होश खो दिया',
    },
    "severe_bleeding": {
        "es": 'tiene una herida profunda que no para de sangrar',
        "en": 'he has a deep cut that will not stop bleeding',
        "fr": "il a une plaie profonde qui n'arrête pas de saigner",
        "de": 'er hat eine tiefe wunde, die nicht aufhört zu bluten',
        "ru": 'у него глубокая рана, кровь не останавливается',
        "ar": 'عنده جرح عميق لا يتوقف عن النزيف',
        "pt": 'tem uma ferida funda que não para de sangrar',
        "hi": 'उसका गहरा घाव है और ख़ून बंद नहीं हो रहा',
    },
    "open_fracture": {
        "es": 'se ha roto el brazo y se le ve el hueso',
        "en": 'he broke his arm and the bone is showing',
        "fr": "il s'est cassé le bras et on voit l'os",
        "de": 'er hat sich den arm gebrochen und der knochen schaut heraus',
        "ru": 'он сломал руку, видна кость',
        "ar": 'كسر ذراعه والعظم ظاهر',
        "pt": 'partiu o braço e vê-se o osso',
        "hi": 'उसका हाथ टूट गया है और हड्डी दिख रही है',
    },
    "petechiae_fever": {
        "es": 'tiene fiebre y unas manchas rojas que no se van al apretar',
        "en": 'she has a fever and a rash that does not fade when I press it',
        "fr": "elle a de la fièvre et des taches qui ne s'effacent pas à la pression",
        "de": 'sie hat fieber und flecken, die beim drücken nicht verschwinden',
        "ru": 'у неё температура и пятна, которые не исчезают при нажатии',
        "ar": 'عندها حمى وبقع لا تختفي عند الضغط',
        "pt": 'tem febre e manchas que não desaparecem ao pressionar',
        "hi": 'उसे बुखार है और ऐसे दाने हैं जो दबाने पर नहीं मिटते',
    },
    "button_battery": {
        "es": 'se ha tragado una pila de botón',
        "en": 'he swallowed a button battery',
        "fr": 'il a avalé une pile bouton',
        "de": 'er hat eine knopfzelle verschluckt',
        "ru": 'он проглотил батарейку-таблетку',
        "ar": 'ابتلع بطارية زر',
        "pt": 'engoliu uma pilha de botão',
        "hi": 'उसने बटन सेल निगल ली',
    },
    "neck_stiffness": {
        "es": 'no puede doblar el cuello y tiene fiebre',
        "en": 'she cannot bend her neck and has a fever',
        "fr": 'elle ne peut pas plier le cou et a de la fièvre',
        "de": 'sie kann den nacken nicht beugen und hat fieber',
        "ru": 'она не может наклонить шею, есть температура',
        "ar": 'لا تستطيع ثني رقبتها وعندها حمى',
        "pt": 'não consegue dobrar o pescoço e tem febre',
        "hi": 'वह गर्दन नहीं झुका पा रही और बुखार है',
    },
    "cannot_swallow_drooling": {
        "es": 'no puede tragar la saliva y babea mucho',
        "en": 'he cannot swallow and is drooling',
        "fr": "il n'arrive pas à avaler et il bave beaucoup",
        "de": 'er kann nicht schlucken und sabbert stark',
        "ru": 'он не может глотать, слюна течёт',
        "ar": 'لا يستطيع البلع واللعاب يسيل منه',
        "pt": 'não consegue engolir e baba muito',
        "hi": 'वह निगल नहीं पा रहा और लार बह रही है',
    },
    "infant_fever_under_3_months": {
        "es": 'mi bebé de 2 meses tiene 38.5 de fiebre',
        "en": 'my 2 month old baby has a fever of 38.5',
        "fr": 'mon bébé de 2 mois a 38,5 de fièvre',
        "de": 'mein 2 monate altes baby hat 38,5 fieber',
        "ru": 'у моего двухмесячного ребёнка температура 38,5',
        "ar": 'طفلي عمره شهران وحرارته 38.5',
        "pt": 'o meu bebé de 2 meses tem 38,5 de febre',
        "hi": 'मेरे 2 महीने के बच्चे को 38.5 बुखार है',
    },
    "very_high_fever": {
        "es": 'tiene 41 de fiebre',
        "en": 'his temperature is 41',
        "fr": 'il a 41 de fièvre',
        "de": 'er hat 41 fieber',
        "ru": 'у него температура 41',
        "ar": 'حرارته 41',
        "pt": 'tem 41 de febre',
        "hi": 'उसे 41 बुखार है',
    },
    "moderate_breathing": {
        "es": 'le silba el pecho al respirar',
        "en": 'he is wheezing when he breathes',
        "fr": 'il siffle quand il respire',
        "de": 'er pfeift beim atmen',
        "ru": 'у него свистящее дыхание',
        "ar": 'صدره يصفر عند التنفس',
        "pt": 'tem pieira quando respira',
        "hi": 'साँस लेते समय सीटी जैसी आवाज़ आती है',
    },
    "drowsy_irritable": {
        "es": 'está muy adormilado y no hay quien lo despierte del todo',
        "en": 'he is extremely drowsy and hard to wake properly',
        "fr": 'il est extrêmement somnolent et difficile à réveiller',
        "de": 'er ist sehr schläfrig und kaum richtig wach zu bekommen',
        "ru": 'он очень вялый и сонный, трудно разбудить',
        "ar": 'نعسان جدا ويصعب إيقاظه',
        "pt": 'está muito sonolento e difícil de acordar',
        "hi": 'वह बहुत सुस्त है और ठीक से जाग नहीं रहा',
    },
    "dehydration": {
        "es": 'lleva todo el día sin hacer pis y tiene la boca seca',
        "en": 'she has not had a wet nappy all day and her mouth is dry',
        "fr": "elle n'a pas mouillé sa couche de la journée et a la bouche sèche",
        "de": 'sie hatte den ganzen tag keine nasse windel und der mund ist trocken',
        "ru": 'она весь день не писала, во рту сухо',
        "ar": 'لم تبلل الحفاض طوال اليوم وفمها جاف',
        "pt": 'não urinou o dia todo e tem a boca seca',
        "hi": 'पूरे दिन पेशाब नहीं किया और मुँह सूखा है',
    },
    "vomiting_headache": {
        "es": 'vomita mucho y le duele muchísimo la cabeza',
        "en": 'she keeps vomiting and has a terrible headache',
        "fr": 'elle vomit beaucoup et a très mal à la tête',
        "de": 'sie erbricht immer wieder und hat starke kopfschmerzen',
        "ru": 'её постоянно рвёт и сильно болит голова',
        "ar": 'تتقيأ كثيرا وعندها صداع شديد',
        "pt": 'vomita muito e tem uma dor de cabeça forte',
        "hi": 'उसे बार-बार उल्टी हो रही है और सिर में तेज़ दर्द है',
    },
    "vomiting_after_head_injury": {
        "es": 'se dio un golpe en la cabeza y ha vomitado dos veces',
        "en": 'he banged his head and has vomited twice',
        "fr": "il s'est cogné la tête et a vomi deux fois",
        "de": 'er hat sich den kopf gestoßen und zweimal erbrochen',
        "ru": 'он ударился головой и дважды вырвало',
        "ar": 'ضرب رأسه وتقيأ مرتين',
        "pt": 'bateu com a cabeça e vomitou duas vezes',
        "hi": 'उसके सिर पर चोट लगी और दो बार उल्टी हुई',
    },
    "foreign_body_ingestion": {
        "es": 'se ha tragado un imán',
        "en": 'he swallowed a magnet',
        "fr": 'il a avalé un aimant',
        "de": 'er hat einen magneten verschluckt',
        "ru": 'он проглотил магнит',
        "ar": 'ابتلع مغناطيسا',
        "pt": 'engoliu um íman',
        "hi": 'उसने चुंबक निगल लिया',
    },
    "poisoning": {
        "es": 'se ha bebido lejía',
        "en": 'she drank bleach',
        "fr": "elle a bu de l'eau de javel",
        "de": 'sie hat bleichmittel getrunken',
        "ru": 'она выпила отбеливатель',
        "ar": 'شربت مبيضا',
        "pt": 'bebeu lixívia',
        "hi": 'उसने ब्लीच पी लिया',
    },
    "severe_abdominal_pain": {
        "es": 'le duele muchísimo la barriga y no se le pasa',
        "en": 'his tummy hurts a lot and it is not going away',
        "fr": 'il a très mal au ventre et ça ne passe pas',
        "de": 'er hat sehr starke bauchschmerzen, die nicht weggehen',
        "ru": 'у него очень сильно болит живот и не проходит',
        "ar": 'بطنه تؤلمه بشدة ولا يزول الألم',
        "pt": 'tem uma dor de barriga muito forte que não passa',
        "hi": 'उसके पेट में बहुत तेज़ दर्द है और जा नहीं रहा',
    },
    "newborn_refusing_feeds": {
        "es": 'mi recién nacido lleva varias tomas sin querer comer',
        "en": 'my newborn is refusing feeds',
        "fr": 'mon nouveau-né refuse de téter',
        "de": 'mein neugeborenes verweigert die nahrung',
        "ru": 'мой новорождённый отказывается от еды',
        "ar": 'مولودي يرفض الرضاعة',
        "pt": 'o meu recém-nascido recusa mamar',
        "hi": 'मेरा नवजात दूध पीने से मना कर रहा है',
    },
    "burn": {
        "es": 'se ha quemado la mano con agua hirviendo',
        "en": 'he burned his hand with boiling water',
        "fr": "il s'est brûlé la main avec de l'eau bouillante",
        "de": 'er hat sich die hand mit kochendem wasser verbrannt',
        "ru": 'он обжёг руку кипятком',
        "ar": 'احترقت يده بماء مغلي',
        "pt": 'queimou a mão com água a ferver',
        "hi": 'उसका हाथ खौलते पानी से जल गया',
    },
    "bilious_or_bloody_vomit": {
        "es": 'ha vomitado verde',
        "en": 'she vomited green',
        "fr": 'elle a vomi vert',
        "de": 'sie hat grün erbrochen',
        "ru": 'её вырвало зелёным',
        "ar": 'تقيأت أخضر',
        "pt": 'vomitou verde',
        "hi": 'उसने हरी उल्टी की',
    },
    "blood_in_stool": {
        "es": 'ha hecho caca con sangre',
        "en": 'there is blood in his poo',
        "fr": 'il y a du sang dans ses selles',
        "de": 'er hat blut im stuhl',
        "ru": 'у него кровь в стуле',
        "ar": 'في برازه دم',
        "pt": 'tem sangue nas fezes',
        "hi": 'उसके मल में ख़ून है',
    },
    "abdominal_pain_localised_or_worsening": {
        "es": 'le duele la barriga en el lado derecho y va a peor',
        "en": 'the pain is on the right side of his tummy and getting worse',
        "fr": 'il a mal au ventre du côté droit et ça empire',
        "de": 'die bauchschmerzen sind rechts und werden schlimmer',
        "ru": 'живот болит справа и становится хуже',
        "ar": 'ألم البطن في الجهة اليمنى ويزداد',
        "pt": 'a dor de barriga é do lado direito e está a piorar',
        "hi": 'पेट के दाहिनी ओर दर्द है और बढ़ रहा है',
    },
    "deformity_fracture": {
        "es": 'tiene el brazo torcido después de la caída',
        "en": 'his arm looks bent after the fall',
        "fr": 'son bras est tordu après la chute',
        "de": 'sein arm ist nach dem sturz verformt',
        "ru": 'после падения рука деформирована',
        "ar": 'ذراعه معوجة بعد السقوط',
        "pt": 'o braço ficou torto depois da queda',
        "hi": 'गिरने के बाद उसका हाथ टेढ़ा है',
    },
    "deep_wound": {
        "es": 'se ha hecho un corte profundo que creo que necesita puntos',
        "en": 'he has a deep cut that I think needs stitches',
        "fr": 'il a une coupure profonde qui a besoin de points',
        "de": 'er hat eine tiefe schnittwunde, die genäht werden muss',
        "ru": 'у него глубокий порез, наверное нужны швы',
        "ar": 'عنده جرح عميق يحتاج غرزا',
        "pt": 'tem um corte fundo que precisa de pontos',
        "hi": 'उसे गहरा कट लगा है, शायद टाँके चाहिए',
    },
    "neuro_deficit": {
        "es": 'no mueve bien el brazo izquierdo desde esta mañana',
        "en": 'he cannot move his left arm properly since this morning',
        "fr": 'il ne bouge plus bien le bras gauche depuis ce matin',
        "de": 'er kann den linken arm seit heute morgen nicht richtig bewegen',
        "ru": 'он с утра плохо двигает левой рукой',
        "ar": 'لا يحرك ذراعه اليسرى جيدا منذ الصباح',
        "pt": 'não mexe bem o braço esquerdo desde esta manhã',
        "hi": 'आज सुबह से उसका बायाँ हाथ ठीक से नहीं हिल रहा',
    },
    "headache_warning_signs": {
        "es": 'le duele la cabeza por la noche y le despierta',
        "en": 'his headache wakes him up at night',
        "fr": 'son mal de tête le réveille la nuit',
        "de": 'die kopfschmerzen wecken ihn nachts auf',
        "ru": 'головная боль будит его ночью',
        "ar": 'الصداع يوقظه ليلا',
        "pt": 'a dor de cabeça acorda-o à noite',
        "hi": 'सिरदर्द रात में उसे जगा देता है',
    },
    "meningitis_signs": {
        "es": 'tiene fiebre y le molesta mucho la luz',
        "en": 'she has a fever and the light hurts her eyes',
        "fr": 'elle a de la fièvre et la lumière la gêne beaucoup',
        "de": 'sie hat fieber und das licht tut ihr weh',
        "ru": 'у неё температура и свет режет глаза',
        "ar": 'عندها حمى والضوء يزعجها كثيرا',
        "pt": 'tem febre e a luz incomoda-lhe muito',
        "hi": 'उसे बुखार है और रोशनी से बहुत तकलीफ़ है',
    },
    "mastoiditis": {
        "es": 'tiene hinchazón detrás de la oreja y la oreja hacia fuera',
        "en": 'there is swelling behind his ear and the ear sticks out',
        "fr": "il a un gonflement derrière l'oreille et l'oreille décollée",
        "de": 'hinter dem ohr ist eine schwellung und das ohr steht ab',
        "ru": 'за ухом припухлость и ухо оттопырено',
        "ar": 'خلف أذنه تورم والأذن بارزة',
        "pt": 'tem inchaço atrás da orelha e a orelha saliente',
        "hi": 'कान के पीछे सूजन है और कान बाहर निकला है',
    },
    "blood_in_urine": {
        "es": 'ha hecho pis con sangre',
        "en": 'there is blood in her wee',
        "fr": 'il y a du sang dans ses urines',
        "de": 'sie hat blut im urin',
        "ru": 'у неё кровь в моче',
        "ar": 'في بولها دم',
        "pt": 'tem sangue na urina',
        "hi": 'उसके पेशाब में ख़ून है',
    },
    "fluid_from_ear_or_nose": {
        "es": 'le sale líquido claro por la nariz desde el golpe',
        "en": 'clear fluid is coming from his nose since the blow',
        "fr": 'un liquide clair sort de son nez depuis le choc',
        "de": 'seit dem schlag läuft klare flüssigkeit aus der nase',
        "ru": 'после удара из носа течёт прозрачная жидкость',
        "ar": 'يخرج سائل صاف من أنفه بعد الضربة',
        "pt": 'sai líquido claro do nariz desde a pancada',
        "hi": 'चोट के बाद नाक से साफ़ तरल निकल रहा है',
    },
    "mammal_bite": {
        "es": 'le ha mordido un perro',
        "en": 'a dog bit him',
        "fr": "un chien l'a mordu",
        "de": 'ein hund hat ihn gebissen',
        "ru": 'его укусила собака',
        "ar": 'عضه كلب',
        "pt": 'um cão mordeu-o',
        "hi": 'उसे कुत्ते ने काट लिया',
    },
    "heatstroke": {
        "es": 'ha estado al sol y está confuso y no suda',
        "en": 'he was in the sun and is confused and not sweating',
        "fr": 'il était au soleil, il est confus et ne transpire pas',
        "de": 'er war in der sonne, ist verwirrt und schwitzt nicht',
        "ru": 'он был на солнце, спутанный и не потеет',
        "ar": 'كان في الشمس وهو مشوش ولا يتعرق',
        "pt": 'esteve ao sol, está confuso e não transpira',
        "hi": 'वह धूप में था, उलझन में है और पसीना नहीं आ रहा',
    },
    "neonatal_jaundice": {
        "es": 'mi recién nacido está amarillo',
        "en": 'my newborn looks yellow',
        "fr": 'mon nouveau-né est tout jaune',
        "de": 'mein neugeborenes ist gelb',
        "ru": 'мой новорождённый жёлтый',
        "ar": 'مولودي أصفر اللون',
        "pt": 'o meu recém-nascido está amarelo',
        "hi": 'मेरा नवजात पीला पड़ गया है',
    },
    "cold_extremities_with_fever": {
        "es": 'tiene fiebre y las manos y los pies muy fríos',
        "en": 'she has a fever and her hands and feet are very cold',
        "fr": 'elle a de la fièvre et les mains et les pieds très froids',
        "de": 'sie hat fieber und die hände und füße sind sehr kalt',
        "ru": 'у неё температура, а руки и ноги очень холодные',
        "ar": 'عندها حمى ويداها وقدماها باردتان جدا',
        "pt": 'tem febre e as mãos e os pés muito frios',
        "hi": 'उसे बुखार है और हाथ-पैर बहुत ठंडे हैं',
    },
    "bleeding_with_fever": {
        "es": 'tiene fiebre y le sangra la nariz',
        "en": 'he has a fever and his nose is bleeding',
        "fr": 'il a de la fièvre et saigne du nez',
        "de": 'er hat fieber und nasenbluten',
        "ru": 'у него температура и идёт кровь из носа',
        "ar": 'عنده حمى وينزف من أنفه',
        "pt": 'tem febre e sangra do nariz',
        "hi": 'उसे बुखार है और नाक से ख़ून आ रहा है',
    },
    "snakebite": {
        "es": 'le ha picado una serpiente',
        "en": 'he was bitten by a snake',
        "fr": 'il a été mordu par un serpent',
        "de": 'er wurde von einer schlange gebissen',
        "ru": 'его укусила змея',
        "ar": 'لدغته أفعى',
        "pt": 'foi mordido por uma cobra',
        "hi": 'उसे साँप ने काट लिया',
    },
    "lockjaw_spasms": {
        "es": 'no puede abrir la boca y tiene espasmos',
        "en": 'he cannot open his mouth and has muscle spasms',
        "fr": 'il ne peut pas ouvrir la bouche et a des spasmes',
        "de": 'er kann den mund nicht öffnen und hat krämpfe',
        "ru": 'он не может открыть рот, есть спазмы',
        "ar": 'لا يستطيع فتح فمه وعنده تشنجات',
        "pt": 'não consegue abrir a boca e tem espasmos',
        "hi": 'वह मुँह नहीं खोल पा रहा और ऐंठन है',
    },
    "suicidal_ideation": {
        "es": 'mi hija dice que no quiere seguir viviendo',
        "en": 'my daughter says she does not want to live any more',
        "fr": "ma fille dit qu'elle ne veut plus vivre",
        "de": 'meine tochter sagt, sie will nicht mehr leben',
        "ru": 'дочь говорит, что не хочет больше жить',
        "ar": 'ابنتي تقول إنها لا تريد أن تعيش',
        "pt": 'a minha filha diz que não quer continuar a viver',
        "hi": 'मेरी बेटी कहती है कि वह और जीना नहीं चाहती',
    },
    "self_harm": {
        "es": 'se ha hecho cortes en los brazos',
        "en": 'she has been cutting her arms',
        "fr": 'elle se fait des entailles aux bras',
        "de": 'sie ritzt sich die arme',
        "ru": 'она режет себе руки',
        "ar": 'تجرح ذراعيها',
        "pt": 'anda a cortar-se nos braços',
        "hi": 'वह अपनी बाँहों पर कट लगाती है',
    },
    "eating_disorder_signs": {
        "es": 'mi hija vomita después de comer y dice que está gorda',
        "en": 'my daughter vomits after meals and says she is fat',
        "fr": 'ma fille vomit après les repas et se trouve grosse',
        "de": 'meine tochter erbricht nach dem essen und findet sich dick',
        "ru": 'дочь вызывает рвоту после еды и считает себя толстой',
        "ar": 'ابنتي تتقيأ بعد الأكل وتقول إنها سمينة',
        "pt": 'a minha filha vomita depois de comer e diz que está gorda',
        "hi": 'मेरी बेटी खाने के बाद उल्टी करती है और ख़ुद को मोटी कहती है',
    },
    "bulging_fontanelle": {
        "es": 'tiene la fontanela abombada',
        "en": 'his fontanelle is bulging',
        "fr": 'sa fontanelle est bombée',
        "de": 'seine fontanelle ist vorgewölbt',
        "ru": 'у него выбухает родничок',
        "ar": 'يافوخه منتفخ',
        "pt": 'a fontanela está abaulada',
        "hi": 'उसका तालू उभरा हुआ है',
    },
    "testicular_pain": {
        "es": 'le duele un testículo',
        "en": 'his testicle hurts',
        "fr": 'il a mal à un testicule',
        "de": 'sein hoden tut weh',
        "ru": 'у него болит яичко',
        "ar": 'خصيته تؤلمه',
        "pt": 'dói-lhe um testículo',
        "hi": 'उसके अंडकोष में दर्द है',
    },
    "sudden_pallor": {
        "es": 'se ha puesto pálido de repente',
        "en": 'he suddenly went pale',
        "fr": "il est devenu pâle d'un coup",
        "de": 'er ist plötzlich blass geworden',
        "ru": 'он вдруг побледнел',
        "ar": 'شحب لونه فجأة',
        "pt": 'ficou pálido de repente',
        "hi": 'वह अचानक पीला पड़ गया',
    },
    "unusual_cry": {
        "es": 'tiene un llanto agudo distinto del suyo',
        "en": 'she has a high-pitched cry',
        "fr": 'elle a un cri aigu',
        "de": 'sie hat einen schrillen schrei',
        "ru": 'у неё пронзительный крик',
        "ar": 'بكاؤها حاد',
        "pt": 'tem um choro agudo',
        "hi": 'उसका रोना तीखा है',
    },
    "limp_with_fever": {
        "es": 'cojea y tiene fiebre',
        "en": 'he is limping and has a fever',
        "fr": 'il boite et a de la fièvre',
        "de": 'er hinkt und hat fieber',
        "ru": 'он хромает, и у него температура',
        "ar": 'يعرج وعنده حرارة',
        "pt": 'coxeia e tem febre',
        "hi": 'वह लंगड़ा रहा है और बुखार है',
    },
    # ── Lote del 17-sep-2026: las diez urgencias que no tenían NINGUNA regla ──────────
    # Salieron de preguntar «¿qué reglas faltan?» en vez de «¿funcionan las que hay?».
    "stridor": {
        "es": 'hace un ruido raro al coger aire y tiene tos perruna',
        "en": 'he makes a harsh noise when he breathes in and has a barking cough',
        "fr": 'il fait un bruit en inspirant et a une toux aboyante',
        "de": 'er macht ein geräusch beim einatmen und hat bellenden husten',
        "ru": 'у него шум на вдохе и лающий кашель',
        "ar": 'يصدر صوتا عند الشهيق وعنده سعال نباحي',
        "pt": 'faz um ruído ao inspirar e tem tosse de cão',
        "hi": 'साँस लेते समय आवाज़ आती है और भौंकने जैसी खाँसी है',
    },
    "intussusception": {
        "es": 'llora a ratos y encoge las piernas cada vez',
        "en": 'he cries in waves and pulls his legs up each time',
        "fr": 'il pleure par crises et replie les jambes à chaque fois',
        "de": 'er schreit in wellen und zieht die beine an',
        "ru": 'плачет приступами и поджимает ноги',
        "ar": 'يبكي على نوبات ويضم ساقيه',
        "pt": 'chora às crises e encolhe as pernas',
        "hi": 'वह रुक-रुक कर रोता है और हर बार पैर सिकोड़ता है',
    },
    "projectile_vomiting_infant": {
        "es": 'mi bebé vomita a chorro después de cada toma',
        "en": 'my baby has projectile vomiting after every feed',
        "fr": 'mon bébé a des vomissements en jet après chaque tétée',
        "de": 'mein baby erbricht schwallartig nach jeder mahlzeit',
        "ru": 'малыша рвёт фонтаном после каждого кормления',
        "ar": 'طفلي عنده قيء قذفي بعد كل رضعة',
        "pt": 'o meu bebé tem vómito em jato depois de cada mamada',
        "hi": 'मेरे बच्चे को हर फ़ीड के बाद उछलकर उल्टी होती है',
    },
    "new_diabetes_signs": {
        "es": 'bebe muchísima agua y orina todo el rato',
        "en": 'she is drinking a lot of water and weeing all the time',
        "fr": "elle boit beaucoup d'eau et urine tout le temps",
        "de": 'sie trinkt sehr viel und uriniert ständig',
        "ru": 'она пьёт очень много и постоянно мочится',
        "ar": 'تشرب كثيرا وتتبول باستمرار',
        "pt": 'bebe muita água e urina o tempo todo',
        "hi": 'वह बहुत पानी पी रही है और बार-बार पेशाब कर रही है',
    },
    "inhaled_foreign_body": {
        "es": 'estaba comiendo frutos secos y le entró una tos de repente',
        "en": 'he was eating peanuts and suddenly started coughing',
        "fr": "il mangeait des cacahuètes et s'est mis à tousser d'un coup",
        "de": 'er aß nüsse und hat plötzlich gehustet',
        "ru": 'он ел орехи и вдруг закашлялся',
        "ar": 'كان يأكل مكسرات وبدأ السعال فجأة',
        "pt": 'estava a comer amendoins e começou a tossir de repente',
        "hi": 'वह मूँगफली खाते समय अचानक खाँसने लगा',
    },
    "asthma_not_responding": {
        "es": 'le he dado el ventolín y sigue igual',
        "en": 'I gave him the inhaler and he is no better',
        "fr": "je lui ai donné la ventoline et c'est toujours pareil",
        "de": 'ich habe ihm das spray gegeben und es hilft nicht',
        "ru": 'дала ингалятор, а ему не помогает',
        "ar": 'أعطيته البخاخ ولا يفيد',
        "pt": 'dei-lhe o inalador e não melhora',
        "hi": 'मैंने इनहेलर दिया पर असर नहीं हुआ',
    },
    "chemical_in_eye": {
        "es": 'le ha entrado lejía en el ojo',
        "en": 'he got bleach in his eye',
        "fr": "il a reçu de la javel dans l'œil",
        "de": 'ihm ist bleichmittel ins auge gekommen',
        "ru": 'ему попал отбеливатель в глаз',
        "ar": 'دخل مبيض في عينه',
        "pt": 'entrou-lhe lixívia no olho',
        "hi": 'उसकी आँख में ब्लीच चला गया',
    },
    "omphalitis": {
        "es": 'el ombligo está rojo y huele mal',
        "en": 'the navel is red and smells bad',
        "fr": 'le nombril est rouge et sent mauvais',
        "de": 'der nabel ist rot und riecht',
        "ru": 'пупок красный и пахнет',
        "ar": 'السرة حمراء ورائحتها كريهة',
        "pt": 'o umbigo está vermelho e cheira mal',
        "hi": 'नाभि लाल है और बदबू आ रही है',
    },
    "carbon_monoxide": {
        "es": 'creo que es monóxido de carbono de la estufa',
        "en": 'I think it is carbon monoxide from the heater',
        "fr": "je crois que c'est du monoxyde de carbone",
        "de": 'ich glaube, es ist kohlenmonoxid',
        "ru": 'думаю, это угарный газ',
        "ar": 'أظنه أول أكسيد الكربون',
        "pt": 'acho que é monóxido de carbono',
        "hi": 'मुझे लगता है यह कार्बन मोनोऑक्साइड है',
    },
    "near_drowning": {
        "es": 'se cayó a la piscina y lo sacamos tosiendo',
        "en": 'he fell into the pool and we pulled him out',
        "fr": 'il est tombé dans la piscine',
        "de": 'er ist in den pool gefallen',
        "ru": 'он упал в бассейн',
        "ar": 'سقط في المسبح',
        "pt": 'caiu na piscina',
        "hi": 'वह पूल में गिर गया',
    },
    # ── Lote del 17-sep-2026 (madrugada): la LISTA PUBLICADA ──────────────────────────
    # Del índice del capítulo «Urgencias y emergencias» del manual y de los signos de
    # peligro del IMNCI. De 31 presentaciones, 23 salían rutina.
    "electric_shock": {
        "es": 'le ha dado la corriente con un enchufe',
        "en": 'he got an electric shock from a socket',
        "fr": "il a reçu une décharge électrique d'une prise",
        "de": 'er hat einen stromschlag von der steckdose bekommen',
        "ru": 'его ударило током от розетки',
        "ar": 'أصابته صعقة كهربائية من المقبس',
        "pt": 'levou um choque elétrico da tomada',
        "hi": 'उसे सॉकेट से बिजली का झटका लगा',
    },
    "foreign_body_nose_or_ear": {
        "es": 'se ha metido una bolita en la nariz',
        "en": 'he pushed a bead up his nose',
        "fr": 'il a mis une perle dans le nez',
        "de": 'er hat eine perle in die nase gesteckt',
        "ru": 'он засунул бусину в нос',
        "ar": 'أدخل خرزة في أنفه',
        "pt": 'enfiou uma bolinha no nariz',
        "hi": 'उसने नाक में मोती डाल लिया',
    },
    "spinal_injury": {
        "es": 'se cayó de espaldas y no mueve las piernas',
        "en": 'he fell on his back and cannot move his legs',
        "fr": 'il est tombé sur le dos et ne bouge plus les jambes',
        "de": 'er ist auf den rücken gefallen und bewegt die beine nicht',
        "ru": 'он упал на спину и не двигает ногами',
        "ar": 'سقط على ظهره ولا يحرك ساقيه',
        "pt": 'caiu de costas e não mexe as pernas',
        "hi": 'वह पीठ के बल गिरा और पैर नहीं हिला रहा',
    },
    "blunt_abdominal_trauma": {
        "es": 'le dio un golpe fuerte en la tripa con el manillar y le duele mucho',
        "en": 'he took a hard blow to the tummy from the handlebar and the pain is bad',
        "fr": 'il a reçu un coup violent au ventre avec le guidon et il a très mal',
        "de": 'er hat einen heftigen schlag mit dem lenker in den bauch bekommen und hat schmerzen',
        "ru": 'он получил сильный удар рулём в живот и сильно болит',
        "ar": 'تلقى ضربة قوية في البطن من المقود وعنده ألم شديد',
        "pt": 'levou uma pancada forte na barriga com o guiador e tem muita dor',
        "hi": 'हैंडल से पेट पर तेज़ चोट लगी और बहुत दर्द है',
    },
    "smoke_inhalation": {
        "es": 'ha respirado mucho humo en un incendio',
        "en": 'he breathed in a lot of smoke from a fire',
        "fr": 'il a respiré beaucoup de fumée dans un incendie',
        "de": 'er hat viel rauch bei einem brand eingeatmet',
        "ru": 'он надышался дымом при пожаре',
        "ar": 'استنشق دخانا كثيرا في حريق',
        "pt": 'respirou muito fumo num incêndio',
        "hi": 'आग में उसने बहुत धुआँ अंदर खींच लिया',
    },
    "bruising_and_pallor": {
        "es": 'le salen moratones sin darse golpes y está muy pálido',
        "en": 'she gets bruises without any knocks and is very pale',
        "fr": 'elle a des bleus sans choc et elle est très pâle',
        "de": 'sie bekommt blaue flecken ohne grund und ist sehr blass',
        "ru": 'у неё синяки без ушибов и она очень бледная',
        "ar": 'تظهر كدمات بدون ارتطام وهي شاحبة جدا',
        "pt": 'aparecem nódoas negras sem pancadas e está muito pálida',
        "hi": 'बिना चोट के नील पड़ते हैं और वह बहुत पीली है',
    },
    "hypoglycaemia": {
        "es": 'es diabético y está sudoroso y confuso',
        "en": 'he is diabetic and is sweaty and confused',
        "fr": 'il est diabétique, en sueur et confus',
        "de": 'er ist diabetiker, schwitzt und ist verwirrt',
        "ru": 'он диабетик, потеет и спутанный',
        "ar": 'هو مريض سكري ويتعرق ومشوش',
        "pt": 'é diabético e está suado e confuso',
        "hi": 'उसे मधुमेह है और पसीने में उलझन में है',
    },
    "sickle_cell_crisis": {
        "es": 'tiene anemia falciforme y un dolor muy fuerte en las piernas',
        "en": 'he has sickle cell and severe pain in his legs',
        "fr": 'il est drépanocytaire et a une douleur très forte aux jambes',
        "de": 'er hat sichelzellkrankheit und starke schmerzen in den beinen',
        "ru": 'у него серповидноклеточная анемия и сильная боль в ногах',
        "ar": 'عنده فقر الدم المنجلي وألم شديد في ساقيه',
        "pt": 'tem anemia falciforme e dor muito forte nas pernas',
        "hi": 'उसे सिकल सेल है और पैरों में तेज़ दर्द है',
    },
    "newborn_cold": {
        "es": 'mi recién nacido está frío y no entra en calor',
        "en": "my newborn is cold and won't warm up",
        "fr": 'mon nouveau-né est froid et ne se réchauffe pas',
        "de": 'mein neugeborenes ist kalt und wird nicht warm',
        "ru": 'мой новорождённый холодный и не согревается',
        "ar": 'مولودي بارد ولا يدفأ',
        "pt": 'o meu recém-nascido está frio e não aquece',
        "hi": 'मेरा नवजात ठंडा है और गर्म नहीं हो रहा',
    },
    "unable_to_drink_or_feed": {
        "es": 'no puede beber ni agarrarse al pecho',
        "en": 'he is unable to drink or breastfeed',
        "fr": 'il ne peut pas boire ni téter',
        "de": 'er kann nicht trinken oder saugen',
        "ru": 'он не может пить или сосать грудь',
        "ar": 'لا يستطيع الشرب أو الرضاعة',
        "pt": 'não consegue beber nem mamar',
        "hi": 'वह पी नहीं पा रहा और स्तनपान नहीं कर पा रहा',
    },
    "vomits_everything": {
        "es": 'vomita todo lo que le doy',
        "en": 'he vomits everything I give him',
        "fr": 'il vomit tout ce que je lui donne',
        "de": 'er erbricht alles',
        "ru": 'его рвёт всем, что даю',
        "ar": 'يتقيأ كل شيء أعطيه',
        "pt": 'vomita tudo o que lhe dou',
        "hi": 'जो भी देती हूँ सब उल्टी कर देता है',
    },
    "bilateral_oedema": {
        "es": 'tiene los dos pies hinchados',
        "en": 'both feet are swollen',
        "fr": 'les deux pieds sont gonflés',
        "de": 'beide füße sind geschwollen',
        "ru": 'обе стопы отекли',
        "ar": 'القدمين متورمتان',
        "pt": 'os dois pés estão inchados',
        "hi": 'दोनों पैर सूजे हुए हैं',
    },
    "sudden_pelvic_pain_adolescent": {
        "es": 'le ha dado de repente un dolor muy fuerte en el bajo vientre',
        "en": 'she has sudden severe lower belly pain',
        "fr": 'elle a une douleur brutale au bas-ventre',
        "de": 'sie hat plötzlich starke unterbauchschmerzen',
        "ru": 'у неё внезапная сильная боль внизу живота',
        "ar": 'عندها ألم مفاجئ شديد أسفل البطن',
        "pt": 'tem dor forte e repentina no baixo-ventre',
        "hi": 'उसे अचानक पेट के निचले हिस्से में तेज़ दर्द है',
    },
    "visible_severe_wasting": {
        "es": 'está muy delgado y no gana peso',
        "en": 'he is very thin and not gaining weight',
        "fr": 'il est très maigre et ne prend pas de poids',
        "de": 'er ist sehr dünn und nimmt nicht zu',
        "ru": 'он очень худой и не набирает вес',
        "ar": 'هو نحيف جدا ولا يزيد وزنه',
        "pt": 'está muito magro e não ganha peso',
        "hi": 'वह बहुत दुबला है और वज़न नहीं बढ़ रहा',
    },
}


def _pares() -> list[tuple[str, str, str]]:
    return [(regla, lg, frases[lg]) for regla, frases in CASOS.items() for lg in IDIOMAS]


@pytest.mark.parametrize("regla,lang,texto", _pares(), ids=lambda x: str(x)[:40])
def test_every_rule_fires_in_every_language(triaje: Triage, regla: str, lang: str, texto: str):
    r = triaje.assess(texto)
    ids = [m.id for m in r.matched]
    assert regla in ids, f"[{lang}] «{texto}» → {r.level} {ids}"


def test_the_battery_covers_every_rule_there_is(triaje: Triage) -> None:
    """Una regla nueva sin frases falla aquí en vez de irse callada a producción."""
    faltan = sorted({r.id for r in triaje.rules} - set(CASOS))
    assert not faltan, f"reglas sin frase de padre en la batería: {faltan}"
    sin_idioma = {r: sorted(set(IDIOMAS) - set(f)) for r, f in CASOS.items() if set(IDIOMAS) - set(f)}
    assert not sin_idioma, f"reglas sin todas las lenguas: {sin_idioma}"


#: Y la otra mitad: lo corriente sigue siendo corriente. Se añadieron más de doscientos patrones
#: en una tarde, y un triaje que salta con todo no avisa de nada.
CORRIENTE = [
    ("es", "mi hijo tiene mocos y tose un poco desde ayer"),
    ("es", "mi bebé llora mucho por las tardes, creo que son cólicos"),
    ("es", "le están saliendo los dientes y babea mucho"),
    ("es", "¿cuándo puedo empezar con la fruta?"),
    ("es", "tiene una costra en la rodilla de una caída de la semana pasada"),
    ("en", "my toddler has a runny nose and a mild cough"),
    ("en", "when can I start giving solids?"),
    ("en", "he is teething and drooling a lot"),
    ("en", "she has a small bruise on her leg from playing"),
    ("fr", "mon enfant a le nez qui coule depuis hier"),
    ("fr", "quand puis-je commencer la diversification ?"),
    ("de", "mein kind hat schnupfen und hustet ein bisschen"),
    ("de", "wann kann ich mit beikost anfangen?"),
    ("ru", "у ребёнка насморк и лёгкий кашель"),
    ("ru", "когда можно начинать прикорм?"),
    ("ar", "ابني عنده زكام وسعال خفيف"),
    ("ar", "متى أبدأ بالطعام الصلب؟"),
    ("pt", "o meu filho tem o nariz a pingar desde ontem"),
    ("pt", "quando posso começar a dar sólidos?"),
    ("hi", "मेरे बच्चे को हल्की खाँसी और नाक बह रही है"),
    ("hi", "ठोस आहार कब शुरू करें?"),
]


@pytest.mark.parametrize("lang,texto", CORRIENTE)
def test_an_ordinary_day_stays_ordinary(triaje: Triage, lang: str, texto: str) -> None:
    r = triaje.assess(texto)
    assert r.level == "routine", f"[{lang}] «{texto}» sale como {r.level}: {[m.id for m in r.matched]}"


# ── y las mismas frases, tecleadas deprisa ───────────────────────────────────────────────────
#
# Nadie pone las tildes a las tres de la mañana con un niño en brazos. Se cogieron las 408 frases
# y se les quitó lo que un padre se salta: las tildes, la ё rusa, la hamza y los harakat árabes,
# el nuqta devanagari. **23 dejaban de saltar, y 17 eran árabes.**
#
# No se arregló con patrones: el triaje ahora aplana la ortografía antes de mirar, igual que la
# búsqueda desde el 16-sep, y lo aplana en las DOS partes —el texto del padre y los patrones—.
# Esta prueba es la que vigila que siga siendo así; las variantes se generan, no se escriben.


def _descuidada(texto: str, lang: str) -> str:
    if lang == "ru":
        return texto.replace("ё", "е").lower()
    if lang == "ar":
        tabla = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ؤ": "و", "ئ": "ي", "ة": "ه", "ى": "ي"})
        return texto.translate(tabla).translate(dict.fromkeys(range(0x064B, 0x0653)))
    if lang == "hi":
        return "".join(c for c in unicodedata.normalize("NFD", texto) if c != "़")
    sin = unicodedata.normalize("NFD", texto)
    return "".join(c for c in sin if unicodedata.category(c) != "Mn").lower()


def _descuidadas() -> list[tuple[str, str, str]]:
    fuera = []
    for regla, frases in CASOS.items():
        for lg in IDIOMAS:
            floja = _descuidada(frases[lg], lg)
            if floja != frases[lg]:
                fuera.append((regla, lg, floja))
    return fuera


@pytest.mark.parametrize("regla,lang,texto", _descuidadas(), ids=lambda x: str(x)[:40])
def test_it_still_fires_when_typed_in_a_hurry(triaje: Triage, regla: str, lang: str, texto: str):
    r = triaje.assess(texto)
    assert regla in [m.id for m in r.matched], f"[{lang}] «{texto}» → {r.level}"


# ── y ahora dicho de OTRA manera ─────────────────────────────────────────────────────────────
#
# «Sigue depurando el triaje, no me puedo fiar de ti», 17-sep-2026. Con razón: la batería de
# arriba prueba UNA forma de decir cada cosa, y un padre no dice las cosas de una sola forma.
#
# Esta segunda batería dice lo mismo con otras palabras —más corto, más coloquial, con el orden
# cambiado— y al escribirla fallaban **121 de 408 casos**. Casi un tercio, con las reglas ya
# «cubiertas» en los ocho idiomas. Lo que faltaba no eran lenguas sino MANERAS:
#
#     severe_abdominal_pain   «está doblado del dolor» —la postura— no estaba en NINGUNA lengua
#     drowsy_irritable        la irritabilidad que no se calma con nada faltaba en siete
#     heatstroke              el NOMBRE de la cosa fallaba en siete: la regla lo pedía siempre
#                             acompañado de otra señal
#     mottled_skin            «se le han puesto los labios morados» —con verbo— en seis
#     choking                 «se atragantó CON una uva» pedía además que se dijera «no respira»
#     bilious_or_bloody_vomit «hay sangre EN el vómito», al revés, en tres
#
# Y al taparlas apareció lo contrario: «¿cómo prevenir un golpe de calor?» pasó a ser urgente.
# Eso lo arregló un guardián nuevo —lo hipotético— que mira si la frase pregunta cómo EVITAR algo
# en vez de contarlo, y que exige el interrogativo delante para que «no pude evitar que se
# tragara una pila» siga saltando.
SEGUNDA: dict[str, dict[str, str]] = {
    "not_responding": {
        "es": 'está inconsciente, no se despierta',
        "en": "he is unconscious and won't wake up",
        "fr": 'il est inconscient, il ne se réveille pas',
        "de": 'er ist bewusstlos und wacht nicht auf',
        "ru": 'он без сознания и не просыпается',
        "ar": 'فاقد الوعي ولا يستيقظ',
        "pt": 'está inconsciente e não acorda',
        "hi": 'वह बेहोश है और जाग नहीं रहा',
    },
    "seizure": {
        "es": 'está convulsionando ahora mismo',
        "en": 'she is having a fit right now',
        "fr": 'elle fait une crise convulsive en ce moment',
        "de": 'sie hat gerade einen anfall',
        "ru": 'у неё сейчас припадок',
        "ar": 'عندها تشنج الآن',
        "pt": 'está a ter uma convulsão agora',
        "hi": 'उसे अभी दौरा पड़ रहा है',
    },
    "severe_breathing": {
        "es": 'le cuesta mucho respirar, se ahoga',
        "en": 'he is really struggling to breathe',
        "fr": 'il a beaucoup de mal à respirer',
        "de": 'er bekommt kaum luft',
        "ru": 'ему очень трудно дышать',
        "ar": 'يعاني من صعوبة شديدة في التنفس',
        "pt": 'tem muita dificuldade em respirar',
        "hi": 'उसे साँस लेने में बहुत तकलीफ़ हो रही है',
    },
    "anaphylaxis": {
        "es": 'reacción alérgica con la cara hinchada y no respira bien',
        "en": "allergic reaction, his face is swollen and he can't breathe well",
        "fr": 'réaction allergique, le visage gonflé et il respire mal',
        "de": 'allergische reaktion, das gesicht ist geschwollen und er atmet schlecht',
        "ru": 'аллергическая реакция, лицо опухло и трудно дышать',
        "ar": 'رد فعل تحسسي، وجهه منتفخ ويتنفس بصعوبة',
        "pt": 'reação alérgica, a cara inchada e respira mal',
        "hi": 'एलर्जी की प्रतिक्रिया, चेहरा सूजा है और साँस ठीक से नहीं आ रही',
    },
    "choking": {
        "es": 'se ha atragantado con un trozo de manzana',
        "en": 'he choked on a piece of apple',
        "fr": "il s'est étouffé avec un morceau de pomme",
        "de": 'er hat sich an einem apfelstück verschluckt',
        "ru": 'он подавился куском яблока',
        "ar": 'اختنق بقطعة تفاح',
        "pt": 'engasgou-se com um pedaço de maçã',
        "hi": 'सेब का टुकड़ा गले में अटक गया और दम घुट रहा है',
    },
    "mottled_skin": {
        "es": 'se le han puesto los labios morados',
        "en": 'his lips have turned blue',
        "fr": 'ses lèvres sont devenues bleues',
        "de": 'seine lippen sind blau geworden',
        "ru": 'у него посинели губы',
        "ar": 'صارت شفتاه زرقاء',
        "pt": 'os lábios ficaram roxos',
        "hi": 'उसके होंठ नीले पड़ गए हैं',
    },
    "head_injury_loss_consciousness": {
        "es": 'se cayó de la cama y se quedó inconsciente un momento',
        "en": 'she fell off the bed and was knocked out for a moment',
        "fr": 'elle est tombée du lit et a perdu connaissance un instant',
        "de": 'sie ist aus dem bett gefallen und war kurz bewusstlos',
        "ru": 'она упала с кровати и на миг потеряла сознание',
        "ar": 'سقطت من السرير وفقدت الوعي لحظة',
        "pt": 'caiu da cama e ficou inconsciente um momento',
        "hi": 'वह बिस्तर से गिरी और एक पल के लिए बेहोश हो गई',
    },
    "severe_bleeding": {
        "es": 'sangra mucho y no para con presión',
        "en": 'it is bleeding heavily and pressure is not stopping it',
        "fr": "ça saigne beaucoup et la pression n'arrête rien",
        "de": 'es blutet stark und mit druck hört es nicht auf',
        "ru": 'сильно кровит и давление не помогает',
        "ar": 'ينزف بغزارة والضغط لا يوقفه',
        "pt": 'sangra muito e a pressão não para',
        "hi": 'बहुत ख़ून बह रहा है और दबाने से भी बंद नहीं हो रहा',
    },
    "open_fracture": {
        "es": 'fractura abierta en la pierna',
        "en": 'open fracture in his leg',
        "fr": 'fracture ouverte à la jambe',
        "de": 'offener bruch am bein',
        "ru": 'открытый перелом ноги',
        "ar": 'كسر مفتوح في الساق',
        "pt": 'fratura exposta na perna',
        "hi": 'पैर में खुला फ़्रैक्चर है',
    },
    "petechiae_fever": {
        "es": 'le han salido petequias con fiebre',
        "en": 'he has petechiae and a fever',
        "fr": 'il a des pétéchies avec de la fièvre',
        "de": 'er hat petechien und fieber',
        "ru": 'у него петехии и температура',
        "ar": 'ظهرت نمشات مع الحمى',
        "pt": 'apareceram petéquias com febre',
        "hi": 'बुखार के साथ पेटीकिया निकले हैं',
    },
    "button_battery": {
        "es": 'creo que se tragó la pila del mando',
        "en": 'I think he swallowed the battery from the remote',
        "fr": "je crois qu'il a avalé la pile de la télécommande",
        "de": 'ich glaube, er hat die batterie der fernbedienung verschluckt',
        "ru": 'кажется, он проглотил батарейку от пульта',
        "ar": 'أظنه ابتلع بطارية الريموت',
        "pt": 'acho que engoliu a pilha do comando',
        "hi": 'लगता है उसने रिमोट की बैटरी निगल ली',
    },
    "neck_stiffness": {
        "es": 'tiene la nuca rígida',
        "en": 'he has a stiff neck',
        "fr": 'il a la nuque raide',
        "de": 'er hat einen steifen nacken',
        "ru": 'у него ригидность затылочных мышц',
        "ar": 'رقبته متيبسة',
        "pt": 'tem o pescoço rígido',
        "hi": 'उसकी गर्दन अकड़ी हुई है',
    },
    "cannot_swallow_drooling": {
        "es": 'le cuesta mucho tragar y se le cae la baba',
        "en": 'he is dribbling and struggling to swallow',
        "fr": "il bave et n'arrive pas à avaler",
        "de": 'er sabbert und kann nicht schlucken',
        "ru": 'слюна течёт, он не может глотать',
        "ar": 'لعابه يسيل ولا يستطيع البلع',
        "pt": 'baba-se e não consegue engolir',
        "hi": 'लार गिर रही है और वह निगल नहीं पा रहा',
    },
    "infant_fever_under_3_months": {
        "es": 'mi recién nacido de 6 semanas tiene fiebre',
        "en": 'my 6 week old has a temperature',
        "fr": 'mon bébé de 6 semaines a de la fièvre',
        "de": 'mein 6 wochen altes baby hat fieber',
        "ru": 'у моего малыша 6 недель температура',
        "ar": 'طفلي عمره 6 أسابيع وعنده حمى',
        "pt": 'o meu bebé de 6 semanas tem febre',
        "hi": 'मेरे 6 हफ़्ते के बच्चे को बुखार है',
    },
    "very_high_fever": {
        "es": 'la fiebre le ha subido a 40,8',
        "en": 'his fever went up to 40.8',
        "fr": 'la fièvre est montée à 40,8',
        "de": 'das fieber ist auf 40,8 gestiegen',
        "ru": 'температура поднялась до 40,8',
        "ar": 'ارتفعت حرارته إلى 40.8',
        "pt": 'a febre subiu para 40,8',
        "hi": 'बुखार 40.8 तक चला गया',
    },
    "moderate_breathing": {
        "es": 'respira muy rápido desde hace un rato',
        "en": 'she has been breathing fast for a while',
        "fr": 'elle respire vite depuis un moment',
        "de": 'sie atmet seit einer weile schnell',
        "ru": 'она уже давно часто дышит',
        "ar": 'تتنفس بسرعة منذ فترة',
        "pt": 'respira depressa há algum tempo',
        "hi": 'वह कुछ देर से तेज़ साँस ले रही है',
    },
    "drowsy_irritable": {
        "es": 'está muy irritable y no se calma con nada',
        "en": 'he is extremely irritable and nothing settles him',
        "fr": 'il est très irritable et rien ne le calme',
        "de": 'er ist sehr reizbar und nichts beruhigt ihn',
        "ru": 'он очень раздражителен, ничто не успокаивает',
        "ar": 'هو عصبي جدا ولا شيء يهدئه',
        "pt": 'está muito irritável e nada o acalma',
        "hi": 'वह बहुत चिड़चिड़ा है और किसी से शांत नहीं हो रहा',
    },
    "dehydration": {
        "es": 'tiene los ojos hundidos y no llora con lágrimas',
        "en": 'her eyes look sunken and she cries without tears',
        "fr": 'ses yeux sont creusés et elle pleure sans larmes',
        "de": 'ihre augen sind eingesunken und sie weint ohne tränen',
        "ru": 'глаза запали и плачет без слёз',
        "ar": 'عيناها غائرتان وتبكي بلا دموع',
        "pt": 'tem os olhos encovados e chora sem lágrimas',
        "hi": 'उसकी आँखें धँसी हैं और बिना आँसू के रो रही है',
    },
    "vomiting_headache": {
        "es": 'le duele la cabeza y ha vomitado tres veces',
        "en": 'she has a bad headache and has vomited three times',
        "fr": 'elle a mal à la tête et a vomi trois fois',
        "de": 'sie hat kopfschmerzen und dreimal erbrochen',
        "ru": 'болит голова и три раза рвало',
        "ar": 'عندها صداع وتقيأت ثلاث مرات',
        "pt": 'tem dor de cabeça e vomitou três vezes',
        "hi": 'सिर में दर्द है और तीन बार उल्टी हुई',
    },
    "vomiting_after_head_injury": {
        "es": 'vomitó después del golpe en la cabeza',
        "en": 'he vomited after the bump on his head',
        "fr": 'il a vomi après le coup à la tête',
        "de": 'er hat nach dem schlag auf den kopf erbrochen',
        "ru": 'после удара по голове его вырвало',
        "ar": 'تقيأ بعد الضربة على رأسه',
        "pt": 'vomitou depois da pancada na cabeça',
        "hi": 'सिर पर चोट के बाद उल्टी हुई',
    },
    "foreign_body_ingestion": {
        "es": 'se ha tragado una moneda',
        "en": 'she swallowed a coin',
        "fr": 'elle a avalé une pièce de monnaie',
        "de": 'sie hat eine münze verschluckt',
        "ru": 'она проглотила монету',
        "ar": 'ابتلعت عملة معدنية',
        "pt": 'engoliu uma moeda',
        "hi": 'उसने सिक्का निगल लिया',
    },
    "poisoning": {
        "es": 'se ha tomado pastillas mías por error',
        "en": 'he took some of my pills by mistake',
        "fr": 'il a pris mes médicaments par erreur',
        "de": 'er hat aus versehen meine tabletten genommen',
        "ru": 'он по ошибке выпил мои таблетки',
        "ar": 'تناول حبوبي بالخطأ',
        "pt": 'tomou os meus comprimidos por engano',
        "hi": 'उसने ग़लती से मेरी गोलियाँ खा लीं',
    },
    "severe_abdominal_pain": {
        "es": 'está doblado del dolor de barriga',
        "en": 'he is doubled over with stomach pain',
        "fr": 'il est plié en deux par le mal de ventre',
        "de": 'er krümmt sich vor bauchschmerzen',
        "ru": 'он согнулся от боли в животе',
        "ar": 'ينحني من شدة ألم البطن',
        "pt": 'está dobrado com dor de barriga',
        "hi": 'पेट दर्द से वह दोहरा हुआ जा रहा है',
    },
    "newborn_refusing_feeds": {
        "es": 'mi bebé de 10 días no quiere mamar',
        "en": 'my 10 day old will not feed',
        "fr": 'mon bébé de 10 jours ne veut pas téter',
        "de": 'mein 10 tage altes baby will nicht trinken',
        "ru": 'мой ребёнок 10 дней не берёт грудь',
        "ar": 'طفلي عمره 10 أيام ويرفض الرضاعة',
        "pt": 'o meu bebé de 10 dias não quer mamar',
        "hi": 'मेरा 10 दिन का बच्चा दूध नहीं पी रहा',
    },
    "burn": {
        "es": 'se ha escaldado el brazo con la sopa',
        "en": 'he scalded his arm with soup',
        "fr": "il s'est ébouillanté le bras avec la soupe",
        "de": 'er hat sich den arm mit suppe verbrüht',
        "ru": 'он обварил руку супом',
        "ar": 'احترق ذراعه بالشوربة',
        "pt": 'escaldou o braço com a sopa',
        "hi": 'सूप से उसका हाथ जल गया',
    },
    "bilious_or_bloody_vomit": {
        "es": 'el vómito tiene sangre',
        "en": 'there is blood in his vomit',
        "fr": 'il y a du sang dans son vomi',
        "de": 'im erbrochenen ist blut',
        "ru": 'в рвоте кровь',
        "ar": 'في القيء دم',
        "pt": 'há sangue no vómito',
        "hi": 'उल्टी में ख़ून है',
    },
    "blood_in_stool": {
        "es": 'la caca es negra como alquitrán',
        "en": 'his poo is black and tarry',
        "fr": 'ses selles sont noires comme du goudron',
        "de": 'sein stuhl ist schwarz wie teer',
        "ru": 'стул чёрный, как дёготь',
        "ar": 'برازه أسود كالقطران',
        "pt": 'as fezes estão pretas como alcatrão',
        "hi": 'उसका मल काला और लसदार है',
    },
    "abdominal_pain_localised_or_worsening": {
        "es": 'el dolor se le ha ido al lado derecho de la tripa',
        "en": 'the pain has moved to the right side of his belly',
        "fr": 'la douleur est passée du côté droit du ventre',
        "de": 'der schmerz ist auf die rechte bauchseite gewandert',
        "ru": 'боль переместилась в правую сторону живота',
        "ar": 'انتقل الألم إلى الجهة اليمنى من البطن',
        "pt": 'a dor passou para o lado direito da barriga',
        "hi": 'दर्द पेट के दाहिनी ओर चला गया है',
    },
    "deformity_fracture": {
        "es": 'la muñeca le ha quedado deformada',
        "en": 'his wrist looks deformed',
        "fr": 'son poignet est déformé',
        "de": 'sein handgelenk ist verformt',
        "ru": 'запястье деформировано',
        "ar": 'معصمه مشوه',
        "pt": 'o pulso ficou deformado',
        "hi": 'उसकी कलाई टेढ़ी हो गई है',
    },
    "deep_wound": {
        "es": 'la herida es honda y creo que hay que coserla',
        "en": 'the wound is deep and I think it needs stitches',
        "fr": 'la plaie est profonde et il faut sans doute des points',
        "de": 'die wunde ist tief und muss wohl genäht werden',
        "ru": 'рана глубокая, наверное нужны швы',
        "ar": 'الجرح عميق وأظنه يحتاج غرزا',
        "pt": 'a ferida é funda e acho que precisa de pontos',
        "hi": 'घाव गहरा है और शायद टाँके लगेंगे',
    },
    "neuro_deficit": {
        "es": 'tiene la boca torcida y no ve bien',
        "en": 'his mouth is drooping and his vision is blurred',
        "fr": 'sa bouche est tordue et il voit flou',
        "de": 'sein mund hängt und er sieht verschwommen',
        "ru": 'рот перекошен и он плохо видит',
        "ar": 'فمه مائل ورؤيته ضبابية',
        "pt": 'a boca está torta e vê turvo',
        "hi": 'उसका मुँह टेढ़ा है और धुंधला दिख रहा है',
    },
    "headache_warning_signs": {
        "es": 'el dolor de cabeza va a peor cada día',
        "en": 'his headache is getting worse every day',
        "fr": 'son mal de tête empire chaque jour',
        "de": 'die kopfschmerzen werden jeden tag schlimmer',
        "ru": 'головная боль с каждым днём сильнее',
        "ar": 'الصداع يزداد سوءا كل يوم',
        "pt": 'a dor de cabeça piora todos os dias',
        "hi": 'सिरदर्द हर दिन बढ़ता जा रहा है',
    },
    "meningitis_signs": {
        "es": 'con fiebre, no aguanta la luz y le duele la cabeza',
        "en": 'with a fever, she cannot stand the light and her head hurts',
        "fr": 'avec de la fièvre, elle ne supporte pas la lumière et a mal à la tête',
        "de": 'mit fieber verträgt sie kein licht und hat kopfschmerzen',
        "ru": 'с температурой не переносит свет и болит голова',
        "ar": 'مع الحمى لا تحتمل الضوء ورأسها يؤلمها',
        "pt": 'com febre, não suporta a luz e dói-lhe a cabeça',
        "hi": 'बुखार के साथ रोशनी बर्दाश्त नहीं और सिर दर्द है',
    },
    "mastoiditis": {
        "es": 'detrás de la oreja lo tiene rojo e hinchado',
        "en": 'behind his ear is red and swollen',
        "fr": "derrière l'oreille c'est rouge et gonflé",
        "de": 'hinter dem ohr ist es rot und geschwollen',
        "ru": 'за ухом красное и припухшее',
        "ar": 'خلف أذنه أحمر ومتورم',
        "pt": 'atrás da orelha está vermelho e inchado',
        "hi": 'कान के पीछे लाल और सूजा हुआ है',
    },
    "blood_in_urine": {
        "es": 'el pis le sale rojo',
        "en": 'his wee is red',
        "fr": 'son pipi est rouge',
        "de": 'sein urin ist rot',
        "ru": 'моча красная',
        "ar": 'بوله أحمر',
        "pt": 'o xixi sai vermelho',
        "hi": 'उसका पेशाब लाल आ रहा है',
    },
    "fluid_from_ear_or_nose": {
        "es": 'le sale sangre del oído desde que se cayó',
        "en": 'blood is coming from his ear since he fell',
        "fr": 'du sang sort de son oreille depuis la chute',
        "de": 'seit dem sturz kommt blut aus dem ohr',
        "ru": 'после падения из уха идёт кровь',
        "ar": 'يخرج دم من أذنه بعد السقوط',
        "pt": 'sai sangue do ouvido desde a queda',
        "hi": 'गिरने के बाद कान से ख़ून आ रहा है',
    },
    "cold_extremities_with_fever": {
        "es": 'con 39 de fiebre y los pies helados',
        "en": '39 fever and his feet are freezing',
        "fr": '39 de fièvre et les pieds glacés',
        "de": '39 fieber und eiskalte füße',
        "ru": 'температура 39 и ледяные ноги',
        "ar": 'حرارته 39 وقدماه باردتان كالثلج',
        "pt": '39 de febre e os pés gelados',
        "hi": '39 बुखार और पैर बर्फ़ जैसे ठंडे',
    },
    "snakebite": {
        "es": 'una víbora le ha mordido en el pie',
        "en": 'a viper bit him on the foot',
        "fr": "une vipère l'a mordu au pied",
        "de": 'eine viper hat ihn in den fuß gebissen',
        "ru": 'гадюка укусила его в ногу',
        "ar": 'لدغته حية في قدمه',
        "pt": 'uma víbora mordeu-lhe o pé',
        "hi": 'साँप ने उसके पैर में काटा',
    },
    "mammal_bite": {
        "es": 'el gato del vecino le ha arañado y mordido',
        "en": "the neighbour's cat scratched and bit him",
        "fr": "le chat du voisin l'a griffé et mordu",
        "de": 'die katze des nachbarn hat ihn gekratzt und gebissen',
        "ru": 'соседская кошка поцарапала и укусила его',
        "ar": 'خدشته وعضته قطة الجيران',
        "pt": 'o gato do vizinho arranhou-o e mordeu-o',
        "hi": 'पड़ोसी की बिल्ली ने खरोंचा और काटा',
    },
    "lockjaw_spasms": {
        "es": 'tiene la mandíbula bloqueada',
        "en": 'his jaw is locked',
        "fr": 'sa mâchoire est bloquée',
        "de": 'sein kiefer ist verkrampft',
        "ru": 'челюсть свело',
        "ar": 'فكه مقفل',
        "pt": 'o maxilar está travado',
        "hi": 'उसका जबड़ा जकड़ गया है',
    },
    "heatstroke": {
        "es": 'golpe de calor después del partido',
        "en": 'heatstroke after the match',
        "fr": 'coup de chaleur après le match',
        "de": 'hitzschlag nach dem spiel',
        "ru": 'тепловой удар после матча',
        "ar": 'ضربة شمس بعد المباراة',
        "pt": 'golpe de calor depois do jogo',
        "hi": 'मैच के बाद लू लग गई',
    },
    "neonatal_jaundice": {
        "es": 'mi bebé de 5 días tiene los ojos amarillos',
        "en": 'my 5 day old has yellow eyes',
        "fr": 'mon bébé de 5 jours a les yeux jaunes',
        "de": 'mein 5 tage altes baby hat gelbe augen',
        "ru": 'у моего пятидневного малыша жёлтые глаза',
        "ar": 'طفلي عمره 5 أيام وعيناه صفراوان',
        "pt": 'o meu bebé de 5 dias tem os olhos amarelos',
        "hi": 'मेरे 5 दिन के बच्चे की आँखें पीली हैं',
    },
    "bleeding_with_fever": {
        "es": 'le sangran las encías y tiene fiebre',
        "en": 'his gums are bleeding and he has a fever',
        "fr": 'ses gencives saignent et il a de la fièvre',
        "de": 'sein zahnfleisch blutet und er hat fieber',
        "ru": 'дёсны кровоточат и температура',
        "ar": 'لثته تنزف وعنده حمى',
        "pt": 'as gengivas sangram e tem febre',
        "hi": 'मसूड़ों से ख़ून आ रहा है और बुखार है',
    },
    "suicidal_ideation": {
        "es": 'dice que quiere morirse',
        "en": 'he says he wants to die',
        "fr": "il dit qu'il veut mourir",
        "de": 'er sagt, er will sterben',
        "ru": 'он говорит, что хочет умереть',
        "ar": 'يقول إنه يريد أن يموت',
        "pt": 'diz que quer morrer',
        "hi": 'वह कहता है कि वह मरना चाहता है',
    },
    "self_harm": {
        "es": 'se corta con una cuchilla',
        "en": 'he cuts himself with a blade',
        "fr": 'il se coupe avec une lame',
        "de": 'er schneidet sich mit einer klinge',
        "ru": 'он режет себя лезвием',
        "ar": 'يجرح نفسه بشفرة',
        "pt": 'corta-se com uma lâmina',
        "hi": 'वह ब्लेड से ख़ुद को काटता है',
    },
    "eating_disorder_signs": {
        "es": 'ha dejado de comer y se salta todas las comidas',
        "en": 'she has stopped eating and skips every meal',
        "fr": 'elle a arrêté de manger et saute tous les repas',
        "de": 'sie isst nicht mehr und lässt jede mahlzeit aus',
        "ru": 'она перестала есть и пропускает все приёмы пищи',
        "ar": 'توقفت عن الأكل وتتخطى كل الوجبات',
        "pt": 'deixou de comer e salta todas as refeições',
        "hi": 'उसने खाना छोड़ दिया है और हर भोजन टाल देती है',
    },
    "bulging_fontanelle": {
        "es": 'la mollera la tiene hinchada y tensa',
        "en": 'the soft spot on his head is swollen and tense',
        "fr": 'la fontanelle est gonflée et tendue',
        "de": 'die fontanelle ist geschwollen und gespannt',
        "ru": 'родничок набух и напряжён',
        "ar": 'اليافوخ متورم ومتوتر',
        "pt": 'a fontanela está inchada e tensa',
        "hi": 'तालू फूला और तना हुआ है',
    },
    "testicular_pain": {
        "es": 'se queja de dolor fuerte en los testículos',
        "en": 'he is complaining of severe pain in his testicles',
        "fr": "il se plaint d'une forte douleur aux testicules",
        "de": 'er klagt über starke schmerzen an den hoden',
        "ru": 'жалуется на сильную боль в яичках',
        "ar": 'يشكو من ألم شديد في الخصيتين',
        "pt": 'queixa-se de dor forte nos testículos',
        "hi": 'वह अंडकोष में तेज़ दर्द की शिकायत कर रहा है',
    },
    "sudden_pallor": {
        "es": 'se quedó blanco como el papel de golpe',
        "en": 'he went white as a sheet all of a sudden',
        "fr": "il est devenu blanc comme un linge d'un coup",
        "de": 'er wurde auf einmal kreidebleich',
        "ru": 'он внезапно стал белым как бумага',
        "ar": 'صار أبيض فجأة',
        "pt": 'ficou branco como papel de repente',
        "hi": 'वह अचानक काग़ज़ जैसा सफ़ेद पड़ गया',
    },
    "unusual_cry": {
        "es": 'llora con un quejido muy débil, no es su llanto',
        "en": 'her cry is weak and not like her usual cry',
        "fr": "son cri est faible et ce n'est pas son cri habituel",
        "de": 'ihr weinen ist schwach und anders als sonst',
        "ru": 'плач слабый и не такой, как обычно',
        "ar": 'بكاؤها ضعيف وغير معتاد',
        "pt": 'o choro é fraco e diferente do habitual',
        "hi": 'उसका रोना कमज़ोर और रोज़ से अलग है',
    },
    "limp_with_fever": {
        "es": 'no quiere apoyar el pie y está con fiebre',
        "en": 'she refuses to put weight on her foot and has a fever',
        "fr": 'elle refuse de marcher sur son pied et a de la fièvre',
        "de": 'sie will das bein nicht belasten und hat fieber',
        "ru": 'она не наступает на ногу и у неё температура',
        "ar": 'ترفض المشي على قدمها وعندها حرارة',
        "pt": 'recusa apoiar o pé e tem febre',
        "hi": 'वह पैर पर वज़न नहीं डाल रही और बुखार है',
    },
    # ── Lote del 17-sep-2026: las diez urgencias que no tenían NINGUNA regla ──────────
    # Salieron de preguntar «¿qué reglas faltan?» en vez de «¿funcionan las que hay?».
    "stridor": {
        "es": 'le oigo estridor al respirar',
        "en": 'I can hear stridor when he breathes',
        "fr": "j'entends un stridor quand il respire",
        "de": 'ich höre einen stridor beim atmen',
        "ru": 'слышу стридор при дыхании',
        "ar": 'أسمع صريرا عند تنفسه',
        "pt": 'ouço estridor quando respira',
        "hi": 'साँस लेते समय स्ट्राइडर सुनाई देता है',
    },
    "intussusception": {
        "es": 'ha hecho una caca como jalea de grosella',
        "en": 'his poo looked like redcurrant jelly',
        "fr": 'ses selles sont comme de la gelée',
        "de": 'der stuhl ist wie gelee',
        "ru": 'стул как малиновое желе',
        "ar": 'برازه كالهلام',
        "pt": 'as fezes estão em geleia',
        "hi": 'उसका मल जेली जैसा है',
    },
    "projectile_vomiting_infant": {
        "es": 'el vómito sale disparado, no es un regurgito',
        "en": 'the vomit shoots out across the room',
        "fr": 'il vomit en jet',
        "de": 'er erbricht im hohen bogen',
        "ru": 'рвота фонтаном',
        "ar": 'يقذف الحليب بقوة',
        "pt": 'vomita em jato',
        "hi": 'फ़व्वारे जैसी उल्टी होती है',
    },
    "new_diabetes_signs": {
        "es": 'tiene mucha sed todo el día y ha adelgazado',
        "en": 'she is very thirsty all day and has lost weight',
        "fr": 'elle boit énormément et urine tout le temps',
        "de": 'sie trinkt literweise und muss ständig pinkeln',
        "ru": 'пьёт литрами и постоянно ходит в туалет',
        "ar": 'يشرب لترات ويتبول باستمرار',
        "pt": 'bebe litros e faz xixi o tempo todo',
        "hi": 'बहुत प्यास लगती है और बार-बार पेशाब आता है',
    },
    "inhaled_foreign_body": {
        "es": 'tos de golpe mientras comía una uva',
        "en": 'sudden cough while eating a grape',
        "fr": 'toux brutale en mangeant du raisin',
        "de": 'plötzlicher husten beim essen einer traube',
        "ru": 'внезапный кашель, когда ел виноград',
        "ar": 'سعال مفاجئ أثناء أكل عنب',
        "pt": 'tosse de repente a comer uva',
        "hi": 'अंगूर खाते समय अचानक खाँसी',
    },
    "asthma_not_responding": {
        "es": 'el inhalador no le hace efecto',
        "en": 'the ventolin is not working',
        "fr": "l'inhalateur ne fait rien",
        "de": 'der inhalator hilft nicht',
        "ru": 'вентолин не помогает',
        "ar": 'الفنتولين لا يفيد',
        "pt": 'a bombinha não faz efeito',
        "hi": 'पंप असर नहीं कर रहा',
    },
    "chemical_in_eye": {
        "es": 'se le ha metido detergente en el ojo',
        "en": 'detergent went into her eye',
        "fr": 'du détergent est entré dans son œil',
        "de": 'reiniger ist ins auge gekommen',
        "ru": 'моющее средство попало в глаза',
        "ar": 'دخل منظف في العين',
        "pt": 'entrou detergente no olho',
        "hi": 'आँख में साबुन का घोल चला गया',
    },
    "omphalitis": {
        "es": 'le sale pus del ombligo',
        "en": 'there is pus coming from the belly button',
        "fr": 'il y a du pus au nombril',
        "de": 'aus dem nabel kommt eiter',
        "ru": 'из пупка гной',
        "ar": 'يخرج قيح من السرة',
        "pt": 'sai pus do umbigo',
        "hi": 'नाभि से मवाद निकल रहा है',
    },
    "carbon_monoxide": {
        "es": 'nos duele la cabeza a todos desde que encendimos el brasero',
        "en": 'all of us have a headache since we lit the stove',
        "fr": 'monoxyde de carbone possible à la maison',
        "de": 'co-vergiftung möglich',
        "ru": 'возможно, угарный газ в доме',
        "ar": 'ربما تسمم بالغاز في البيت',
        "pt": 'pode ser monóxido de carbono em casa',
        "hi": 'घर में गैस से ज़हर हो सकता है',
    },
    "near_drowning": {
        "es": 'casi se ahoga en la bañera',
        "en": 'he nearly drowned in the bath',
        "fr": 'il a failli se noyer',
        "de": 'er ist fast ertrunken',
        "ru": 'он чуть не утонул',
        "ar": 'كاد يغرق',
        "pt": 'quase se afogou',
        "hi": 'वह डूबते-डूबते बचा',
    },
    # ── Lote del 17-sep-2026 (madrugada): la LISTA PUBLICADA ──────────────────────────
    # Del índice del capítulo «Urgencias y emergencias» del manual y de los signos de
    # peligro del IMNCI. De 31 presentaciones, 23 salían rutina.
    "electric_shock": {
        "es": 'se ha electrocutado con un cable',
        "en": 'he electrocuted himself on a wire',
        "fr": "il s'est électrocuté avec un câble",
        "de": 'er hat einen stromunfall mit einem kabel gehabt',
        "ru": 'у него электротравма от провода',
        "ar": 'تعرض لكهربة من سلك',
        "pt": 'eletrocutou-se com um cabo',
        "hi": 'तार से करंट लग गया',
    },
    "foreign_body_nose_or_ear": {
        "es": 'tiene un garbanzo en el oído',
        "en": 'there is a pea in his ear',
        "fr": "il a une graine dans l'oreille",
        "de": 'er hat eine erbse im ohr',
        "ru": 'у него горошина в ухе',
        "ar": 'في أذنه حبة',
        "pt": 'tem um grão no ouvido',
        "hi": 'उसके कान में दाना है',
    },
    "spinal_injury": {
        "es": 'después de la caída le duele mucho el cuello',
        "en": 'after the fall he cannot move his arms',
        "fr": 'après la chute il ne bouge plus les bras',
        "de": 'nach dem sturz bewegt er die arme nicht',
        "ru": 'после падения не двигает руками',
        "ar": 'بعد السقوط لا يحرك ذراعيه',
        "pt": 'depois da queda não mexe os braços',
        "hi": 'गिरने के बाद हाथ नहीं हिला रहा',
    },
    "blunt_abdominal_trauma": {
        "es": 'recibió una patada en la tripa y está pálido',
        "en": 'he was kicked in the stomach and looks pale',
        "fr": 'il a reçu un coup de pied dans le ventre et il est pâle',
        "de": 'er hat einen tritt in den bauch bekommen und ist blass',
        "ru": 'получил удар в живот и бледный',
        "ar": 'تلقى ركلة في البطن وهو شاحب',
        "pt": 'levou um pontapé na barriga e está pálido',
        "hi": 'पेट पर लात लगी और वह पीला है',
    },
    "smoke_inhalation": {
        "es": 'tragó humo en el incendio de la cocina',
        "en": 'he inhaled smoke in the kitchen fire',
        "fr": "il a inhalé de la fumée dans l'incendie",
        "de": 'er hat rauch eingeatmet',
        "ru": 'он вдохнул дым',
        "ar": 'شم دخانا كثيفا',
        "pt": 'inalou fumaça no incêndio',
        "hi": 'उसने धुआँ साँस में खींचा',
    },
    "bruising_and_pallor": {
        "es": 'le duelen los huesos por la noche y se despierta',
        "en": 'he has bone pain at night that wakes him up',
        "fr": 'il a des douleurs osseuses la nuit qui le réveillent',
        "de": 'er hat nachts knochenschmerzen',
        "ru": 'у него ночью боли в костях',
        "ar": 'عنده ألم في العظام ليلا',
        "pt": 'tem dor nos ossos à noite',
        "hi": 'उसे रात में हड्डी में दर्द होता है',
    },
    "hypoglycaemia": {
        "es": 'le ha bajado el azúcar y está temblando',
        "en": 'his blood sugar is low and he is shaking',
        "fr": 'il fait une hypoglycémie',
        "de": 'er hat eine unterzuckerung',
        "ru": 'у него гипогликемия',
        "ar": 'عنده هبوط السكر',
        "pt": 'tem hipoglicemia',
        "hi": 'उसकी शुगर कम हो गई है',
    },
    "sickle_cell_crisis": {
        "es": 'crisis de dolor por su drepanocitosis',
        "en": 'a pain crisis from his sickle cell disease',
        "fr": 'une crise douloureuse de sa drépanocytose',
        "de": 'eine schmerzkrise bei sichelzellkrankheit',
        "ru": 'болевой криз при серповидноклеточной анемии',
        "ar": 'نوبة ألم بسبب فقر الدم المنجلي',
        "pt": 'crise de dor pela anemia falciforme',
        "hi": 'सिकल सेल के कारण दर्द का संकट',
    },
    "newborn_cold": {
        "es": 'mi bebé de pocos días está muy frío',
        "en": "my newborn is cold to touch and won't warm up",
        "fr": 'mon nouveau-né est froid et ne se réchauffe pas du tout',
        "de": 'das neugeborene ist kalt und wird nicht warm',
        "ru": 'новорождённый холодный и не согревается совсем',
        "ar": 'رضيعي بارد ولا يدفأ أبدا',
        "pt": 'o recém-nascido está frio e não aquece',
        "hi": 'नवजात ठंडा है और बिल्कुल गर्म नहीं हो रहा',
    },
    "unable_to_drink_or_feed": {
        "es": 'no consigue agarrarse al pecho ni beber',
        "en": 'she cannot feed or drink at all',
        "fr": "elle n'arrive pas à boire ni à téter",
        "de": 'sie kann nicht an die brust und nicht trinken',
        "ru": 'она не может пить и не берёт грудь',
        "ar": 'لا تستطيع الرضاعة ولا الشرب',
        "pt": 'não consegue mamar nem beber',
        "hi": 'वह स्तनपान नहीं कर पा रही और पी नहीं पा रही',
    },
    "vomits_everything": {
        "es": 'no retiene nada, lo echa todo',
        "en": 'he keeps nothing down',
        "fr": 'il rend tout, il ne garde rien',
        "de": 'er behält nichts bei sich',
        "ru": 'ничего не удерживает',
        "ar": 'لا يحتفظ بشيء ويرجع كل شيء',
        "pt": 'não retém nada',
        "hi": 'कुछ भी नहीं टिक रहा',
    },
    "bilateral_oedema": {
        "es": 'se le han hinchado los pies, los dos',
        "en": 'both his ankles are swollen',
        "fr": 'les deux chevilles sont gonflées',
        "de": 'beide knöchel sind geschwollen',
        "ru": 'обе ноги отекли',
        "ar": 'الرجلين متورمتان',
        "pt": 'ambos os pés estão inchados',
        "hi": 'दोनों टखने सूजे हैं',
    },
    "sudden_pelvic_pain_adolescent": {
        "es": 'mi hija de 14 años tiene un dolor de ovario muy fuerte de repente',
        "en": 'my 14 year old has sudden severe pelvic pain',
        "fr": 'ma fille de 14 ans a une douleur pelvienne brutale',
        "de": 'meine 14-jährige hat plötzlich starke unterleibsschmerzen',
        "ru": 'у дочери 14 лет внезапная сильная боль внизу живота',
        "ar": 'ابنتي عمرها 14 سنة عندها ألم مفاجئ شديد أسفل البطن',
        "pt": 'a minha filha de 14 anos tem dor pélvica forte e repentina',
        "hi": 'मेरी 14 साल की बेटी को अचानक पेडू में तेज़ दर्द है',
    },
    "visible_severe_wasting": {
        "es": 'se le marcan las costillas y ha perdido peso',
        "en": 'his ribs are showing and he has lost weight',
        "fr": "il n'a que la peau et les os et perd du poids",
        "de": 'er ist nur haut und knochen und verliert gewicht',
        "ru": 'кожа да кости, и теряет вес',
        "ar": 'جلد وعظم وينقص وزنه',
        "pt": 'é pele e osso e está a perder peso',
        "hi": 'हड्डी दिख रही है और वज़न घट रहा है',
    },
}


def _pares_segunda() -> list[tuple[str, str, str]]:
    return [(regla, lg, frases[lg]) for regla, frases in SEGUNDA.items() for lg in IDIOMAS]


@pytest.mark.parametrize("regla,lang,texto", _pares_segunda(), ids=lambda x: str(x)[:40])
def test_it_also_fires_when_said_another_way(triaje: Triage, regla: str, lang: str, texto: str):
    r = triaje.assess(texto)
    assert regla in [m.id for m in r.matched], f"[{lang}] «{texto}» → {r.level}"


def test_the_second_battery_covers_the_same_rules(triaje: Triage) -> None:
    assert set(SEGUNDA) == set(CASOS), "las dos baterías tienen que cubrir las mismas reglas"


#: Preguntar cómo EVITAR algo no es que ese algo esté pasando. Salió al escribir «golpe de calor»
#: como patrón suelto: una pregunta de prevención pasó a urgente.
PREVENCION_NO_ES_URGENCIA = [
    ("es", "¿cómo prevenir un golpe de calor en verano?"),
    ("en", "how can I protect my child from heatstroke?"),
    ("fr", "comment éviter un coup de chaleur ?"),
    ("de", "wie kann ich einen hitzschlag verhindern?"),
    ("ru", "как предотвратить тепловой удар?"),
    ("ar", "كيف أحمي طفلي من ضربة الشمس؟"),
    ("pt", "como evitar um golpe de calor?"),
    ("hi", "गर्मी से कैसे बचाएँ?"),
    ("es", "¿cómo evito que se atragante con la comida?"),
    ("en", "how do I prevent choking with grapes?"),
]


@pytest.mark.parametrize("lang,texto", PREVENCION_NO_ES_URGENCIA)
def test_asking_how_to_prevent_it_is_not_an_emergency(triaje: Triage, lang: str, texto: str):
    r = triaje.assess(texto)
    assert r.level == "routine", f"[{lang}] «{texto}» → {r.level} {[m.id for m in r.matched]}"


#: Pero una hipótesis no puede tapar lo que ya ha pasado.
YA_HA_PASADO = [
    ("es", "no pude evitar que se tragara una pila"),
    ("es", "cómo evitar que se atragante, se ha atragantado con una uva"),
    ("es", "quería saber cómo prevenir. Ahora mismo está convulsionando"),
]


@pytest.mark.parametrize("lang,texto", YA_HA_PASADO)
def test_a_hypothesis_does_not_silence_what_already_happened(triaje: Triage, lang: str, texto: str):
    r = triaje.assess(texto)
    assert r.level in ("urgent", "emergency"), f"[{lang}] «{texto}» → {r.level}"


# ── y el mensaje corto, que es como se escribe en el móvil ───────────────────────────────────
#
# Las dos baterías de arriba escriben frases completas. A las tres de la mañana nadie escribe
# frases completas: se escribe «fiebre 39 y no se despierta», «sin pis desde ayer», «convulsión
# ahora». Con las diez reglas más graves fallaban 7 de 80, y cuatro eran el mismo fallo fino:
# **la negación ES la señal**. «Sin pis desde ayer» y «не может дышать» llevan la negación
# dentro, y el guardián que anula «sin fiebre» los apagaba. El guardián ya tenía la salvedad
# —si la coincidencia empieza por una negación, cuenta—, pero sólo sirve si el patrón se escribe
# incluyendo esa negación, y no estaba escrito así.
CORTO: dict[str, dict[str, str]] = {
    "not_responding": {
        "es": 'no responde',
        "en": 'not responding',
        "fr": 'ne répond pas',
        "de": 'reagiert nicht',
        "ru": 'не реагирует',
        "ar": 'لا يستجيب',
        "pt": 'não responde',
        "hi": 'कोई प्रतिक्रिया नहीं',
    },
    "seizure": {
        "es": 'convulsión ahora',
        "en": 'seizure now',
        "fr": 'convulsion maintenant',
        "de": 'krampfanfall jetzt',
        "ru": 'судороги сейчас',
        "ar": 'تشنج الآن',
        "pt": 'convulsão agora',
        "hi": 'अभी दौरा',
    },
    "severe_breathing": {
        "es": 'no puede respirar',
        "en": "can't breathe",
        "fr": "n'arrive pas à respirer",
        "de": 'bekommt keine luft',
        "ru": 'не может дышать',
        "ar": 'لا يستطيع التنفس',
        "pt": 'não consegue respirar',
        "hi": 'साँस नहीं ले पा रहा',
    },
    "choking": {
        "es": 'atragantado',
        "en": 'choking',
        "fr": "il s'étouffe",
        "de": 'erstickt',
        "ru": 'подавился',
        "ar": 'يختنق',
        "pt": 'engasgado',
        "hi": 'दम घुट रहा है',
    },
    "petechiae_fever": {
        "es": 'fiebre y manchas que no se van',
        "en": "fever and spots that don't fade",
        "fr": "fièvre et taches qui ne s'effacent pas",
        "de": 'fieber und flecken die nicht verschwinden',
        "ru": 'температура и пятна не исчезают',
        "ar": 'حمى وبقع لا تختفي',
        "pt": 'febre e manchas que não somem',
        "hi": 'बुखार और दाने जो नहीं मिटते',
    },
    "button_battery": {
        "es": 'pila de botón tragada',
        "en": 'swallowed button battery',
        "fr": 'pile bouton avalée',
        "de": 'knopfzelle verschluckt',
        "ru": 'проглотил батарейку',
        "ar": 'ابتلع بطارية',
        "pt": 'engoliu pilha de botão',
        "hi": 'बटन सेल निगल ली',
    },
    "infant_fever_under_3_months": {
        "es": '2 meses fiebre 38.5',
        "en": '2 months old fever 38.5',
        "fr": '2 mois fièvre 38,5',
        "de": '2 monate fieber 38,5',
        "ru": '2 месяца температура 38,5',
        "ar": 'شهرين حرارة 38.5',
        "pt": '2 meses febre 38,5',
        "hi": '2 महीने बुखार 38.5',
    },
    "neck_stiffness": {
        "es": 'nuca rígida y fiebre',
        "en": 'stiff neck and fever',
        "fr": 'nuque raide et fièvre',
        "de": 'steifer nacken und fieber',
        "ru": 'ригидность шеи и температура',
        "ar": 'تيبس الرقبة وحمى',
        "pt": 'pescoço rígido e febre',
        "hi": 'गर्दन अकड़ी और बुखार',
    },
    "dehydration": {
        "es": 'sin pis desde ayer',
        "en": 'no wet nappy since yesterday',
        "fr": 'pas de pipi depuis hier',
        "de": 'keine nasse windel seit gestern',
        "ru": 'не писает со вчера',
        "ar": 'لم يتبول منذ أمس',
        "pt": 'sem xixi desde ontem',
        "hi": 'कल से पेशाब नहीं',
    },
    "limp_with_fever": {
        "es": 'cojea y fiebre',
        "en": 'limping and fever',
        "fr": 'boite et fièvre',
        "de": 'hinkt und fieber',
        "ru": 'хромает и температура',
        "ar": 'يعرج وحمى',
        "pt": 'coxeia e febre',
        "hi": 'लंगड़ा और बुखार',
    },
}


def _pares_cortos() -> list[tuple[str, str, str]]:
    return [(regla, lg, frases[lg]) for regla, frases in CORTO.items() for lg in IDIOMAS]


@pytest.mark.parametrize("regla,lang,texto", _pares_cortos(), ids=lambda x: str(x)[:40])
def test_the_shortest_message_a_parent_would_send_still_fires(
    triaje: Triage, regla: str, lang: str, texto: str
):
    r = triaje.assess(texto)
    assert regla in [m.id for m in r.matched], f"[{lang}] «{texto}» → {r.level}"
