# La ficha de las tiendas — textos listos para pegar

> 19-sep-2026. Fase F6 del plan de `APP.md`. Está escrito para **pegarlo tal cual** en Play
> Console y en App Store Connect: cada bloque dice su campo y su límite de caracteres, y el
> texto ya cabe. Nada de esto necesita Android Studio, así que se puede dejar hecho mientras
> llega la máquina que compile.
>
> Lo que **no** está aquí y hay que hacer con la app delante: las capturas de pantalla. Se
> explica al final qué hacen falta exactamente.

---

## 1. Lo que las dos tiendas piden igual

| Campo | Valor |
|---|---|
| Nombre del paquete | `xyz.pedibot.app` |
| Categoría | Medicina (Play) · Medical (App Store) |
| Web | https://pedibot.xyz |
| Privacidad | https://pedibot.xyz/legal |
| Soporte | pedibot.ai@gmail.com |
| Precio | Gratis, sin compras dentro, sin anuncios |
| Idiomas de la ficha | inglés, español, francés, alemán, ruso, árabe, portugués, hindi |

---

## 2. Google Play

> **1-oct-2026: revisada para la app que de verdad se publica**, la TWA de `appgoogle.md` (la web
> abierta por Chrome, no la carcasa de Capacitor de septiembre). Cambia: las cifras (releídas de
> `DATOS.md`: 75 calendarios, 95 países con número, 26 organismos), lo de «sin cobertura» (lo
> guarda la web la primera vez que se abre con conexión, no viene dentro del paquete) y el
> formulario de datos (faltaban el identificador de la conversación y el recuento de visitas).
> Y una frase que no era verdad: «todas las respuestas llevan la fuente, con su año y su enlace».
> Desde el 25-ago el chat nombra al organismo dentro del texto y no enseña lista de fuentes; los
> documentos con su año y su enlace están en /sources. Google revisa que la ficha diga lo que
> hace la app, así que se dice lo que hace.

### Nombre de la app (30 caracteres)

```
PediBot: salud infantil
```

Inglés: `PediBot: child health`

### Descripción breve (80 caracteres)

**Español** (70):
```
Guías pediátricas citadas, vacunas y urgencias. Gratis y sin conexión.
```

**Inglés** (79):
```
Paediatric answers with sources, vaccines and emergency numbers. Free, offline.
```

**Francés** (77):
```
Réponses pédiatriques sourcées, vaccins et urgences. Gratuit, hors connexion.
```

**Alemán** (75):
```
Kindermedizin mit Quellen, Impfungen und Notrufnummern. Kostenlos, offline.
```

**Ruso** (71):
```
Детское здоровье с источниками, прививки и скорая. Бесплатно, без сети.
```

**Árabe** (72):
```
إجابات طب الأطفال بمصادرها، التطعيمات وأرقام الطوارئ. مجانا وبلا إنترنت.
```

**Portugués** (79):
```
Respostas pediátricas com fontes, vacinas e emergências. Grátis e sem internet.
```

**Hindi** (76):
```
स्रोत सहित बाल-स्वास्थ्य जवाब, टीके और आपातकालीन नंबर। मुफ़्त, बिना इंटरनेट।
```

### Descripción completa (4.000 caracteres)

**Español** (2005):

