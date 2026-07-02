#!/usr/bin/env python3
"""
Streamlit UI for the Autonomous Lead Qualifier.

Wraps the already-tested qualify() function from qualify.py in a local web UI.
No API key ever touches the browser — it stays in the environment, exactly as
in the CLI. Run with:

    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=sk-ant-...      # PowerShell: $env:ANTHROPIC_API_KEY="sk-ant-..."
    streamlit run app.py

Your browser opens automatically at http://localhost:8501
"""

import os

import streamlit as st

from qualify import qualify  # reuses the exact logic the CLI already tested

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Lead Qualifier — Stellmann", page_icon="◆", layout="centered")

# Semantic colors: meaning, not decoration. Fit/confidence map to intent.
GREEN, AMBER, RED, GRAY, INK = "#1f7a4d", "#b76e00", "#a3341f", "#5b6470", "#1a1d21"

FIT_STYLE = {
    "STRONG_FIT_INSTALLER": (GREEN, "Strong fit — installer"),
    "STRONG_FIT_COMMERCIAL_BUYER": (GREEN, "Strong fit — commercial buyer"),
    "PARTIAL_FIT": (AMBER, "Partial fit"),
    "NO_FIT_COMPETITOR": (RED, "No fit — competitor"),
    "NO_FIT": (RED, "No fit"),
    "UNKNOWN": (GRAY, "Unknown"),
}
LEVEL_COLOR = {"HIGH": GREEN, "MEDIUM": AMBER, "LOW": RED, "UNKNOWN": GRAY}

st.markdown(
    f"""
    <style>
      .block-container {{ max-width: 760px; padding-top: 2.2rem; }}
      .lq-badge {{
        display:inline-block; padding:.28rem .7rem; border-radius:999px;
        color:#fff; font-weight:600; font-size:.82rem; letter-spacing:.02em;
      }}
      .lq-field-label {{
        text-transform:uppercase; font-size:.72rem; letter-spacing:.08em;
        color:{GRAY}; font-weight:700; margin:1.1rem 0 .2rem;
      }}
      .lq-conf-banner {{
        border-radius:10px; padding:1rem 1.15rem; margin:.4rem 0 1.2rem;
        border-left:5px solid; font-size:.95rem;
      }}
      .lq-src a {{ color:{GRAY}; font-size:.85rem; }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Lead Qualifier")
st.caption("Enter a company name or website URL. It researches the company live and qualifies it against Stellmann's ICP — and says so when it isn't sure.")

# ---------------------------------------------------------------------------
# Sidebar — key status + what it checks for
# ---------------------------------------------------------------------------

with st.sidebar:
    st.subheader("Status")
    if os.environ.get("ANTHROPIC_API_KEY"):
        st.success("API key detected")
    else:
        st.error("No API key set")
        st.caption("Set ANTHROPIC_API_KEY in the terminal, then restart this app.")
    st.divider()
    st.subheader("Ideal customer")
    st.caption(
        "**Fit:** tradie installers / applicators, and commercial buyers of "
        "non-slip solutions.\n\n**Not a fit:** manufacturers of competing "
        "coatings. An applicator who installs others' products is a *customer*, "
        "not a competitor."
    )

# ---------------------------------------------------------------------------
# Input — free text plus one-tap test companies
# ---------------------------------------------------------------------------

if "target" not in st.session_state:
    st.session_state.target = ""

st.markdown("**Company name or URL**")
target = st.text_input(
    "target", value=st.session_state.target, label_visibility="collapsed",
    placeholder="e.g. ascoat.com.au  or  Slip Solutions Sydney",
)


run = st.button("Qualify lead", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Run + render
# ---------------------------------------------------------------------------


def badge(text: str, color: str) -> str:
    return f'<span class="lq-badge" style="background:{color}">{text}</span>'


def render(r: dict) -> None:
    fit_color, fit_label = FIT_STYLE.get(r.get("icp_fit", "UNKNOWN"), (GRAY, r.get("icp_fit", "Unknown")))
    pot = r.get("deal_potential", "UNKNOWN")
    conf = r.get("confidence", "LOW")

    st.markdown(f"## {r.get('company_name', 'Unknown company')}")
    site = r.get("website")
    if site:
        st.markdown(f"[{site}]({site})")

    st.markdown(
        badge(fit_label, fit_color)
        + "&nbsp;&nbsp;"
        + badge(f"Deal potential: {pot}", LEVEL_COLOR.get(pot, GRAY)),
        unsafe_allow_html=True,
    )

    # Confidence is the signature element — loudest thing on the page, because
    # "say so when unsure" is the whole point of the tool.
    conf_color = LEVEL_COLOR.get(conf, GRAY)
    tint = {GREEN: "#eaf5ef", AMBER: "#fbf3e3", RED: "#f8ebe8", GRAY: "#eef0f2"}[conf_color]
    st.markdown(
        f'<div class="lq-conf-banner" style="border-color:{conf_color};background:{tint}">'
        f'<strong style="color:{conf_color}">Confidence: {conf}</strong><br>'
        f'{r.get("confidence_reasoning","")}</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="lq-field-label">What they do</div>', unsafe_allow_html=True)
    st.write(r.get("what_they_do", ""))
    st.markdown('<div class="lq-field-label">Why they fit (or don\'t)</div>', unsafe_allow_html=True)
    st.write(r.get("fit_reasoning", ""))
    st.markdown('<div class="lq-field-label">Deal potential</div>', unsafe_allow_html=True)
    st.write(r.get("deal_reasoning", ""))
    st.markdown('<div class="lq-field-label">Recommended next action</div>', unsafe_allow_html=True)
    st.info(r.get("recommended_next_action", ""))

    sources = r.get("sources") or []
    if sources:
        st.markdown('<div class="lq-field-label">Sources</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="lq-src">' + "<br>".join(f'<a href="{s}">{s}</a>' for s in sources) + "</div>",
            unsafe_allow_html=True,
        )


if run:
    if not target.strip():
        st.warning("Enter a company name or URL first.")
    elif not os.environ.get("ANTHROPIC_API_KEY"):
        st.error("No API key set. Add ANTHROPIC_API_KEY in your terminal and restart the app.")
    else:
        with st.spinner(f'Researching "{target}" live — 30 to 60 seconds...'):
            try:
                result = qualify(target.strip())
                render(result)
            except Exception as exc:
                st.error(f"Qualification failed: {exc}")