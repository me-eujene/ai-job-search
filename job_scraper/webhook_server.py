"""
Webhook server for n8n ↔ Telegram integration.

Accepts a job posting (URL or raw text) from n8n, stores it in state.db,
runs a quick Claude fit assessment, and returns a pre-formatted Telegram message.

Usage (from repo root):
    uv run python -m job_scraper.webhook_server

Endpoints:
    GET  /health        — liveness check
    POST /ingest        — ingest a job and return a fit assessment

Environment variables (all optional unless noted):
    ANTHROPIC_API_KEY   — required for fit assessment
    CLAUDE_MODEL        — model to use (default: claude-sonnet-4-6)
    WEBHOOK_PORT        — port to listen on (default: 8765)
    WEBHOOK_HOST        — bind address (default: 0.0.0.0)
    WEBHOOK_SECRET      — if set, requests must include X-Webhook-Secret header
"""

import json
import os
import re
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from flask import Flask, jsonify, request

load_dotenv(Path(__file__).parent / ".env")

from .src.helpers import iso_date, iso_ts, utc_now
from .src.state import init_db, mark_seen_if_new
from .src.types import make_canonical_key

app = Flask(__name__)

_REPO_ROOT = Path(__file__).parent.parent
_SKILLS_DIR = _REPO_ROOT / ".claude" / "skills" / "job-application-assistant"
_PROFILE_PATH = _SKILLS_DIR / "01-candidate-profile.md"
_EVAL_PATH = _SKILLS_DIR / "04-job-evaluation.md"

_URL_RE = re.compile(r"https?://[^\s\"'>]+")
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s{2,}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_text(path: Path, fallback: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return fallback


def _check_secret() -> bool:
    """Return True if the request carries the correct webhook secret (or none is set)."""
    secret = os.getenv("WEBHOOK_SECRET", "")
    if not secret:
        return True
    return request.headers.get("X-Webhook-Secret", "") == secret


def _extract_url(text: str) -> str:
    """Return the first HTTP(S) URL found in text, or empty string."""
    m = _URL_RE.search(text)
    return m.group(0).rstrip(".,;)") if m else ""


def _fetch_page_text(url: str, max_chars: int = 8000) -> str:
    """Fetch a URL and return stripped plain text (best-effort)."""
    try:
        with httpx.Client(
            timeout=20,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
                )
            },
        ) as client:
            resp = client.get(url)
            resp.raise_for_status()
            text = _HTML_TAG_RE.sub(" ", resp.text)
            text = _WS_RE.sub(" ", text).strip()
            return text[:max_chars]
    except Exception as exc:
        return f"(Could not fetch URL: {exc})"


def _assess(job_text: str) -> dict:
    """
    Call Claude to extract job fields and produce a structured fit assessment.
    Returns a dict with keys: title, company, location, score, verdict,
    recommendation, technical_score, experience_score, behavioral_score,
    career_score, location_pass, strengths, gaps, summary.
    Falls back to an error dict if the API call fails.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return {
            "error": "ANTHROPIC_API_KEY not set in job_scraper/.env",
            "title": "Unknown Role",
            "company": "Unknown Company",
            "location": "Unknown",
            "score": 0,
            "verdict": "Unknown",
            "recommendation": "Skip",
            "technical_score": 0,
            "experience_score": 0,
            "behavioral_score": 0,
            "career_score": 0,
            "location_pass": True,
            "strengths": [],
            "gaps": [],
            "summary": "Cannot assess — ANTHROPIC_API_KEY missing.",
        }

    try:
        import anthropic  # imported lazily so the server starts even without it
    except ImportError:
        return {
            "error": "anthropic package not installed. Run: pip install anthropic",
            "title": "Unknown Role",
            "company": "Unknown Company",
            "location": "Unknown",
            "score": 0,
            "verdict": "Unknown",
            "recommendation": "Skip",
            "technical_score": 0,
            "experience_score": 0,
            "behavioral_score": 0,
            "career_score": 0,
            "location_pass": True,
            "strengths": [],
            "gaps": [],
            "summary": "Cannot assess — anthropic package missing.",
        }

    profile = _load_text(_PROFILE_PATH, "(Candidate profile empty — run /job-scraper-setup)")
    eval_fw = _load_text(_EVAL_PATH)

    system = (
        "You are a career advisor assessing job fit. "
        "Respond ONLY with valid JSON — no markdown fences, no extra text."
    )

    user_prompt = f"""## Candidate Profile
{profile}

## Evaluation Framework
{eval_fw}

## Job Posting
{job_text}

