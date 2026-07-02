# Autonomous Lead Qualifier

**Point it at a company. Get back a sales-ready verdict — and an honest "not sure" when the evidence isn't there.**

Give it one company name or website URL. It researches the company live, then tells you five things: what they do, whether they fit the ideal customer profile, rough deal potential, a recommended next action, and how confident it is in that read.

---

## The problem it solves

Every inbound lead raises the same question: *is this company worth a rep's time?*

Answering it by hand means searching the company, reading their site, judging whether they fit, and deciding a next step — roughly ten minutes per lead, and it takes judgment. Across a full inbound list that's hours of skilled time spent on triage before a single sales conversation happens.

This tool automates that triage. It makes the same call a good rep would — consistently, in under a minute — and it flags the leads a human still needs to check instead of guessing at them.

## What it gives you

For any company, one structured verdict:

| Output | What it answers |
|---|---|
| **What they do** | A short, factual summary from live research |
| **ICP fit** | Customer, competitor, or unclear — with the reasoning |
| **Deal potential** | Rough size read: HIGH / MEDIUM / LOW |
| **Next action** | The specific move to make on this lead |
| **Confidence** | How far to trust the above — and *why* |

---

## Try it — the web app (recommended)

The easiest way to see it work is the built-in interface. No command line needed once it's set up.

```bash
# 1. install
pip install -r requirements.txt

# 2. set your Anthropic API key (once per terminal window)
#    Windows PowerShell:
$env:ANTHROPIC_API_KEY="sk-ant-..."
#    Mac / Linux:
export ANTHROPIC_API_KEY=sk-ant-...

# 3. launch
streamlit run app.py
```

Your browser opens at `http://localhost:8501`. Type a company, or tap one of the four test buttons, then click **Qualify lead** and read the verdict. The confidence banner is the loudest element on the screen by design — a low-confidence result is meant to *stop* you, not blend in.

> **Getting an Anthropic API key:** create one at [console.anthropic.com](https://console.anthropic.com) → Billing → add a small credit → API Keys. Each qualification costs roughly 5–15 US cents.

## Prefer the command line?

Same engine, no interface:

```bash
python qualify.py "ascoat.com.au"
python qualify.py "Slip Solutions Sydney"
python qualify.py "commercialcleaning.au"
```

Each run prints a report and saves `outputs/<company>.md` and `outputs/<company>.json`.

> **One engine, two front doors.** The web app and the command line both call the same tested `qualify()` function. The interface is a thin layer — all the judgment lives in one place, so there's nothing to keep in sync.

---

## How it works

```
   You enter a company name or URL
                │
                ▼
   Claude researches it live  ──►  up to 5 web searches, on its own:
                │                  resolves a name to a website, checks
                │                  who really runs a domain, gathers what
                │                  they do and rough size signals
                ▼
   It judges the company     ──►  against a fixed ideal-customer profile
                │                  (installers & buyers = fit,
                │                  manufacturers = competitors)
                ▼
   A code check runs         ──►  any verdict with no sources cited is
                │                  forced down to LOW confidence
                ▼
   You get one clear verdict ──►  fit, potential, next action,
                                  confidence + reasoning, sources
```

## How it qualifies — the logic

The tool isn't a keyword matcher. It follows a decision sequence, and every verdict is tied to evidence it actually found.

**Step 1 — Work out who the company really is.** Before judging anything, it confirms the actual entity — resolving a name to a real website, or checking who operates a given domain. This matters more than it sounds: `commercialcleaning.au` is run by *Clean Group*, not a business called "Commercial Cleaning." Qualify the wrong entity and every downstream answer is wrong.

**Step 2 — Sort the business into one of three roles.** Fit hinges on a single distinction most naive tools get backwards:

| Role | Signal | Verdict |
|---|---|---|
| **Installer / applicator** | Applies coatings — including *other brands'* products | **Customer** (buys product, repeatedly) |
| **Commercial buyer** | Owns or manages premises that need non-slip solutions | **Customer** (buys for its own sites) |
| **Manufacturer** | Makes or owns a competing coating brand | **Competitor — not a fit** |

The trap the profile is built to avoid: *an applicator who installs rival brands looks like a competitor but is actually an ideal customer.* Ascoat is exactly this — it applies Sika, Flowcrete, and Fosroc. The play is adding Stellmann to that roster, not writing the company off.

**Step 3 — Reason each output from evidence, not assumption.**
- **Deal potential** comes from size and buying pattern — staff, locations, one-off vs. repeat purchasing — never an invented number.
- **Next action** is matched to the fit: a strong installer gets a direct sales approach; an uncertain lead gets a discovery or verification step, not a pitch.
- **Confidence** is scored on how good the evidence is — and this is where the tool has an opinion.

**Step 4 — Fail honest, not confident.** When the evidence isn't there, the right output is LOW confidence with a plain statement of what couldn't be verified. A confident guess is treated as a *failure*, because in a real pipeline a false "strong fit" wastes a rep's day and a false "no fit" throws away revenue.

## Confidence, enforced twice

The honesty rule isn't left to chance — it's backed at two levels:

1. **Prompt rules** — an unreachable site, thin results, an ambiguous entity, or conflicting evidence all force confidence to LOW, require the output to state what couldn't be verified, and turn the next action into a human check.
2. **A code guard** (`enforce_confidence_guard`) — any verdict that cites *zero sources* is automatically downgraded to LOW, no matter what the model claims. Instructions can be ignored under pressure; code can't. Honesty becomes a structural constraint rather than a suggestion.

---

## Design decisions

- **Live web search instead of a scraper.** The task has to accept a *name* or a *URL*. A scraper handles URLs but fails on names, and can't tell that a domain belongs to a differently-named business. Search-first research handles all of it.
- **The installer-vs-manufacturer rule is written into the profile.** In the anti-slip space, the most valuable customers can look like competitors at a glance. The tool is forced to make that distinction explicitly, with evidence.
- **Two-layer confidence.** Prompt rules plus a code guard — described above. This is the single most important design choice, because it's the difference between a tool a sales team can trust and one that quietly makes things up.
- **One engine, kept small.** The one-hour cap is a scoping constraint, not just a clock. A rough version that runs and reasons well beats an elaborate one that doesn't.

## Test results — the three supplied companies

> _Confirm each row against your own run before submitting; replace if your output differs._

| Input | ICP fit | Deal potential | Confidence |
|---|---|---|---|
| ascoat.com.au | _fill from your run_ | _—_ | _—_ |
| Slip Solutions Sydney | _fill from your run_ | _—_ | _—_ |
| commercialcleaning.au | _fill from your run_ | _—_ | _—_ |

Full outputs for each are committed under [`outputs/`](outputs/).

## What I'd build next — the production path

Same qualification engine, wired into the sales motion: batch mode over a CSV of inbound and scraped leads → results pushed into Zoho CRM as scored leads (fit, potential, and next action as fields) → an n8n schedule for continuous qualification → a daily digest to the sales inbox. The one-hour version proves the judgment layer; production is plumbing.
