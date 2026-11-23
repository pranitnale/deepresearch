# Session Handoff — Business Naming Research

> Generated: 2026-11-23 | Branch: claude/business-naming-research-0zqe1r | Agent: claude-code
> Task slug: business_naming

## Goal / Objective
Find and verify a company name for the founder's planned Germany-based B2B parent company (custom AI applications across sectors; ultimate mission: AI adoption in the European energy sector). The name must have an Indian/Sanskrit root, be effortless for German/European speakers (say, spell after one hearing, remember), stay sector-agnostic, and have exact-match .com/.ai (+ ideally .de) domains. Deliver research the founder can reference or extend from any future project.

**The complete research documentation lives in `business names/00-RESEARCH-HANDOFF.md` — read that first.** This note is the session-state wrapper around it.

## Progress Made

### Completed
- [x] Evidence-based naming rulebook with sources — `business names/01-naming-best-practices.md`, `business names/04-linguistic-pitfalls.md`
- [x] 45 dictionary-verified Sanskrit roots — `business names/02-sanskrit-roots.md`
- [x] Collision landscape + 19 avoid-roots — `business names/03-landscape-collisions.md`
- [x] Five candidate waves, each with collision + 7-language + domain screens — `business names/05…12-*.md` (waves driven by founder feedback: more-unique → tej → T/light-energy → tivra → tiv-family)
- [x] Master handoff consolidating method, full candidate ledger, conclusion, playbook — `business names/00-RESEARCH-HANDOFF.md`
- [x] Reusable controlled domain checker — `business names/check_domains.py` (aborts on failed controls; verified it aborts correctly in this DNS-blocked sandbox)

