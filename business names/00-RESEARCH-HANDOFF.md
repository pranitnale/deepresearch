# BUSINESS NAMING RESEARCH — MASTER HANDOFF

**Project:** Company name for a Germany-based B2B parent company (custom AI applications across sectors; long-term mission: AI adoption in the European energy sector).
**Founder:** Indian citizen, renewable-energy engineer, living in Germany.
**Research period:** 2026-07-13 (waves 1–3e, one day, two sessions) · Handoff written 2026-11-23.
**Repository location:** `business names/` folder, files `01`–`12` + this handoff + `check_domains.py`.

This document is self-contained: it holds the brief, the method, every rule, every candidate with its verdict, the conclusion, and a step-by-step playbook to resume the research in any future project or session. Detail lives in files 01–12; this file is the map and the summary.

---

## 1. The brief (constraints every candidate must meet)

1. **Indian/Sanskrit root**, but easy for Europeans — especially German speakers — to pronounce, spell after hearing once, and remember. Pure Sanskrit not required: suffixes (-x, -ai, -on, …) and Indian+German or Indian+English hybrids allowed.
2. **Parent-company logic:** sector-agnostic (AI products across sectors now, energy as the ultimate goal) — nothing that hard-codes one product, technology or vertical into the legal name.
3. **Target customers:** European businesses (B2B trust signal required).
4. **Exact-match `.com` or `.ai` domain** desired; `.de` a bonus.
5. Entity will be a **German GmbH** → must pass German company-name law and clear DPMA/EUIPO trademarks.

---

## 2. Methodology — how the research was actually done

The work ran as a pipeline of five phases. Each produced one or more numbered files.

### Phase A — Evidence-based naming principles (file 01)
Web research into peer-reviewed and practitioner sources on what makes names work (processing fluency, plosives, vowel symbolism, length, spelling tests, trademark distinctiveness, parent-company naming). Every principle in file 01 carries its source URL. These principles became the **rulebook** (section 3 below) that every later candidate was scored against.

### Phase B — Root inventory (file 02)
45 Sanskrit roots were collected across the themes energy / light / sun / wind / motion / intellect / knowledge / vision / machine / connection / direction / newness / growth. **Every meaning was verified against an online Sanskrit dictionary** (wisdomlib.org, sanskritdictionary.com) — no root was used on folk memory. Each root got a German-pronunciation note and a 1–5 "ease" score (5 = a German can say and spell it after one hearing).

