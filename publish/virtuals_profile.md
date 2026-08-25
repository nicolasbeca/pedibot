# PediBot — Virtuals agent profile texts (2026-08-25)

Paste-ready. Everything here is true as of today; no projections dressed up as facts.

## How it works

PediBot is a free paediatric assistant for parents at **pedibot.xyz** and on Telegram (**@Pedichat_bot**). It answers only from published paediatric guidelines and names the source in every sentence — "According to the SEUP…", "The WHO recommends…" — with a link to the original document.

Every question goes through three checks before a word is written:

1. **Safety first.** A rule-based triage (no AI) looks for the warning signs paediatric emergency doctors publish for parents — a baby under 3 months with fever, vomiting after a head bump, breathing difficulty, a swallowed battery, suicidal thoughts. If one matches, the answer opens with "go to the emergency department now" and the emergency number for the parent's country.
2. **Sources only.** The question is matched against 211 documents from paediatric societies and public health bodies (SEUP, AEP, AEPap, NHS, CDC, MedlinePlus, WHO, Spanish Ministry of Health). No forums, no blogs, no model memory. If nothing relevant is found, PediBot says "I don't have reliable information on this" instead of guessing.
3. **Verified writing.** The reply is drafted from those passages, and a verifier rejects any answer that cites a source that wasn't retrieved or states a dose the guideline didn't. Medication doses never come from the AI: they come from a fixed-table calculator (paracetamol/acetaminophen and ibuprofen, by weight, in ml for 20 brands across 12 countries).

It remembers the conversation (age, symptoms) for follow-up questions, works in English and Spanish, and stores nothing personal — no account, no name, no IP in clear.

## Roadmap

**Done (August 2026)**
- Engine rebuilt from scratch with a citation verifier and rule-based triage; evaluated on a 60-question golden set (100 % warning-sign recall, 100 % valid citations, 96 % correct source in the top 3).
- 211 sources ingested: 49 PDFs from Spanish paediatric societies + 163 public pages from NHS, CDC, MedlinePlus and WHO (all with reuse licences).
- Website live at pedibot.xyz (EN/ES): chat, dose calculator with brands, oral-rehydration guide, "should I go to the ER?" checklist, symptom diary with next-dose reminder, 1,300+ SEO pages for dose queries, public list of sources.
- Telegram bot @Pedichat_bot in production.

**Next (Q3–Q4 2026)**
- Closed beta with parents; every anonymised conversation reviewed by a human before opening wider.
- Two new guides per week, auto-generated from the sources and verified, in EN and ES.
- "Reviewed by" programme with practising paediatricians.
- Photo check limited to warning signs (petechiae, cyanosis, lip swelling) — never a diagnosis.
- Register PediBot as a **service provider on Virtuals ACP**: other agents can buy sourced paediatric answers, paid in $PDBT / $VIRTUAL.
- Regular public updates on what was built and what comes next.

**Later (2027)**
- More languages (Portuguese, French) from the same verified sources.
- Country-specific vaccination schedules.
- WhatsApp channel.

## Additional details

- **Product:** pedibot.xyz · Telegram @Pedichat_bot · X @pedibotai · contact pedibot.ai@gmail.com
- **Sources policy:** only documents whose licence allows reuse (Open Government Licence, US public domain, CC BY-NC-SA, Spanish scientific societies' parent leaflets). Copyrighted parent sites (e.g. commercial or membership-only content) are linked, never ingested. Full list with licences and years: pedibot.xyz/sources.
- **Safety policy:** not medical advice, no diagnosis, no prescriptions. Under-3-months + fever is always "see a doctor today". Mental-health messages get a fixed protocol with the local helpline. Answers without a supporting passage are refused rather than improvised.
- **Privacy:** no accounts, no personal data. Conversations are stored anonymously (random session token) to evaluate answer quality; memory expires after 24 hours.
- **Team:** Nicolás Bk, architect and father, building in the open with AI tooling; advisors in web3, medicine and legal.
- **Token:** PediBot ($PDBT) on Base, launched on Virtuals, trading on Uniswap. Contract 0x196A67BA334DbeD501E19BAEc47D217BB2FC15E1.

## Token utility

$PDBT is the way to back PediBot — not a key to use it.

- **Nothing is gated.** The website and the Telegram bot are free for every parent, always. No premium tier, no holder discounts, no token-only features. A children's health tool must not have a paywall, and it won't.
- **Funds the service.** Keeping PediBot running has a cost — the server and the AI behind every answer — and the token is what pays for it. What we build with it is public; the accounting is not.
- **Agent-to-agent commerce (planned).** Through Virtuals ACP, other AI agents will be able to buy verified, sourced paediatric answers from PediBot and pay in $PDBT or $VIRTUAL. That is the token's economic loop: humans get it free; machines pay.
- **Transparency instead of promises.** We do not promise price, we do not pay for listings, trending or engagement, and product news reach holders and non-holders at the same time.