```
PediBot contesta preguntas sobre la salud de tu hijo con lo que dicen las guías pediátricas publicadas, y te enseña de dónde sale cada respuesta.

No es un médico y no diagnostica. Es la parte que suele faltar a las tres de la mañana: qué dicen las sociedades pediátricas y los servicios de salud sobre lo que te está pasando, dicho en tu idioma y nombrando quién lo dice.

QUÉ HACE

• Responde en ocho idiomas citando a 26 organismos; en español, la SEUP, la AEP, la OMS y MedlinePlus en español.
• Avisa cuando lo que cuentas encaja con un signo de alarma, y te da el número de emergencias de tu país.
• Calendario de vacunas de 75 países, transcrito de los documentos oficiales, con su fuente y su fecha.
• Curvas de crecimiento de la OMS: peso y talla de tu hijo, con su percentil.
• Calculadora de dosis de paracetamol e ibuprofeno por peso, con las marcas de tu país.
• Diario de síntomas y lista de «¿tengo que ir a urgencias?».

FUNCIONA SIN COBERTURA

La primera vez que la abres con conexión, guarda en el teléfono los números de emergencia de 95 países, los signos de alarma, los calendarios de vacunas y las tablas de crecimiento. Desde entonces abre sin cobertura y te dice lo que sabe. Sólo el chat necesita red.

TUS HIJOS, SI QUIERES

Puedes crear una cuenta gratuita y guardar la fecha de nacimiento de cada hijo. Entonces preguntas «¿qué vacunas le tocan a Laura?» y contesta por la edad de Laura. Puedes apuntar su peso y su talla y ver su curva, y llevarte las próximas vacunas al calendario del teléfono.

La cuenta es opcional: sin ella funciona todo igual. Lo que guardes puedes descargarlo o borrarlo cuando quieras, desde la propia app.

LO QUE NO HACE

No diagnostica. No sustituye a tu pediatra ni a urgencias. No tiene anuncios, no vende datos y no pide dinero. Si tu centro de salud dice otra cosa, tu centro de salud tiene razón.

Cada respuesta dice qué organismo lo dice, y la lista completa de documentos, con su año y su enlace, está en la propia app. Puedes comprobarlo.
```

**Inglés** (2019):

```
PediBot answers questions about your child's health using published paediatric guidance, and shows you where every answer comes from.

It is not a doctor and it does not diagnose. It is the part that tends to be missing at three in the morning: what the paediatric societies and health services actually say about what is happening, in your language, naming who says it.

WHAT IT DOES

• Answers in eight languages, quoting 26 health bodies; in English, the NHS, the CDC, MedlinePlus and the WHO.
• Warns you when what you describe matches a red flag, and gives you your country's emergency number.
• Vaccination schedules for 75 countries, transcribed from the official documents, with source and date.
• WHO growth charts: your child's weight and height, with percentile.
• Paracetamol and ibuprofen dosing by weight, with the brands sold in your country.
• Symptom diary and a "should I go to A&E?" checklist.

IT WORKS WITHOUT A SIGNAL

The first time you open it with a connection, it keeps on your phone the emergency numbers for 95 countries, the red-flag checklist, the vaccination schedules and the growth tables. From then on it opens with no signal and tells you what it knows. Only the chat needs the network.

YOUR CHILDREN, IF YOU WANT

You can create a free account and save each child's date of birth. Then you ask "what vaccines are due for Laura?" and it answers for Laura's age. You can record her weight and height and see her curve, and send the next appointments to your phone's calendar.

The account is optional: everything works without one. Whatever you save, you can download or delete whenever you like, from inside the app.

WHAT IT DOES NOT DO

It does not diagnose. It does not replace your paediatrician or the emergency department. No ads, no data selling, no payments. If your health service says something different, your health service is right.

Every answer names the body that says it, and the full list of documents, with their year and link, is inside the app. You can check it.
```

> 1-oct-2026: el operador aprobó las dos de arriba y pidió que **cada lengua nombre las fuentes
> que tiene en esa lengua**. Sacado del catálogo (`dataset/sources.json`, documentos por lengua):
> fr — OMS 41, Gobierno de Canadá 10 · de — RKI 30 · ru — OMS 47 · ar — OMS 47, Immunize.org 9 ·
> pt — Ministério da Saúde 14 · hi — Vikaspedia 19, Immunize.org 10 · es — OMS 40, MedlinePlus 31,
> SEUP 29, AEP · en — NHS 159, MedlinePlus 87, OMS 45, CDC 22. Las seis de abajo son traducción
> de la inglesa, con eso cambiado, el nombre de la niña del ejemplo puesto en cada lengua y
> «urgencias» dicho como se dice allí.

**Francés** (2209):

