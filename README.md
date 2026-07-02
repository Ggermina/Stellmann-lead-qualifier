# Autonomous Lead Qualifier — Stellmann Practical Task

One command. Give it a **company name or a website URL**; it researches the
company live and returns a structured qualification against Stellmann's ICP —
and it is built to say **"I don't know"** instead of guessing.

```
$ python qualify.py "Slip Solutions Sydney"
```

Returns: what the company does, ICP fit, rough deal potential, a recommended
next action, and a confidence level with explicit reasoning — printed to the
console and saved as `.md` + `.json` in `outputs/`.

## How it works

```
input (name or URL)
      │
      ▼
agentic research ──► Claude + server-side web search (max 5 searches)
      │               resolves name → website, verifies who runs a domain,
      │               gathers what they do + size signals
      ▼
qualification ─────► hard-coded ICP: tradie installers & commercial buyers,
      │               with an explicit installer-vs-manufacturer rule
      │               (applicators = customers; manufacturers = competitors)
      ▼
structured verdict ► one JSON object: fit, deal potential, next action,
                     confidence + reasoning, cited sources
```

**Confidence is governed twice:**

1. **Prompt-level rules** — unreachable site, sparse results, ambiguous
   entity, or conflicting evidence ⇒ confidence must be LOW, the output must
   state what could not be verified, and the next action becomes a human
   verification step.
2. **Code-level guard** (`enforce_confidence_guard`) — any verdict citing
   zero sources is force-downgraded to LOW, regardless of what the model
   claims. Honesty as a structural constraint, not a suggestion.

## Run it

```bash
pip install -r requirements.txt

export ANTHROPIC_API_KEY=sk-ant-...
# Windows PowerShell:  $env:ANTHROPIC_API_KEY="sk-ant-..."

python qualify.py "ascoat.com.au"
python qualify.py "Slip Solutions Sydney"
python qualify.py "commercialcleaning.au"
```

Each run prints a report and writes `outputs/<company>.md` and
`outputs/<company>.json`.

## Optional web UI

A Streamlit interface (`app.py`) is included so a non-technical user could run
qualifications without the command line. It calls the **same tested
`qualify()` function** — the UI is a thin layer over the engine, not a
reimplementation.

```bash
pip install -r requirements.txt
streamlit run app.py     # opens http://localhost:8501
```

## Design decisions

- **LLM + live web search instead of a scraper.** The spec requires accepting
  a *name* or a *URL*. A scraper handles URLs but fails on names; search-first
  research handles both, and also catches the case where a domain is operated
  by a differently-named business.
- **Installer vs manufacturer is hard-coded into the ICP.** Companies in the
  anti-slip space can look like competitors while actually being ideal
  customers (applicators who buy product). The prompt forces that distinction
  to be made explicitly, with evidence.
- **Two-layer confidence enforcement.** Prompt instructions can be ignored
  under pressure; the code guard cannot. Low-evidence verdicts are structurally
  prevented from presenting as high-confidence.
- **One file, one dependency.** The 1-hour cap is a scoping constraint, not
  just a time limit. A rough working version that runs beats an elaborate
  plan that doesn't.

## Test results — the three supplied companies

| Input | Verdict | Deal potential | Confidence |
|---|---|---|---|
| ascoat.com.au | _run to fill_ | _—_ | _—_ |
| Slip Solutions Sydney | _run to fill_ | _—_ | _—_ |
| commercialcleaning.au | _run to fill_ | _—_ | _—_ |

Full outputs for each are committed under [`outputs/`](outputs/).

## What I'd build next (the production path)

Same qualification engine, wired into the sales motion: batch mode over a CSV
of inbound and scraped leads → results pushed into Zoho CRM as scored leads
(fit, potential, and next action as fields) → an n8n schedule for continuous
qualification → a daily digest to the sales inbox. The one-hour version proves
the judgement layer; production is plumbing.
