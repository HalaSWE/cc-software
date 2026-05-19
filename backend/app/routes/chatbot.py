"""
Chatbot route — AI assistant powered by Groq (free tier).
Fetches live project context and sends it to the LLM.
"""
import os
import json
import logging
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.project import Project
from app.models.evm import EVMMetrics
from app.utils.auth import get_current_user, visible_project_ids
from app.models.user import User

logger = logging.getLogger("cc_software")

router = APIRouter(prefix="/api/chatbot", tags=["🤖 Chatbot"])

GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "openai/gpt-oss-120b"


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []


@router.post("/ask")
async def ask(
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            503,
            "GROQ_API_KEY is not configured. Add it to your .env file. "
            "Get a free key at https://console.groq.com"
        )

    context = _build_context(db, current_user)
    system  = _system_prompt(context, current_user.username)

    messages = [{"role": "system", "content": system}]
    for h in (req.history or [])[-8:]:         # keep last 4 exchanges
        messages.append({"role": h.role, "content": h.content})
    messages.append({"role": "user", "content": req.message})

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {api_key}",
                         "Content-Type": "application/json"},
                json={"model": GROQ_MODEL, "messages": messages,
                      "max_tokens": 600, "temperature": 0.3},
            )
    except httpx.TimeoutException:
        raise HTTPException(504, "AI service timed out. Please try again.")
    except httpx.RequestError as e:
        raise HTTPException(502, f"Network error reaching AI service: {e}")

    if r.status_code == 401:
        raise HTTPException(401, "Invalid GROQ_API_KEY. Check your .env file.")
    if r.status_code == 429:
        raise HTTPException(429, "Rate limit reached. Please wait a moment and try again.")
    if r.status_code != 200:
        raise HTTPException(502, f"AI service returned {r.status_code}")

    reply = r.json()["choices"][0]["message"]["content"]
    return {"reply": reply}


# ── helpers ──────────────────────────────────────────────────────────────────

def _build_context(db: Session, user: User) -> dict:
    ids = visible_project_ids(user, db)

    query = db.query(Project)
    if ids is not None:
        query = query.filter(Project.project_id.in_(ids))
    projects = query.all()

    rows = []
    for p in projects:
        evm = (db.query(EVMMetrics)
                 .filter(EVMMetrics.project_id == p.project_id)
                 .first())
        rows.append({
            "name":    p.name,
            "status":  p.status,
            "budget":  float(p.budget or 0),
            "cpi":     float(evm.cpi) if evm and evm.cpi else None,
            "spi":     float(evm.spi) if evm and evm.spi else None,
            "over_budget":      bool(evm.is_over_budget)      if evm else False,
            "behind_schedule":  bool(evm.is_behind_schedule)  if evm else False,
        })

    status_counts: dict = {}
    for r in rows:
        status_counts[r["status"]] = status_counts.get(r["status"], 0) + 1

    over_budget_count = sum(1 for r in rows if r["over_budget"])
    at_risk_count     = sum(1 for r in rows if r["cpi"] and r["cpi"] < 1.0)

    return {
        "total":            len(rows),
        "status_counts":    status_counts,
        "over_budget":      over_budget_count,
        "at_risk":          at_risk_count,
        "projects":         rows,
    }


def _system_prompt(ctx: dict, username: str) -> str:
    # Compact project list for context window efficiency
    proj_lines = []
    for p in ctx["projects"]:
        cpi_str = f"CPI={p['cpi']:.2f}" if p["cpi"] else "CPI=N/A"
        spi_str = f"SPI={p['spi']:.2f}" if p["spi"] else "SPI=N/A"
        flags   = []
        if p["over_budget"]:     flags.append("OVER_BUDGET")
        if p["behind_schedule"]: flags.append("BEHIND_SCHEDULE")
        flag_str = " [" + ", ".join(flags) + "]" if flags else ""
        budget_k = f"{p['budget']/1000:.0f}K" if p["budget"] >= 1000 else str(p["budget"])
        proj_lines.append(
            f'  - "{p["name"]}" | {p["status"]} | Budget: {budget_k} SAR | {cpi_str} | {spi_str}{flag_str}'
        )

    proj_block = "\n".join(proj_lines) if proj_lines else "  (no projects)"

    return f"""You are ARIA (AI Resource & Intelligence Assistant), CC Software's expert project management AI.
You are talking to: {username}

LIVE PORTFOLIO DATA ({ctx['total']} projects):
{proj_block}

Summary: {ctx['status_counts']} | Over-budget: {ctx['over_budget']} | At-risk (CPI<1): {ctx['at_risk']}

RULES:
- Answer using the live data above when the question relates to projects
- For EVM/PM theory (CPI, SPI, EVM, WBS, ROI, NPV, BCR, EAC, VAC) give clear, brief explanations
- CPI < 1.0 means over budget; CPI > 1.0 means under budget
- SPI < 1.0 means behind schedule; SPI > 1.0 means ahead of schedule
- Be concise (2-5 sentences or a short list); avoid padding
- Do not invent data not present above
- Use markdown: **bold** for emphasis, bullet lists with "-" for lists
"""
