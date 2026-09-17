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
