# What PediBot is, and what it can and cannot do

Facts about this service. Numbers in braces are filled in from the running system, so they are
never out of date. Everything here must stay true: if the service changes, this file changes with
it (`tests/test_the_card_about_pedibot_is_true.py` checks the parts that can be checked).

## What it is

- PediBot is a free website, pedibot.xyz, that answers questions about the health of babies and
  children using only published paediatric guidelines, and shows which document each sentence
  comes from.
- It is not a doctor. It does not diagnose, does not prescribe and does not replace a
  paediatrician, a nurse or the emergency services.
- It needs no account and asks for no personal data. There are no ads and nothing is sold.
- Who makes it and how it is paid for: pedibot.xyz/about. Legal notice and privacy:
  pedibot.xyz/legal.

## How an answer is made

1. Fixed rules, not AI, read the message first looking for danger signs ({rules} rules, in every
   language the site speaks). When one matches, a warning appears above the answer saying whether
   to call an ambulance, go today or watch at home, with the emergency number of the country.
2. It then searches its own library of {docs} documents, already downloaded and indexed on the
   server. It does not browse the internet when you ask, and it does not use a search engine.
3. An AI writes the answer using only the passages it found, and each source is shown underneath
   with a link to the original document.
4. A second AI step checks the draft before it is shown, and the answer is rewritten if it does
   not answer what was asked.
5. If the library has nothing about the question, it says so instead of inventing an answer.

## Where the information comes from

- The World Health Organization, the NHS (United Kingdom), the CDC and the American Academy of
  Pediatrics (United States), the Spanish Association of Paediatrics (AEP), its primary care
  branch (AEPap) and the Spanish paediatric emergency society (SEUP), the Spanish medicines
  agency (AEMPS) and regional health services, ECIMED (Cuba), the Catholic University of Chile,
  the National Health Mission (India), the Brazilian health ministry, MedlinePlus and Canadian
  public health.
- Every document it is allowed to quote is listed, with organisation, title, year, language and a
  link to the original, at pedibot.xyz/sources.
- The documents are checked once a week to see whether the original page has changed.

## Languages

- The site itself is in eight languages: Spanish, English, French, German, Russian, Arabic,
  Portuguese and Hindi.
- If you write in another language, the answer is written in the language you wrote in. The fixed
  safety warning above it appears in English (and in Swahili, which the danger rules also speak).
- It understands messages without accents, with spelling mistakes, in capitals, very short, or
  mixing two languages. The brand names it knows are the ones for paracetamol and ibuprofen
  (Calpol, Apiretal, Dalsy, Nurofen, Tylenol…), misspelled too; for any other medicine it can
  only say what the guidelines in its library say, and it does not hold a drug dictionary.
- You can ask it to answer in another language ("answer me in French") and it will.

## What it needs to answer well

- The child's age. Much of what the guidelines say changes with age, and under three months
  almost everything is different.
- The weight, only for a dose. Without a weight it cannot calculate one, and it says so instead
  of guessing.
- The country, to give the right emergency number ({countries} countries) and the right
  vaccination schedule ({vax} countries). You can choose it at the top of the chat.
- If you give data that contradicts itself, or a weight that is impossible for the age, it uses
  the last thing you said and asks.

## Memory

- Inside one conversation it remembers what you already told it, so follow-up questions do not
  need the whole story again ("and now what do I do?" works).
- If you change the subject, it starts fresh on purpose: the age of one child does not leak into
  a question about another problem.
- That memory lasts 24 hours. It does not recognise you from one day to the next, and it never
  knows who you are.
- With a free account it knows the date of birth of each child, so asking "which vaccines are due
  for Laura?" works out her age by itself.

## The tools on the site, besides the chat

- Dose calculator: paracetamol and ibuprofen by weight, in ml for the strength of your bottle,
  from fixed tables, calculated on the page without AI (pedibot.xyz/dose).
- Growth chart: where a child is on the WHO curves — weight for age, height for age, weight for
  height and BMI — calculated on the page (pedibot.xyz/growth).
- Vaccination schedule by country and age, transcribed from each ministry (pedibot.xyz/vaccines).
- "Should I take my child to the emergency department?": a checklist of the signs the guidelines
  say need to be seen (pedibot.xyz/emergency).
- Symptom diary: temperature and medicines given, kept in your own phone (pedibot.xyz/diary).
- Arm tape (MUAC): for where there is no scale, to find malnutrition (pedibot.xyz/muac).
- What the guidelines say to keep at home (pedibot.xyz/kit).
- Written guides on common problems (pedibot.xyz/guides).
- Every page exists in the eight languages: the same address with the language code after the
  domain, for example pedibot.xyz/es/dose or pedibot.xyz/fr/growth.
- An optional free account (pedibot.xyz/family). It keeps exactly this about each child and
  nothing else: name, date of birth, sex, country, the measurements you note down (weight,
  height, head) and which vaccination visits have already been given. There is no place to save
  allergies, long-term conditions, usual medicines, past illnesses or notes, and the chat does
  not carry anything from one day to the next. You can download it all or delete it whenever you
  want, from your own page, without asking anyone.
- The site can be installed on a phone from the browser menu, and then the emergency numbers and
  anything already read open with no signal.

## What the chat does with a question

- It explains what the published guidelines say about what you describe, shows the document each
  sentence comes from, says which signs to watch for at home and when the child needs to be seen.
- It can go over a problem with you in several messages, and it will ask for the age or the
  weight when the answer depends on them.
- It does not give an opinion of its own, and it does not decide for you. Where the guidelines
  disagree with what someone told you, it says what the guidelines say and whose they are.

## What it cannot do

- It cannot see photographs, videos or audio, and nothing can be uploaded to it: no rash photo,
  no test result, no prescription, no scan, no medical report. Everything has to be written.
- It cannot look things up around you: no nearby hospital, no pharmacy on duty, no list of
  paediatricians, no appointments.
- It cannot send reminders or notifications, and there is no button that dials an emergency
  number by itself: the number is shown, the call is yours to make.
- It does not answer questions about pregnancy, about adults, or about anything that is not the
  health of a baby or a child.
- It does not say what a child has. It explains what the guidelines say and when a child needs to
  be seen.
- It can be wrong. That is why every sentence shows the document it came from, so it can be
  checked, and why the answer always says when to see a doctor.

## Privacy

- Without an account nothing personal is asked and nothing personal should be written.
- Questions and answers are kept anonymously — a random session identifier, no IP address — to
  measure and improve quality. The IP is used only as a salted hash to limit how many questions
  come from one place.
- With an account: the e-mail, a hash of the password (never the password) and what you write
  about your children. It is not sold, not shared and not used for advertising, and you can
  delete all of it yourself.
- The browser keeps the session identifier, the chosen country and night mode. There are no
  advertising trackers.
- An answer shared with the "copy link" button becomes a public page with the question and the
  answer on it, and nothing else.