### Phase C — Landscape & collision mapping (file 03)
Web search for existing companies using Sanskrit names (Samsara, Asana, Indra, Druva, Vyoma, VEDA GmbH, …) plus AI-sector and energy-sector naming-trend research. Output: a list of **19 roots to avoid outright** because established companies own them (see file 03 §"Crowded roots"), and the strategic insight that Sanskrit names are proven and accepted in European B2B (Airbus Vahana, Munich's Vyoma) but the thematically obvious roots are claimed.

### Phase D — Linguistic pitfall rules for DACH/EU (file 04)
Research into German pronunciation rules and cross-language brand failures. Produced 12 hard screening rules (V/W→/f/, J→/y/, initial CH/SP/ST shifts, "ai"→"eye", no th, no umlauts, CV-syllable preference, the 7-language rude-word screen DE/EN/FR/ES/IT/NL/PL, GmbH-name law, EUIPO distinctiveness). These are merged into the rulebook below.

### Phase E — Candidate waves with a fixed 3-pass screen (files 05–12)
Candidates were generated in **waves**, each wave triggered by founder feedback, and every candidate went through the same three passes:

1. **Collision pass** — web search for the exact string + "company/brand/startup"; verdicts CLEAR / MINOR RISK / AVOID. (Not a formal register search — see §7.)
2. **Language pass** — the file-04 rules + 7-language screen, applied as reasoned assessment.
3. **Domain pass** — `.com` / `.ai` / `.de` availability. Primary tool was the GoDaddy connector; it hit its shared-IP daily quota both sessions, so the working method was **authoritative-DNS NS-lookup via dnspython** with mandatory control queries (see §6 for the method and its November failure mode). `AVAILABLE` = not delegated in the TLD zone — near-certain for .com/.ai, effectively certain for .de (DENIC requires working NS). **Always re-verify at a registrar before purchase.**

**The waves and what drove them:**

| Wave | File | Trigger | Outcome headline |
|---|---|---|---|
| 1–2 | 05, 06, 07 | original brief | **Urjawerk** recommended; every pure Sanskrit dictionary word already taken on .com+.ai |
| 3 | 08 | "not happy, want more unique" | 23 fresh uncrowded roots → **Sumarga, Mitrawerk, Kiranwerk** full-stack clear |
| 3b | 09 | "something where tej is possible?" | **Sutejas, Tejawerk** full-stack clear; J-split trade-off documented |
| 3c | 10 | "light/energy names starting with T?" | **Tapanwerk, Tejomani** full-stack clear |
| 3d | 11 | "names created from tivra, follow all rules" | **Tivrium** clear; Tivran, Tivrawerk full-stack |
| 3e | 12 | "I like Tivran — more tiv- ideas like Tivrex" | **Tivrin** (zero web hits) full-stack; Tivrex viable .ai-first |

---

## 3. The rulebook (apply to any future candidate)

Distilled from files 01 + 04. A candidate passes only if **all** of these hold:

1. **Fluency first** — effortless to say and read (the strongest evidence-based lever; Alter & Oppenheimer stock-fluency study).
2. **Plosive start preferred** (b/d/g/k/p/t) — measurable recall advantage.
3. **1–3 syllables, ~4–8 characters** (4 syllables only for exceptional meaning).
4. **One unambiguous spelling after one hearing** — test by dictation to one German and one English speaker; both must write the same string. Hyphens, CamelCase, double-reading graphemes (c/k, i/y) fail.
5. **Letter-shift audit (DACH):** German reads native V as /f/, W as /v/, J as /y/, Z as /ts/, initial SP/ST as shp/sht, "ai/ei" as "eye", and cannot say th. Use a shifting letter only if both readings are acceptable. Intervocalic J (Maja, Kajak) is German-spellable; bare J before consonant is not. Obvious coinages often get loanword /v/ (the Vodafone effect) — dictation test decides.
6. **7-language rude/comic screen:** DE, EN, FR, ES, IT, NL, PL (precedents: Mist, Pajero, e-tron, Osram, Lumia…).
7. **Coined/fanciful over descriptive** — strongest EUIPO tier; a Sanskrit root reads as coined in Europe. No descriptive terms (AI, Energy, Consult) as the protectable core.
8. **Suffix discipline:** -ai/-ly/-io/-ify date quickly; keep any suffix detachable. **-ex is the legitimate corporate suffix** (Xerox/Rolex); **-ix reads comic-book** (the Krantix/Asterix failure); **-nix is German slang for "nothing"** (the Kiranix failure).
9. **Sector-agnostic for the parent** (Alphabet logic) — signal AI via the .ai domain and sub-brands, not the legal name.
10. **Sound–meaning congruence** — a root whose acoustics match its meaning is remembered better (tīvra's sharp front "i" matching "intense" is the model case).
11. **ASCII only** — no umlauts/accents.
12. **Clearance before commitment** — collision search is only a first filter; formal checks in §7 are mandatory.

---

## 4. Complete candidate ledger (all waves)

Domain status: **as verified 2026-07-13** (authoritative-DNS; controls passed). A 2026-11-23 re-check was attempted and **aborted — environment could not perform valid DNS lookups** (see §6). Treat all availability as stale until registrar-verified.

### Tier 1 — collision-clear AND .com+.ai+.de all available (2026-07-13)

| Name | Construction / meaning | Say it (DE/EN) | File | Notes |
|---|---|---|---|---|
| **Tivrin** | tivr- coinage (tīvra = intense, sharp) | TIV-rin / TIF-rin | 12 | **Zero web hits — cleanest record of entire project.** Faint "-rin" pharma echo. |
| **Tivran** | tivr- coinage | TIV-ran | 11, 12 | **Founder's stated favorite.** Best Kodak-shape (2 syl/6 ch). Defunct e-commerce residue; Tivian (Cologne software) one letter away. |
| **Tivrium** | tivr- + -ium ("element of intensity") | TIV-ri-um | 11 | Zero collisions. Most gravitas; mild pharma/materials flavor. |
| **Sumarga** | sumārga = "the good path" (real Sanskrit) | su-MAR-ga | 08 | **Most sector-agnostic meaning of the project; zero letter-shifts.** Faint Spanish *amarga* (bitter) echo. |
| **Tapanwerk** | tapana ("the sun, the warming one") + Werk | ta-PAN-verk | 10 | **Best pure phonetics of the project — zero DE/EN letter-shifts.** Sun-flavored. |
| **Mitrawerk** | mitra (ally/partner + sun) + Werk | MI-tra-verk | 08 | Best B2B meaning. German *Mitra* = bishop's mitre (neutral); Mitra AI exists abroad as root-user. |
| **Kiranwerk** | kiraṇa (ray of light) + Werk | KI-ran-verk | 08 | Fixes the Kiranix "-nix" failure; light-flavored. |
| **Sutejas** | su-tejas = "very radiant" (real Sanskrit) | su-TE-yas / soo-TAY-jas | 09 | Most authentic tej option; J-split applies. |
| **Tejawerk** | tejas (radiance) + Werk | te-YA-verk / te-JAH-werk | 09 | J-split; linking -a makes German spelling recoverable. |
| **Tejomani** | tejas + maṇi = "jewel of light" | te-yo-MA-ni | 10 | Most evocative meaning; 4 syllables; Teji Mandi (Indian fintech) faint echo. |
| **Urjawerk** | ūrjā (energy) + Werk | OOR-ya-verk | 07 | Original wave-1 winner. Energy-literal (bends rule 9); urja root crowded among Indian energy brands. |
| **Ojaswerk** | ojas (vigour) + Werk | O-yas-verk / O-jass-werk | 08 | Open root; J-split splits audiences. |
| **Tivrawerk** | tīvra + Werk | TIV-ra-verk | 11 | Clear but clunkiest -werk phonetics. |
| **Tejomana** | coinage: tejas + manas "light-mind" (NOT dictionary Sanskrit) | te-yo-MA-na | 10 | All domains free; **needs its own collision search before use.** |
| Tejwerk | tejas + Werk, no linking vowel | TEY-verk | 09 | Available but deprioritized: German mishearing as *Teewerk* + TEQWERK GmbH proximity. |
| Setuwerk | setu (bridge) + Werk | SAY-too-verk | 05/07 | Available but SETU GmbH exists in German software — legal advice required for the root. |

### Tier 2 — `.ai`(+ mostly `.de`) available, minor risks

| Name | Meaning | File | Risk noted |
|---|---|---|---|
| Medhira | medhā (intelligence) coinage | 07 | small non-EU Medhira firms; medhira.com = US consultancy |
| Ritama | ṛtam (cosmic order) coinage | 07 | Ritrama S.p.A. one letter away |
| Suryana | sūrya (sun) coinage | 07 | Suyana GmbH (Cologne) near-homophone |
| Urjon | ūrjā + -on | 07 | Urjon Control (water treatment); DE/EN J-split |
| Ojasva | ojas coinage | 07 | hardest to spell after one hearing |
| Sunaya | su+naya "good guidance" (contains SUN) | 08 | Suyana GmbH is an anagram; sunaya.com registered-broken |
| Sunetra / Tarini | vision / "she who carries across" | 08 | feminine-first-name feel |
| Tejomaya | "made of radiance" | 09/10 | Indian resort brand; 4 syllables |
| Tapana | the sun | 10 | dormant TAPANA LTD (UK); Finnish word echo |
| Taijasa | "made of light" (Upanishadic) | 10 | internal "ai"→"eye" in German; fragile spelling |
| Tivrex | tivr- + corporate -ex (founder's idea) | 12 | no company collision (only a Steam profile); tivrex.com parked; T-rex echo |
| Tivren | tivr- coinage | 12 | clean; .com taken |

### Dropped — with reasons (do not re-propose without new facts)

| Name | Reason | File |
|---|---|---|
| Krantix | identical active agency; "Krant-" ≈ German *krank* (sick); -ix comic | 05 |
| Kiranix | "-nix" = German slang "nothing" ("Kira gets nothing") | 05 |
| Sumati | SumatoSoft (AI custom-software, Boston) one sound away | 08 |
| Agrima | Agrima Infotech (AI startup, acquired by BigBasket) | 08 |
| Utsaha | Utsaha Technologies (IT+AI consultancy) + several firms | 08 |
| Pramita | Pramati Technologies (enterprise software, since 1998) one vowel away | 08 |
| Sudaksha | Sudaksha Education + Sudaksha Management Solutions | 08 |
| Tejora | Tejora Technologies (Mumbai custom software — exact sector) | 09 |
| Tejasva/Tejasvi | multiple Indian firms + prominent MP | 09 |
| Tejon | Spanish *tejón* = badger; Tejon Ranch | 09 |
| Taraka | Latvian plumbing + Indonesian logistics + Taaraka "AI astrology" | 10 |
| Tivron | Polish contact-center (owns tivron.com) + Tivron Solutions (IN, programming) + tivron.net | 11 |
| Tivrix / Tivrus / Tivrea | rules-outs: -ix comic / "virus" echo / ambiguous pronunciation (all domains were free!) | 11 |
| Tivram | Tivram Private Limited (Udaipur conglomerate) | 12 |
| Tivos | one letter from TiVo | 12 |
| Tivrana | reads as Tirana | 12 |
| Tivrion | spoken confusion with crowded Tivron | 12 |
| Tivano | Lake Como wind (lovely) but .com/.de taken | 12 |
| Tivex | Tyvek near-homophone | 12 |
| Roots avoided outright (file 03) | samsara, asana, indra, veda, yantra, tarka, arka, urja*, vidyut, vayu, setu, meru, tejas*, sarvam, vyoma, druva, manas, gati, medha (*as exact word; compounds were cleared case-by-case) | 03 |

### Taken on both .com and .ai (root confirmed sniped; aftermarket only)
ritam, ojas, yukti, dhara (dhara.ai buyable), kranti, netra, udaya, disha (both buyable), suryon, mitra (mitra.ai buyable), medha, pramiti, daksha, mihira, hetu, damini, urmi, sahai, nirmana, tantu, upaya, aruni, tapan, tarani, taras, tivra, tigma, tarang(a), tarika, tandava, teja, tejas, tej.

**Structural finding:** every clean single-word Sanskrit dictionary word checked was already registered on .com AND .ai. Exact-match domains require compounds, hybrids or coinages. This held across all five waves.

---

## 5. CONCLUSION

**The research converged on three lanes; the choice between them is a positioning decision, not a research question:**

- **Lane A — rules-perfect & sector-agnostic: `Sumarga`** ("the good path"). Scores highest against the full rulebook: real Sanskrit, zero company usage found, zero letter-shift issues, meaning works for AI, energy, and anything later. The purest "Alphabet-logic" parent name of the project.
- **Lane B — Indo-German compound (the founder's story in the name): `Tapanwerk`** (best phonetics — no DE/EN shift at all) or **`Mitrawerk`** (best B2B meaning: ally + hidden sun), with **`Urjawerk`** as the original energy-literal version. All echo *Kraftwerk* and read instantly credible to German Mittelstand.
- **Lane C — the founder's taste (sharp coined T-name): `Tivran`** (stated favorite, best Kodak-geometry) and **`Tivrin`** (same shape, the only name in the whole project with literally zero web hits), with **`Tivrium`** (gravitas) and **`Sutejas`** (authentic Sanskrit "very radiant") behind them.

**Bottom-line recommendation (as of research close):** shortlist **Tivran + Tivrin** (taste-aligned, strongest shapes) with **Sumarga** as the rules-first alternative and **Tapanwerk** as the best compound. Register the .com/.ai/.de for the top two or three immediately (coined names get sniped; total cost is trivial next to GmbH formation), then let two cheap empirical steps decide:
1. **The dictation test** — say each name once to a German speaker and an English speaker; both must write the same string. This is the decisive test for the tiv- family (the V question) and the tej- family (the J question). Sumarga and Tapanwerk should pass trivially; whether Tivran/Tivrin do is exactly what the test reveals.
2. **The legal pre-checks** (§7). Any name failing either step falls back to the next on the list.

**What was NOT concluded:** no formal trademark or register clearance was performed; domain availability is a point-in-time DNS observation from 2026-07-13, not a reservation. Nothing is secured until domains are registered and DPMA/EUIPO come back clean.

---

## 6. Domain-check method — exactly how to reproduce it

**Preferred order of tools:**
1. A **registrar search** (GoDaddy/Namecheap/INWX) — authoritative, do this before any purchase. The session's GoDaddy MCP connector works but shares a daily quota across a shared IP (exhausted on both 2026-07-13 sessions — plan around midnight-UTC reset).
2. **RDAP over HTTPS** (`https://rdap.verisign.com/com/v1/domain/<name>.com`; HTTP 404 = unregistered) — blocked in both the July and November sandbox network policies.
3. **Authoritative-DNS NS lookup** (dnspython) — the method that produced all data in files 06/08–12. Interpretation: NS delegation exists → REGISTERED (definitive); NXDOMAIN → AVAILABLE (near-certain for .com/.ai; effectively certain for .de since DENIC requires working NS at registration). Script: `business names/check_domains.py`.

**MANDATORY CONTROLS (non-negotiable):** every run must first check a known-registered domain (expect REGISTERED) and a gibberish domain (expect AVAILABLE). **If the positive control fails, every result is invalid — discard the whole run.**

**Why this matters — documented failure (2026-11-23):** in the November session, port-53 DNS silently failed and returned "available" for *everything, including google.com*. Without the control, all 16 full-stack candidates would have been falsely "re-confirmed". DoH (dns.google) and RDAP hosts were also outside the network allowlist, so no live re-verification was possible that day. The 2026-07-13 data (controls passed) remains the last valid observation.

---

## 7. Legal/formal next steps (unchanged since wave 1, still ALL open)

For whichever name is chosen, in order:
1. **Register the domains first** — before any public mention, pitch deck, or register filing.
2. **IHK name pre-check** (free) + **Handelsregister** search — GmbH name needs Unterscheidungskraft, must not mislead, must differ clearly from same-municipality entries.
3. **DPMA + EUIPO trademark search**, Nice classes **9 / 35 / 42** (software, consulting, SaaS). Add known near-names to the similarity check: Tejas Networks (tej family); TIVAR, Tivian, Tivron (tiv family); URWERK (werk family); SETU GmbH (setu); Suyana GmbH (sun-/surya family).
4. **Dictation test** DE + EN (described in §5).
5. Decide **brand architecture**: parent name + sub-brand convention for individual AI products (e.g. `<Name> Grid`, `<Name> Labs`) — deliberately left open.

---

## 8. Playbook: evaluating a NEW name idea in a future session

1. **Meaning:** verify the root on wisdomlib.org / sanskritdictionary.com. Never trust folk memory. Note the IAST form.
2. **Avoid-list:** check it is not in file 03's crowded-roots list or §4's dropped table.
3. **Rulebook:** score against §3 (syllables, plosive, letter-shift audit, 7-language screen, suffix discipline, sector-agnosticism).
4. **Collision pass:** web-search `"<name>" company OR startup OR brand` (and `"<name>" GmbH` for DACH). Classify CLEAR / MINOR / AVOID. Remember search indexes lag — a hit may be defunct (verify its domain) and absence is not legal clearance.
5. **Domain pass:** run `python3 "business names/check_domains.py" <name> [more names]` — controls run automatically; then registrar-confirm anything you intend to buy.
6. **Record it:** append to the ledger (§4) with verdict + date, so the next session never re-screens blind.
7. If it survives: §7 steps.

---

## 9. File index

| File | Content |
|---|---|
| `00-RESEARCH-HANDOFF.md` | This master handoff |
| `01-naming-best-practices.md` | 11 evidence-based principles, with sources |
| `02-sanskrit-roots.md` | 45 dictionary-verified roots, meanings, DE-pronunciation, ease scores |
| `03-landscape-collisions.md` | Sanskrit-named companies, AI/energy naming trends, 19 avoid-roots |
| `04-linguistic-pitfalls.md` | 12 German/EU linguistic + legal screening rules, with sources |
| `05-finalist-verification.md` | Wave-1 collision + 7-language verdicts (9 names) |
| `06-domain-availability.md` | Wave-1/2 domain sweep + method note |
| `07-final-recommendations.md` | Wave-1 shortlist: Urjawerk + alternatives |
| `08-new-candidates.md` | Wave 3: 23 fresh roots → Sumarga, Mitrawerk, Kiranwerk |
| `09-tej-family.md` | Wave 3b: Sutejas, Tejawerk; J-split analysis |
| `10-t-light-energy.md` | Wave 3c: Tapanwerk, Tejomani; T-root inventory |
| `11-tivra-coinages.md` | Wave 3d: Tivrium, Tivran; V-letter analysis |
| `12-tiv-family.md` | Wave 3e: Tivrin, Tivrex; consolidated tiv ranking |
| `check_domains.py` | Reusable controlled domain-availability checker |
| `../handoff/handoff_business_naming.md` | Session-handoff note (goal/progress/failures/next actions) |