### Decisions & Logic
- **Decision:** Recommend shortlist Tivran + Tivrin (founder's taste lane), with Sumarga (rules-first lane) and Tapanwerk (Indo-German compound lane) as alternatives; final pick hinges on the DE+EN dictation test and legal pre-checks.
  - **Alternatives considered:** Urjawerk (wave-1 winner — energy-literal, bends the sector-agnostic rule); ~70 names screened in total.
  - **Rationale:** Tivran is the founder's stated favorite and best Kodak-shape; Tivrin has the only zero-web-hit record of the project; Sumarga scores highest on the rulebook; Tapanwerk has the only zero-letter-shift DE/EN phonetics.
  - **Reversibility:** fully reversible until domains are bought and GmbH/trademark filings start.
- **Decision:** Use authoritative-DNS NS lookups (dnspython) with mandatory positive+negative controls as the domain-screening method, after the GoDaddy connector hit its shared-IP daily quota.
  - **Rationale:** registrar APIs quota-limited; RDAP/DoH blocked by sandbox network policy; NS delegation is a reliable registered-signal and NXDOMAIN a near-certain availability signal for .com/.ai/.de.
  - **Reversibility:** n/a (method choice); registrar check remains mandatory before purchase.
- **Decision:** Treat suffix classes differently: -ex is legitimate corporate (Xerox/Rolex); -ix comic-book (killed Krantix); -nix German "nothing" (killed Kiranix).

## Files & Resources Used

### Files written (all under `business names/`)
- `00-RESEARCH-HANDOFF.md` — master handoff (brief, method, rulebook, full ledger, conclusion, playbook)
- `01`–`07` — original wave-1/2 research (2026-07-13, first session)
- `08`–`12` — waves 3–3e (2026-07-13, this session's earlier turns)
- `check_domains.py` — reusable checker
- `README.md` — folder index (updated each wave)

### Documentation consulted
- wisdomlib.org + sanskritdictionary.com — every Sanskrit meaning verified there
- Source URLs embedded per-finding in files 01, 03, 04

### External references
- GitHub branch: `claude/business-naming-research-0zqe1r` on `pranitnale/deepresearch`

## Failed Approaches
- **Tried:** GoDaddy MCP connector for domain checks (both 2026-07-13 sessions)
  - **Failed because:** daily search quota exhausted on shared IP (resets midnight UTC)
  - **Retry if:** needed again right after quota reset; otherwise use `check_domains.py` or a registrar site.
- **Tried:** Re-verifying all headline domains on 2026-11-23 via port-53 DNS in this cloud sandbox
  - **Failed because:** positive control failed — google.com returned "available"; the sandbox silently blocks/filters DNS, so every result was false. Without the control this would have fabricated a full false re-confirmation.
  - **Retry if:** running in an environment where `check_domains.py` controls pass. **Never trust a run whose controls failed.**
- **Tried:** DNS-over-HTTPS (dns.google) and RDAP (rdap.verisign.com) as fallbacks on 2026-11-23
  - **Failed because:** both hosts outside the session's network allowlist (proxy 403 / ENOTFOUND).
  - **Retry if:** the user allows those hosts in session network settings, or from a local machine.
- **Tried (naming dead-ends, do not re-propose):** full list with reasons in `00-RESEARCH-HANDOFF.md` §4 "Dropped" — highlights: Krantix/Kiranix (German semantics), Tivron/Tejora/Agrima/Sumati/Pramita (direct sector collisions), Tivos (TiVo), pure dictionary roots (all sniped on .com+.ai).

## Next Actions
1. **Re-verify domain availability** of the shortlist (tivran, tivrin, tivrium, sumarga, tapanwerk, mitrawerk, sutejas, tejawerk, urjawerk) — run `python3 "business names/check_domains.py" tivran tivrin tivrium sumarga tapanwerk mitrawerk sutejas tejawerk urjawerk` from a network where controls pass, or search them on a registrar.
   - Expected: confirmation that the 2026-07-13 availability still holds. If a name is gone, strike it from the ledger and move down the ranking.
2. **Register .com/.ai/.de for the top 2–3 names** before any public mention (the founder decides which; research recommendation: Tivran, Tivrin, + one of Sumarga/Tapanwerk).
3. **Run the dictation test** for the registered names: say each once to a German speaker and an English speaker; both must write the same string. Decides the tiv- (V) and tej- (J) questions. Record results in the ledger.
4. **IHK name pre-check (free) + Handelsregister search** for the winning name + "GmbH".
5. **DPMA + EUIPO search, Nice classes 9/35/42**, including the similarity list: Tejas Networks, TIVAR, Tivian, Tivron, URWERK, SETU GmbH, Suyana GmbH.
6. **Decide brand architecture** (parent + sub-brand convention, e.g. "<Name> Grid/Labs") — deliberately left open.
7. For any **new name idea**, follow the playbook in `00-RESEARCH-HANDOFF.md` §8 (verify root → avoid-list → rulebook → collision search → `check_domains.py` → append to ledger).

## Learned
- Every clean single-word Sanskrit dictionary word checked (dozens, five waves) is already registered on .com AND .ai — only compounds/hybrids/coinages yield exact-match domains.
- German reads native V as /f/ and J as /y/, but pronounces obvious coinages/loanwords with /v/ (Vodafone effect); intervocalic J (Maja pattern) is German-spellable while bare "tej-" before a consonant gets misheard as "Tee-" (Teewerk).
- "-nix" is German slang for "nothing" and "-ix" reads comic-book (Asterix); "-ex" is the safe corporate coined suffix.
- DNS screening without a positive control can silently fabricate availability: a sandbox that blocks port 53 returned "available" for google.com on 2026-11-23. Controls are non-negotiable; `check_domains.py` enforces them.
- Search indexes lag reality: a "collision" found via web search (Tivran e-commerce) can be a dead site whose domain already dropped — verify the domain before treating an index hit as an active collision.
- This cloud sandbox's network policy changes between sessions (July allowed port-53 DNS + web search; November blocked DNS, DoH and RDAP) — never assume last session's verification path still works.

## Context
- **Branch:** `claude/business-naming-research-0zqe1r` (pushed to origin)
- **Last commit before this session's docs:** e4de8ad "Add tiv-family coinages: Tivrin clear with all domains free"
- **Uncommitted changes:** this handoff + `business names/00-RESEARCH-HANDOFF.md` + `check_domains.py` + README update (committed in this session)
- **Failing tests:** n/a (research repo, no test suite)
- **Environment notes:** GoDaddy MCP quota-limited (shared IP, midnight-UTC reset); current sandbox cannot do valid DNS lookups (controls fail) and blocks dns.google + rdap.verisign.com; domain data is as of 2026-07-13.

## Session Log
- 2026-07-13 — claude-code — waves 1–2: principles, roots, collisions, pitfalls, Urjawerk recommendation (files 01–07)
- 2026-07-13 — claude-code — waves 3–3e on founder feedback: Sumarga/Mitrawerk/Kiranwerk, tej family, T-names, tivra coinages, tiv family (files 08–12)
- 2026-11-23 — claude-code — master handoff written (00-RESEARCH-HANDOFF.md), reusable checker added, November re-verification attempted and correctly aborted on failed DNS controls