## Instructions
Extract the job details and assess fit using the evaluation framework above.
Return a single JSON object with exactly these keys:
- "title": job title (string)
- "company": company name (string)
- "location": city / region (string)
- "score": overall fit score 0-100 (integer, weighted per framework)
- "verdict": one of "Strong Fit"|"Good Fit"|"Moderate Fit"|"Weak Fit"|"Poor Fit"
- "recommendation": one of "Apply"|"Consider"|"Skip"
- "technical_score": integer 0-100
- "experience_score": integer 0-100
- "behavioral_score": integer 0-100
- "career_score": integer 0-100
- "location_pass": boolean
- "strengths": list of 2-3 concise strings
- "gaps": list of 1-3 concise strings (or empty list)
- "summary": 1-2 sentence recommendation"""

    client = anthropic.Anthropic(api_key=api_key)
    model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

    try:
        msg = client.messages.create(
            model=model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw = msg.content[0].text.strip()
        # Strip accidental markdown fences
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)
    except Exception as exc:
        return {
            "error": str(exc),
            "title": "Unknown Role",
            "company": "Unknown Company",
            "location": "Unknown",
            "score": 0,
            "verdict": "Unknown",
            "recommendation": "Skip",
            "technical_score": 0,
            "experience_score": 0,
            "behavioral_score": 0,
            "career_score": 0,
            "location_pass": True,
            "strengths": [],
            "gaps": [],
            "summary": f"Assessment failed: {exc}",
        }


def _format_telegram(assessment: dict, apply_url: str, is_new: bool) -> str:
    """Build a Markdown-safe Telegram message from an assessment dict."""
    verdict = assessment.get("verdict", "Unknown")
    score = assessment.get("score", 0)
    rec = assessment.get("recommendation", "?")
    title = assessment.get("title", "Unknown Role")
    company = assessment.get("company", "Unknown Company")
    location = assessment.get("location", "Unknown")

    verdict_emoji = {
        "Strong Fit": "\U0001f7e2",   # 🟢
        "Good Fit": "\U0001f7e1",     # 🟡
        "Moderate Fit": "\U0001f7e0", # 🟠
        "Weak Fit": "\U0001f534",     # 🔴
        "Poor Fit": "\u26d4",         # ⛔
    }.get(verdict, "\u26aa")           # ⚪

    rec_emoji = {"Apply": "\u2705", "Consider": "\U0001f914", "Skip": "\u274c"}.get(rec, "\u2753")
    loc_status = "\u2705 PASS" if assessment.get("location_pass", True) else "\u274c FAIL"

    strengths = assessment.get("strengths") or []
    gaps = assessment.get("gaps") or []
    summary = assessment.get("summary", "")

    strengths_lines = "\n".join(f"  \u2713 {s}" for s in strengths) or "  (none identified)"
    gaps_lines = "\n".join(f"  \u2717 {g}" for g in gaps) or "  (none)"

    dup_tag = "" if is_new else "\n_\u26a0\ufe0f Already in pipeline_"

    lines = [
        f"{verdict_emoji} *Fit: {verdict}* \u2014 *{score}/100*",
        "",
        f"\U0001f4cb *{title}* @ {company}",
        f"\U0001f4cd {location} \u2014 Location: {loc_status}",
        "",
        "*Scores:*",
        (
            f"  Tech: {assessment.get('technical_score','?')}/100"
            f"  |  Exp: {assessment.get('experience_score','?')}/100"
        ),
        (
            f"  Culture: {assessment.get('behavioral_score','?')}/100"
            f"  |  Career: {assessment.get('career_score','?')}/100"
        ),
        "",
        "*Strengths:*",
        strengths_lines,
        "",
        "*Gaps:*",
        gaps_lines,
        "",
        f"\U0001f4a1 {summary}",
        "",
        f"{rec_emoji} *Recommendation: {rec}*",
    ]

    if apply_url:
        lines.append(f"\n\U0001f517 [Apply here]({apply_url})")

    if dup_tag:
        lines.append(dup_tag)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/ingest")
def ingest():
    """
    Ingest a job posting from n8n.

    Request JSON body (all optional, but at least one of url/text required):
        url   (str): Direct link to the job posting
        text  (str): Raw message text — may also contain a URL

    Response JSON:
        job:              {title, company, location, apply_url, canonical_key, is_new}
        assessment:       Full Claude assessment dict
        telegram_message: Pre-formatted Markdown string for Telegram sendMessage
    """
    if not _check_secret():
        return jsonify({"error": "Unauthorized"}), 401

    body = request.get_json(force=True, silent=True) or {}
    url: str = (body.get("url") or "").strip()
    text: str = (body.get("text") or "").strip()

    # Extract URL from text if not provided explicitly
    if not url and text:
        url = _extract_url(text)

    job_parts: list[str] = []
    if text:
        job_parts.append(text)
    if url:
        fetched = _fetch_page_text(url)
        job_parts.append(f"\n[Content from {url}]\n{fetched}")

    if not job_parts:
        return jsonify({"error": "Provide 'url' or 'text' in the request body"}), 400

    full_text = "\n".join(job_parts)

    # Claude assessment (also extracts structured fields)
    assessment = _assess(full_text)

    title = assessment.get("title") or "Unknown Role"
    company = assessment.get("company") or "Unknown Company"
    location = assessment.get("location") or "Unknown"
    city = location.split(",")[0].strip()

    canonical_key = make_canonical_key(title, company, city)
    now = utc_now()

    is_new = mark_seen_if_new(
        canonical_key=canonical_key,
        title=title,
        company=company,
        location=location,
        source="manual",
        apply_url=url or "(no URL)",
        date_posted=iso_date(now),
        description=full_text[:4000],
        fetched_at=iso_ts(now),
    )

    telegram_message = _format_telegram(assessment, url, is_new)

    return jsonify({
        "job": {
            "title": title,
            "company": company,
            "location": location,
            "apply_url": url or None,
            "canonical_key": canonical_key,
            "is_new": is_new,
        },
        "assessment": assessment,
        "telegram_message": telegram_message,
    })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    port = int(os.getenv("WEBHOOK_PORT", "8765"))
    host = os.getenv("WEBHOOK_HOST", "0.0.0.0")
    debug = os.getenv("WEBHOOK_DEBUG", "").lower() in ("1", "true", "yes")
    init_db()
    print(f"Webhook server listening on {host}:{port}", file=sys.stderr)
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