```
PediBot répond aux questions sur la santé de votre enfant à partir des recommandations pédiatriques publiées, et vous montre d'où vient chaque réponse.

Ce n'est pas un médecin et il ne pose pas de diagnostic. C'est ce qui manque souvent à trois heures du matin : ce que disent vraiment les sociétés de pédiatrie et les services de santé sur ce qui se passe, dans votre langue, en nommant qui le dit.

CE QU'IL FAIT

• Répond en huit langues en citant 26 organismes de santé ; en français, l'OMS et le gouvernement du Canada.
• Vous prévient quand ce que vous décrivez correspond à un signe d'alerte, et vous donne le numéro d'urgence de votre pays.
• Calendriers vaccinaux de 75 pays, transcrits des documents officiels, avec leur source et leur date.
• Courbes de croissance de l'OMS : le poids et la taille de votre enfant, avec son percentile.
• Doses de paracétamol et d'ibuprofène selon le poids, avec les marques vendues dans votre pays.
• Journal des symptômes et liste « dois-je aller aux urgences ? ».

IL FONCTIONNE SANS RÉSEAU

La première fois que vous l'ouvrez avec une connexion, il garde sur votre téléphone les numéros d'urgence de 95 pays, les signes d'alerte, les calendriers vaccinaux et les tables de croissance. Ensuite, il s'ouvre sans réseau et vous dit ce qu'il sait. Seul le chat a besoin d'internet.

VOS ENFANTS, SI VOUS LE SOUHAITEZ

Vous pouvez créer un compte gratuit et enregistrer la date de naissance de chaque enfant. Vous demandez alors « quels vaccins pour Léa ? » et il répond selon l'âge de Léa. Vous pouvez noter son poids et sa taille, voir sa courbe et envoyer les prochains rendez-vous dans l'agenda de votre téléphone.

Le compte est facultatif : tout fonctionne sans lui. Ce que vous enregistrez, vous pouvez le télécharger ou l'effacer quand vous voulez, depuis l'application.

CE QU'IL NE FAIT PAS

Il ne pose pas de diagnostic. Il ne remplace ni votre pédiatre ni les urgences. Pas de publicité, pas de revente de données, rien à payer. Si votre service de santé dit autre chose, c'est lui qui a raison.

Chaque réponse nomme l'organisme qui le dit, et la liste complète des documents, avec leur année et leur lien, est dans l'application. Vous pouvez vérifier.
```

**Alemán** (2121):

```
PediBot beantwortet Fragen zur Gesundheit Ihres Kindes mit dem, was veröffentlichte kinderärztliche Leitlinien sagen, und zeigt Ihnen, woher jede Antwort stammt.

Es ist kein Arzt und stellt keine Diagnosen. Es ist das, was um drei Uhr nachts oft fehlt: was Fachgesellschaften und Gesundheitsbehörden wirklich zu dem sagen, was gerade passiert, in Ihrer Sprache und mit dem Namen dessen, der es sagt.

WAS ES KANN

• Antwortet in acht Sprachen und zitiert 26 Gesundheitsorganisationen; auf Deutsch das Robert Koch-Institut.
• Warnt Sie, wenn das Beschriebene zu einem Warnzeichen passt, und nennt Ihnen die Notrufnummer Ihres Landes.
• Impfkalender für 75 Länder, aus den offiziellen Dokumenten übertragen, mit Quelle und Datum.
• WHO-Wachstumskurven: Gewicht und Größe Ihres Kindes, mit Perzentile.
• Paracetamol- und Ibuprofen-Dosis nach Gewicht, mit den Marken, die in Ihrem Land verkauft werden.
• Symptomtagebuch und die Liste „Muss ich in die Notaufnahme?“.

ES FUNKTIONIERT OHNE NETZ

Beim ersten Öffnen mit Verbindung speichert es auf Ihrem Telefon die Notrufnummern von 95 Ländern, die Warnzeichen, die Impfkalender und die Wachstumstabellen. Danach öffnet es sich auch ohne Netz und sagt Ihnen, was es weiß. Nur der Chat braucht Internet.

IHRE KINDER, WENN SIE MÖCHTEN

Sie können ein kostenloses Konto anlegen und das Geburtsdatum jedes Kindes speichern. Dann fragen Sie „Welche Impfungen braucht Lena jetzt?“ und es antwortet passend zu Lenas Alter. Sie können Gewicht und Größe notieren, ihre Kurve sehen und die nächsten Termine in den Kalender Ihres Telefons übernehmen.

Das Konto ist freiwillig: Ohne funktioniert alles genauso. Was Sie speichern, können Sie jederzeit in der App herunterladen oder löschen.

WAS ES NICHT TUT

Es stellt keine Diagnosen. Es ersetzt weder Ihre Kinderärztin oder Ihren Kinderarzt noch die Notaufnahme. Keine Werbung, kein Verkauf von Daten, nichts zu bezahlen. Wenn Ihre Gesundheitsstelle etwas anderes sagt, gilt sie.

Jede Antwort nennt die Organisation, die es sagt, und die vollständige Liste der Dokumente, mit Jahr und Link, ist in der App. Sie können es nachprüfen.
```

