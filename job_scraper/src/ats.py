"""
Public ATS API adapters — fetch full job descriptions for hiring.cafe jobs.

hiring.cafe job ids encode (ats, board_token, ats_job_id):
  grnhse___fundraiseup___4711181005
  recruitee__greenflux__2664342          (recruitee uses DOUBLE underscores)
  successfactors___eu___AFKL___1354459957 (board token can span segments)

All endpoints validated live 2026-07-05; every adapter returned full
descriptions (2.7k-8.2k chars). Unknown ATS types fall back to trafilatura
on apply_url (works for server-rendered career pages only).
"""
import html as _html
import logging
from typing import Optional
from urllib.parse import unquote

import httpx

from .helpers import extract_text_from_html, html_to_md

logger = logging.getLogger(__name__)


def parse_hc_id(job_id: str) -> Optional[tuple[str, str, str]]:
    """Split a hiring.cafe id into (ats_source, board_token, ats_job_id)."""
    for sep in ("___", "__"):
        parts = job_id.split(sep)
        if len(parts) >= 3:
            return parts[0], unquote(sep.join(parts[1:-1])), unquote(parts[-1])
    return None


def _join_smartrecruiters_sections(sections: dict) -> str:
    chunks = []
    for section in sections.values():
        if isinstance(section, dict) and section.get("text"):
            md = html_to_md(section["text"])
            if md:
                chunks.append(md)
    return "\n\n".join(chunks)


# ---------------------------------------------------------------------------
# Per-ATS adapters. Each returns markdown/plain text or None. May raise —
# the dispatcher catches everything.
# ---------------------------------------------------------------------------

async def _greenhouse(client: httpx.AsyncClient, board: str, aid: str) -> Optional[str]:
    r = await client.get(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{aid}")
    r.raise_for_status()
    content = r.json().get("content") or ""     # HTML-escaped HTML
    return html_to_md(_html.unescape(content))


async def _ashby(client: httpx.AsyncClient, board: str, aid: str,
                 cache: dict) -> Optional[str]:
    if board not in cache:
        r = await client.get(f"https://api.ashbyhq.com/posting-api/job-board/{board}")
        r.raise_for_status()
        cache[board] = r.json().get("jobs") or []
    for job in cache[board]:
        if str(job.get("id")) == aid:
            return html_to_md(job.get("descriptionHtml"))
    return None


async def _workday(client: httpx.AsyncClient, board: str, aid: str) -> Optional[str]:
    # board_token format: "{tenant}-{wdN}-{site}", e.g. "brenntag-wd3-brenntag_jobs"
    try:
        tenant, wd, site = board.split("-", 2)
    except ValueError:
        return None
    r = await client.get(
        f"https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/job/{aid}"
    )
    r.raise_for_status()
    return html_to_md((r.json().get("jobPostingInfo") or {}).get("jobDescription"))


async def _smartrecruiters(client: httpx.AsyncClient, board: str, aid: str) -> Optional[str]:
    r = await client.get(
        f"https://api.smartrecruiters.com/v1/companies/{board}/postings/{aid}"
    )
    r.raise_for_status()
    sections = (r.json().get("jobAd") or {}).get("sections") or {}
    return _join_smartrecruiters_sections(sections) or None


async def _lever(client: httpx.AsyncClient, board: str, aid: str,
                 eu: bool = False) -> Optional[str]:
    host = "api.eu.lever.co" if eu else "api.lever.co"
    r = await client.get(f"https://{host}/v0/postings/{board}/{aid}")
    r.raise_for_status()
    data = r.json()
    chunks = [html_to_md(data.get("description")) or ""]
    for lst in data.get("lists") or []:
        chunks.append(f"{lst.get('text', '')}\n{html_to_md(lst.get('content')) or ''}")
    text = "\n\n".join(c for c in chunks if c.strip())
    return text or None


async def _recruitee(client: httpx.AsyncClient, board: str, aid: str,
                     cache: dict) -> Optional[str]:
    key = f"recruitee:{board}"
    if key not in cache:
        r = await client.get(f"https://{board}.recruitee.com/api/offers/")
        r.raise_for_status()
        cache[key] = r.json().get("offers") or []
    for offer in cache[key]:
        if str(offer.get("id")) == aid:
            return html_to_md(offer.get("description"))
    return None


async def fetch_ats_description(client: httpx.AsyncClient, job_id: str,
                                apply_url: str, cache: dict) -> Optional[str]:
    """Try the ATS API for this job; fall back to trafilatura on apply_url."""
    parsed = parse_hc_id(job_id)
    if parsed:
        src, board, aid = parsed
        try:
            if src in ("grnhse", "greenhouse"):
                return await _greenhouse(client, board, aid)
            if src == "ashby":
                return await _ashby(client, board, aid, cache)
            if src == "workday":
                return await _workday(client, board, aid)
            if src == "smartrecruiters":
                return await _smartrecruiters(client, board, aid)
            if src in ("lever", "eu_lever"):
                return await _lever(client, board, aid, eu=(src == "eu_lever"))
            if src == "recruitee":
                return await _recruitee(client, board, aid, cache)
        except Exception as e:
            logger.warning("ats: %s adapter failed for %s: %s", src, job_id, e)

    # Fallback: server-rendered career pages only; JS-heavy ATS pages fail here.
    if apply_url:
        try:
            r = await client.get(apply_url)
            r.raise_for_status()
            return extract_text_from_html(r.text)
        except Exception as e:
            logger.debug("ats: fallback fetch failed for %s: %s", apply_url, e)
    return None
