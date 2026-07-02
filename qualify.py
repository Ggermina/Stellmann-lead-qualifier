#!/usr/bin/env python3
"""
Autonomous Lead Qualifier — Stellmann practical task (Task 1 + Task 2).

Give it a company name OR a website URL. It researches the company live
via web search, then returns a structured qualification against Stellmann's
ICP — built to say "I don't know" instead of guessing.

Usage:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=sk-ant-...      # PowerShell: $env:ANTHROPIC_API_KEY="sk-ant-..."
    python qualify.py "ascoat.com.au"
    python qualify.py "Slip Solutions Sydney"
    python qualify.py "commercialcleaning.au"
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from anthropic import Anthropic

MODEL = os.environ.get("QUALIFIER_MODEL", "claude-sonnet-4-6")
MAX_SEARCHES = 5

# ---------------------------------------------------------------------------
# Who we sell for, and what counts as a lead
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an autonomous lead-qualification agent for Stellmann, an Australian
manufacturer of non-slip coatings, sold through (a) DIY e-commerce and
(b) consultative B2B sales.

IDEAL CUSTOMER PROFILE — a company FITS if it is one of:
1. TRADIE INSTALLER: flooring contractors, coating applicators, anti-slip
   treatment specialists, safety-surface or line-marking installers — trades
   businesses that would BUY Stellmann product repeatedly and apply it for
   their own clients.
2. COMMERCIAL BUYER: organisations that purchase non-slip solutions for
   premises they own, manage, or service — facility management, property
   groups, aged care, hospitality, industrial and government sites.

NOT A FIT:
- COMPETITOR: another manufacturer or brand owner of anti-slip coatings or
  treatments. IMPORTANT: a company that APPLIES or INSTALLS coatings made
  by others is a customer, NOT a competitor. Only companies that make or
  own competing products are competitors.
- Companies with no plausible purchase path for floor-safety products.

HARD RULES:
- Every claim must come from what you actually find in web search results.
  Never invent details. Never fill gaps with plausible-sounding guesses.
- If the website is unreachable, results are sparse, the entity is ambiguous
  (e.g. two businesses share the name), or the evidence conflicts: set
  confidence to LOW, state plainly WHAT you could not verify, and make the
  recommended next action a human verification step. "I don't know" is a
  correct output. A confident guess is a failure.
- If the input domain and the actual trading name differ, report the real
  trading name you verified and note the difference.
- Deal potential is a rough, evidence-based judgement (company size, repeat
  vs one-off purchase pattern, service overlap) — not a fabricated number.
"""

USER_PROMPT = """\
Research and qualify this company as a sales lead for Stellmann: {target}

Steps:
1. Identify the company. If given a name, resolve it to the right website;
   if given a URL, verify who actually operates it.
2. Establish what it does, where it operates, and rough size signals
   (staff, locations, service range).
3. Decide whether it INSTALLS coatings, MANUFACTURES coatings, or would BUY
   non-slip solutions — and qualify it against the ICP.

First write brief working notes. Then output ONE final json object inside a
```json fence with EXACTLY these keys:

- "company_name": verified trading name
- "website": verified primary website, or null
- "what_they_do": 2-3 factual sentences
- "icp_fit": one of "STRONG_FIT_INSTALLER" | "STRONG_FIT_COMMERCIAL_BUYER" |
  "PARTIAL_FIT" | "NO_FIT_COMPETITOR" | "NO_FIT" | "UNKNOWN"
- "fit_reasoning": 1-3 sentences tied to evidence
- "deal_potential": one of "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN"
- "deal_reasoning": 1-2 sentences
- "recommended_next_action": one specific, concrete sentence
- "confidence": one of "HIGH" | "MEDIUM" | "LOW"
- "confidence_reasoning": what was verified vs. what remains uncertain
- "sources": list of URLs actually used
"""

# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def extract_json(text: str) -> dict:
    """Pull the last ```json fenced block; fall back to outermost braces."""
    fenced = re.findall(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        return json.loads(fenced[-1])
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        return json.loads(text[start : end + 1])
    raise ValueError("No JSON object found in model output.")


def enforce_confidence_guard(result: dict) -> dict:
    """Code-level guard: a verdict citing zero sources cannot exceed LOW.

    The prompt already instructs honesty, but instructions can be ignored;
    this guard makes the honesty rule structural rather than optional.
    """
    sources = result.get("sources") or []
    if not sources and result.get("confidence") != "LOW":
        result["confidence"] = "LOW"
        result["confidence_reasoning"] = (
            "[Code guard] Downgraded to LOW: no sources were cited, so this "
            "qualification cannot be trusted. Original note: "
            + str(result.get("confidence_reasoning", ""))
        )
    return result


def qualify(target: str) -> dict:
    client = Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    response = client.messages.create(
        model=MODEL,
        max_tokens=3000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": USER_PROMPT.format(target=target)}],
        tools=[
            {
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": MAX_SEARCHES,
            }
        ],
    )
    text = "".join(b.text for b in response.content if b.type == "text")
    result = enforce_confidence_guard(extract_json(text))
    result["_meta"] = {
        "input": target,
        "model": MODEL,
        "qualified_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    return result


# ---------------------------------------------------------------------------
# Output rendering
# ---------------------------------------------------------------------------


def render_console(r: dict) -> str:
    line = "=" * 64
    sources = "\n".join(f"    - {s}" for s in (r.get("sources") or [])) or "    - (none cited)"
    return f"""
{line}
  LEAD QUALIFICATION — {r.get('company_name', 'Unknown')}
{line}
  Website           : {r.get('website') or '—'}
  ICP fit           : {r.get('icp_fit', 'UNKNOWN')}
  Deal potential    : {r.get('deal_potential', 'UNKNOWN')}
  Confidence        : {r.get('confidence', 'LOW')}
{line}
  What they do      : {r.get('what_they_do', '')}

  Fit reasoning     : {r.get('fit_reasoning', '')}

  Deal reasoning    : {r.get('deal_reasoning', '')}

  Next action       : {r.get('recommended_next_action', '')}

  Confidence notes  : {r.get('confidence_reasoning', '')}

  Sources:
{sources}
{line}"""


def to_markdown(r: dict) -> str:
    meta = r.get("_meta", {})
    sources = "\n".join(f"- {s}" for s in (r.get("sources") or [])) or "- (none cited)"
    return f"""# Lead Qualification — {r.get('company_name', 'Unknown')}

**Input:** `{meta.get('input', '')}` | **Qualified:** {meta.get('qualified_at', '')}

| Field | Result |
|---|---|
| Website | {r.get('website') or '—'} |
| ICP fit | **{r.get('icp_fit', 'UNKNOWN')}** |
| Deal potential | **{r.get('deal_potential', 'UNKNOWN')}** |
| Confidence | **{r.get('confidence', 'LOW')}** |

## What they do
{r.get('what_they_do', '')}

## Fit reasoning
{r.get('fit_reasoning', '')}

## Deal potential
{r.get('deal_reasoning', '')}

## Recommended next action
{r.get('recommended_next_action', '')}

## Confidence notes
{r.get('confidence_reasoning', '')}

## Sources
{sources}
"""


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python qualify.py "<company name or URL>"')
        sys.exit(1)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: set the ANTHROPIC_API_KEY environment variable first.")
        sys.exit(1)

    target = " ".join(sys.argv[1:]).strip()
    print(f'Qualifying "{target}" — researching live, ~30-60 seconds...')

    try:
        result = qualify(target)
    except Exception as exc:  # surface API/parse errors plainly
        print(f"Qualification failed: {exc}")
        sys.exit(1)

    print(render_console(result))

    slug = re.sub(r"[^a-z0-9]+", "-", target.lower()).strip("-")[:60] or "result"
    outdir = Path("outputs")
    outdir.mkdir(exist_ok=True)
    (outdir / f"{slug}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (outdir / f"{slug}.md").write_text(to_markdown(result), encoding="utf-8")
    print(f"Saved: outputs/{slug}.json and outputs/{slug}.md")


if __name__ == "__main__":
    main()