**Ruso** (1954):

```
PediBot отвечает на вопросы о здоровье вашего ребёнка по опубликованным педиатрическим рекомендациям и показывает, откуда взят каждый ответ.

Это не врач, и он не ставит диагнозов. Это то, чего часто не хватает в три часа ночи: что на самом деле говорят педиатрические общества и службы здравоохранения о происходящем, на вашем языке и с указанием, кто это говорит.

ЧТО ОН УМЕЕТ

• Отвечает на восьми языках, ссылаясь на 26 организаций здравоохранения; по-русски — на Всемирную организацию здравоохранения (ВОЗ).
• Предупреждает, если описанное похоже на тревожный признак, и даёт номер экстренной помощи вашей страны.
• Календари прививок 75 стран, переписанные из официальных документов, с источником и датой.
• Кривые роста ВОЗ: вес и рост вашего ребёнка с перцентилем.
• Дозы парацетамола и ибупрофена по весу, с марками, которые продаются в вашей стране.
• Дневник симптомов и список «нужно ли ехать в больницу?».

РАБОТАЕТ БЕЗ СВЯЗИ

При первом открытии с интернетом он сохраняет в телефоне номера экстренных служб 95 стран, тревожные признаки, календари прививок и таблицы роста. После этого он открывается без связи и говорит то, что знает. Интернет нужен только для чата.

ВАШИ ДЕТИ, ЕСЛИ ХОТИТЕ

Можно создать бесплатный аккаунт и сохранить дату рождения каждого ребёнка. Тогда вы спрашиваете «какие прививки нужны Маше?», и он отвечает по возрасту Маши. Можно записывать её вес и рост, смотреть её кривую и добавлять следующие визиты в календарь телефона.

Аккаунт не обязателен: без него всё работает так же. Всё сохранённое можно скачать или удалить в любой момент прямо в приложении.

ЧЕГО ОН НЕ ДЕЛАЕТ

Он не ставит диагнозов. Он не заменяет вашего педиатра и приёмное отделение. Без рекламы, без продажи данных, ничего платить не нужно. Если в вашей поликлинике говорят иначе, права поликлиника.

Каждый ответ называет организацию, которая это говорит, а полный список документов с годом и ссылкой есть в приложении. Это можно проверить.
```

**Árabe** (1493):

```
يجيب PediBot عن أسئلتك حول صحة طفلك بما تقوله إرشادات طب الأطفال المنشورة، ويُريك من أين جاءت كل إجابة.

ليس طبيبا ولا يشخّص. إنه ما يغيب عادة في الثالثة فجرا: ما تقوله فعلا جمعيات طب الأطفال والجهات الصحية عمّا يحدث، بلغتك، مع ذكر من يقوله.

ماذا يفعل

• يجيب بثماني لغات مستشهدا بـ 26 جهة صحية؛ وبالعربية: منظمة الصحة العالمية، ونشرات معلومات اللقاحات المترجمة إلى العربية من Immunize.org.
• ينبّهك عندما يطابق ما تصفه علامة خطر، ويعطيك رقم الطوارئ في بلدك.
• جداول التطعيم لـ 75 بلدا، منقولة من الوثائق الرسمية، مع مصدرها وتاريخها.
• منحنيات النمو لمنظمة الصحة العالمية: وزن طفلك وطوله مع المئين.
• جرعات الباراسيتامول والإيبوبروفين حسب الوزن، مع الأسماء التجارية المبيعة في بلدك.
• مفكرة للأعراض وقائمة «هل أذهب إلى الطوارئ؟».

يعمل بلا إنترنت

في أول مرة تفتحه وأنت متصل، يحفظ في هاتفك أرقام الطوارئ في 95 بلدا وعلامات الخطر وجداول التطعيم وجداول النمو. بعدها يفتح بلا إنترنت ويخبرك بما يعرفه. المحادثة وحدها تحتاج إلى الشبكة.

أطفالك، إن شئت

يمكنك إنشاء حساب مجاني وحفظ تاريخ ميلاد كل طفل. ثم تسأل «ما اللقاحات المستحقة لليلى؟» فيجيب حسب عمر ليلى. ويمكنك تسجيل وزنها وطولها ورؤية منحناها، وإضافة المواعيد القادمة إلى تقويم هاتفك.

الحساب اختياري: كل شيء يعمل من دونه. ما تحفظه يمكنك تنزيله أو حذفه متى شئت من داخل التطبيق.

ما لا يفعله

لا يشخّص. لا يغني عن طبيب طفلك ولا عن قسم الطوارئ. لا إعلانات، لا بيع للبيانات، لا شيء تدفعه. إذا قال لك مركزك الصحي غير ذلك، فالقول قوله.

كل إجابة تذكر الجهة التي تقول ذلك، والقائمة الكاملة للوثائق، بسنتها ورابطها، موجودة في التطبيق. يمكنك التحقق.
```

**Portugués** (1989):

```
O PediBot responde a perguntas sobre a saúde do seu filho com o que dizem as diretrizes pediátricas publicadas, e mostra de onde vem cada resposta.

Não é um médico e não faz diagnósticos. É o que costuma faltar às três da manhã: o que as sociedades de pediatria e os serviços de saúde dizem de verdade sobre o que está acontecendo, na sua língua e dizendo quem o diz.

O QUE FAZ

• Responde em oito línguas citando 26 organismos de saúde; em português, o Ministério da Saúde do Brasil.
• Avisa quando o que você descreve corresponde a um sinal de alarme, e dá o número de emergência do seu país.
• Calendários de vacinação de 75 países, transcritos dos documentos oficiais, com fonte e data.
• Curvas de crescimento da OMS: o peso e a altura do seu filho, com o percentil.
• Doses de paracetamol e ibuprofeno pelo peso, com as marcas vendidas no seu país.
• Diário de sintomas e a lista «preciso ir ao pronto-socorro?».

FUNCIONA SEM SINAL

Na primeira vez que você abre o app com conexão, ele guarda no celular os números de emergência de 95 países, os sinais de alarme, os calendários de vacinação e as tabelas de crescimento. A partir daí, abre sem sinal e diz o que sabe. Só o chat precisa de internet.

OS SEUS FILHOS, SE QUISER

Você pode criar uma conta gratuita e guardar a data de nascimento de cada filho. Depois pergunta «quais vacinas a Ana precisa tomar?» e ele responde pela idade da Ana. Você pode registrar o peso e a altura, ver a curva e enviar as próximas consultas para a agenda do celular.

A conta é opcional: sem ela tudo funciona igual. O que você guardar pode ser baixado ou apagado quando quiser, dentro do próprio app.

O QUE NÃO FAZ

Não faz diagnósticos. Não substitui o seu pediatra nem o pronto-socorro. Sem anúncios, sem venda de dados, nada a pagar. Se o seu serviço de saúde disser outra coisa, vale o que ele diz.

Cada resposta diz o organismo que o afirma, e a lista completa dos documentos, com o ano e o link, está dentro do app. Você pode conferir.
```

**Hindi** (2074):

```
PediBot आपके बच्चे की सेहत से जुड़े सवालों का जवाब प्रकाशित बाल-रोग दिशानिर्देशों के आधार पर देता है, और दिखाता है कि हर जवाब कहाँ से आया है।

यह डॉक्टर नहीं है और बीमारी का निदान नहीं करता। यह वह चीज़ है जो रात के तीन बजे अक्सर नहीं मिलती: बाल-रोग संस्थाएँ और स्वास्थ्य सेवाएँ जो हो रहा है उसके बारे में सच में क्या कहती हैं, आपकी भाषा में, और यह बताते हुए कि कौन कह रहा है।

यह क्या करता है

• आठ भाषाओं में जवाब देता है और 26 स्वास्थ्य संस्थाओं का हवाला देता है; हिंदी में विकासपीडिया (भारत सरकार का पोर्टल) और Immunize.org के हिंदी टीका-सूचना पत्रक।
• जब आपकी बताई बात किसी ख़तरे के संकेत से मेल खाती है तो चेतावनी देता है, और आपके देश का आपातकालीन नंबर बताता है।
• 75 देशों की टीकाकरण अनुसूची, आधिकारिक दस्तावेज़ों से उतारी हुई, स्रोत और तारीख़ के साथ।
• विश्व स्वास्थ्य संगठन के विकास चार्ट: आपके बच्चे का वज़न और लंबाई, पर्सेंटाइल के साथ।
• वज़न के हिसाब से पैरासिटामोल और आइबुप्रोफ़ेन की ख़ुराक, आपके देश में बिकने वाले ब्रांडों के साथ।
• लक्षणों की डायरी और «क्या मुझे अस्पताल की इमरजेंसी जाना चाहिए?» सूची।

बिना नेटवर्क के भी चलता है

जब आप इसे पहली बार इंटरनेट के साथ खोलते हैं, तो यह आपके फ़ोन में 95 देशों के आपातकालीन नंबर, ख़तरे के संकेत, टीकाकरण अनुसूचियाँ और विकास तालिकाएँ रख लेता है। उसके बाद यह बिना नेटवर्क के भी खुलता है और बताता है कि उसे क्या पता है। सिर्फ़ चैट को इंटरनेट चाहिए।

आपके बच्चे, अगर आप चाहें

आप मुफ़्त खाता बनाकर हर बच्चे की जन्मतिथि सहेज सकते हैं। फिर आप पूछते हैं «प्रिया को कौन-से टीके लगने हैं?» और यह प्रिया की उम्र के हिसाब से जवाब देता है। आप उसका वज़न और लंबाई लिख सकते हैं, उसका चार्ट देख सकते हैं, और अगली तारीख़ें फ़ोन के कैलेंडर में भेज सकते हैं।

खाता वैकल्पिक है: उसके बिना भी सब कुछ वैसे ही चलता है। जो भी आप सहेजें, उसे ऐप के अंदर से जब चाहें डाउनलोड या मिटा सकते हैं।

यह क्या नहीं करता

यह निदान नहीं करता। यह आपके बाल-रोग डॉक्टर या अस्पताल की इमरजेंसी की जगह नहीं लेता। कोई विज्ञापन नहीं, डेटा की बिक्री नहीं, कोई भुगतान नहीं। अगर आपका स्वास्थ्य केंद्र कुछ और कहे, तो वही सही है।

हर जवाब बताता है कि यह बात कौन-सी संस्था कहती है, और सभी दस्तावेज़ों की पूरी सूची, साल और लिंक के साथ, ऐप में ही है। आप जाँच सकते हैं।
```

### Gráfico destacado (1.024 × 500)

**Hecho el 1-oct-2026:** `app/assets/play-feature-1024x500.png`. Es la tarjeta de compartir (ya
aprobada por el operador) reencuadrada; la saca `scripts/make_icons.py` junto con los iconos, así
que si cambia el logo cambia con él.

### Formulario «Data safety»

Lo que hay que marcar, y por qué. Esto no se improvisa el día del envío:

| Pregunta | Respuesta |
|---|---|
| ¿Recoge datos? | **Sí** |
| Personal info → Email address | Recogido · obligatorio sólo si el usuario crea cuenta · para gestionar la cuenta · **no compartido** |
| Personal info → Name | Recogido (el nombre del hijo, que lo escribe el usuario) · opcional · funcionalidad de la app · **no compartido** |
| Health and fitness → Health info | Recogido (la pregunta del chat, el peso y la talla) · para funcionalidad de la app · **compartido con un proveedor de modelo de lenguaje** para redactar la respuesta |
| Device or other IDs | Recogido (el identificador de la conversación que el chat guarda en el teléfono para unir una pregunta con la siguiente) · funcionalidad de la app · **no compartido** |
| App activity → App interactions | Recogido (páginas vistas y si una respuesta fue útil; las visitas se cuentan con una huella de IP y navegador sacada del registro del servidor, sin herramienta de terceros) · **analítica** · **no compartido** |
| ¿Cifrado en tránsito? | Sí, todo por HTTPS |
| ¿Se puede pedir el borrado? | **Sí**, desde la propia app, sin escribirnos (cuenta, hijos y medidas) |
| ¿Hay publicidad o analítica de terceros? | No |

> 1-oct-2026: añadidas las dos filas de arriba. En septiembre se declaraba sólo correo, nombre y
> salud, y la app guarda además el identificador de la conversación y cuenta visitas. Google
> pide declarar también lo que se recoge para uso propio, aunque no salga del servidor.
> Pendiente de confirmar al rellenarlo: si Google pide declarar la IP del registro del servidor
> como dato aparte; hoy sólo se usa para contar visitantes, cifrada en una huella.

### Declaración de app de salud

Categoría: **información de salud**, no app clínica. PediBot transcribe y cita guías publicadas;
no diagnostica, no mide nada con los sensores del teléfono y no sustituye a un profesional. La
página `https://pedibot.xyz/legal` lo dice con esas palabras y en los ocho idiomas.

En el formulario de Play («Health apps»), la casilla que encaja es **«Health & fitness → Medical
reference and education»** (información y referencia médica). NO marcar «diagnóstico», «gestión
de enfermedades» ni «dispositivo médico». Si pide aviso legal: «PediBot provides general
information from published paediatric guidelines. It is not medical advice, does not diagnose,
and does not replace your paediatrician.» (es el `footer_legal` de la web, palabra por palabra).

### Clasificación por edad (IARC)

Hay «información médica o de tratamiento» → sale una edad recomendada más alta. No es un
problema: es una casilla y hay que responderla como es.

Respuestas del cuestionario, para no improvisarlas:

| Pregunta | Respuesta |
|---|---|
| Categoría | **Referencia, noticias o educación** (no «juego», no «red social») |
| Violencia, sexo, lenguaje, drogas, apuestas | **No** a todo |
| ¿Los usuarios pueden interactuar o intercambiar contenido entre ellos? | **No** (el chat es con PediBot; nadie ve lo de otro) |
| ¿Comparte la ubicación del usuario? | **No** (el país lo elige el usuario; no se pide la ubicación) |
| ¿Permite compras digitales? | **No** |
| ¿Contiene información médica o de tratamiento? | **Sí** |

---

## 3. App Store

### Nombre (30) y subtítulo (30)

```
PediBot
```
```
Salud infantil con fuentes
```

Inglés: `Child health, with sources`

### Palabras clave (100 caracteres, separadas por comas, sin repetir el nombre)

**Español** (96):
```
pediatría,fiebre,vacunas,bebé,urgencias,niños,percentiles,dosis,pediatra,tos,vómitos,crecimiento
```

**Inglés** (94):
```
paediatrics,fever,vaccines,baby,emergency,children,percentile,dosage,pediatrician,cough,growth
```

### Texto promocional (170, se puede cambiar sin revisión)

```
Ahora con la ficha de cada hijo: su edad, su curva de crecimiento y las vacunas que le tocan, con fecha. Y los números de emergencia de 88 países, también sin cobertura.
```

### Descripción

La misma de Play, quitando las viñetas con `•` si el revisor las marca (no suele). App Store no
tiene límite corto de descripción.

### Etiqueta de privacidad (App Privacy)

| Tipo de dato | Uso | ¿Vinculado a la identidad? | ¿Seguimiento? |
|---|---|---|---|
| Contact Info → Email | Funcionalidad de la app | **Sí** (hay cuenta) | No |
| Health & Fitness → Health | Funcionalidad de la app | Sí | No |
| User Content → Other | Funcionalidad de la app | Sí | No |
| Identifiers | — | — | — |

Sin SDK de publicidad, sin analítica de terceros, sin identificador de dispositivo.

### Notas para el revisor (el campo que decide la mitad de los rechazos)

```
PediBot is an information app for parents. It transcribes and quotes published paediatric guidance (NHS, CDC, WHO, AAP, SEUP, AEP and others) and always shows the source, the year and a link to the original document. It does not diagnose and it says so on every screen and in its legal page (https://pedibot.xyz/legal).

Two points about the App Review Guidelines:

1.4.2 — This version of the iOS app does NOT include the weight-based drug dosage calculator that the website offers. We removed it deliberately because the calculator does not come from a drug manufacturer, hospital, university, pharmacy or approved entity. The app shows dosing information only as it is published by the source, without calculating.

4.2 — The app is not a repackaged website. Emergency numbers for 88 countries, the red-flag checklist, 61 vaccination schedules and the WHO growth tables are bundled inside the app and work with no network at all: put the device in airplane mode and open it. It also schedules local notifications for each child's vaccination appointments, which a website cannot do.

There is no account needed to use the app. An optional free account stores a child's date of birth and measurements so the app can answer by their age; it can be deleted from inside the app at any time.

Test account, if you want one: (crear una en la propia app; no hay verificación por correo, así que cualquier dirección funciona)
```

---

## 4. Las capturas

> **Google Play, hechas el 1-oct-2026** en el emulador (Android 15, 1080 × 2400), con la app de
> verdad instalada, en inglés. En `app/assets/play-screens/`, en este orden:
>
> 1. `play-0-chat.png` — el chat contestando una fiebre de 39 en un niño de 2 años, nombrando a
>    la SEUP.
> 2. `play-1-urgencias.png` — urgencias de Kenia: 999, de dónde sale el número y los signos de
>    alarma.
> 3. `play-2-vacunas.png` — el calendario de Kenia por edades.
> 4. `play-3-dosis.png` — la calculadora: Calpol para 14 kg, en mg y en ml por concentración, con
>    la guía de la AEPap citada.
> 5. `play-5-sin-red.png` — **en modo avión** (se ve el avión arriba): el buscador de urgencias
>    con el número del país. Es la que dice que esto es una app y no una web.
>
> Los ceros salen tachados («1Ø»): es la tipografía Atkinson Hyperlegible, hecha para baja visión,
> que tacha el cero a propósito. Igual que en la web; no es un fallo. Lo de abajo es el plan de
> septiembre, para cuando se haga la versión de iPhone.

Cinco por plataforma, en este orden, y hay que hacerlas **con la app funcionando**, no montadas:

1. **El chat contestando una pregunta con su fuente.** Es lo que la distingue de todo lo demás.
2. **El aviso rojo con el número de emergencias**, en modo avión, para que se vea que funciona
   sin red. Es la captura que también sirve de respuesta a la 4.2.
3. **La ficha de un hijo con su curva de crecimiento** sobre las bandas de la OMS.
4. **El calendario de vacunas de ese hijo, con fechas.**
5. **El calendario vacunal de un país** con su fuente oficial citada al pie.

Tamaños: Play pide 1.080 × 1.920 como mínimo y admite hasta ocho; Apple pide las de 6,7" y 6,5"
(1.290 × 2.796 y 1.242 × 2.688). Se sacan del propio teléfono, no de un emulador, porque el
emulador pinta las tipografías distinto.

---

## 5. Antes de darle a enviar

- [ ] La cuenta de Play abierta y pagada (25 $, una vez) — **decisión D-A1: personal**
- [ ] Doce probadores apuntados y **catorce días seguidos** corriendo
- [ ] La cuenta de Apple abierta (99 $/año)
- [ ] La app compilada en una máquina con JDK 17 y Android Studio (ver `app/README.md`)
- [ ] Las cinco capturas hechas en un teléfono de verdad
- [ ] El gráfico destacado de Play (1.024 × 500)
- [ ] Las seis traducciones de la descripción larga
- [ ] La calculadora de dosis **fuera** de la versión de iOS (D-A2)
- [ ] Recuperación de contraseña funcionando (I-20): hoy quien la pierde no puede recuperarla, y
      eso en una app con cuenta es una queja de una estrella el primer día
