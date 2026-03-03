"""
DualMind — Dual-LLM Consensus Chatbot
Railway-ready | Redis sessions | Iterative debate loop reconciler

Reconciliation flow:
  Round 0:  GPT answers, Claude answers (parallel)
  Round 1:  GPT critiques Claude, Claude critiques GPT → both revise (parallel)
            → Agreement check
  Round 2:  (if no agreement) Same cross-critique again
            → Agreement check
  Fallback: Both models vote on the best answer → winner returned
            If split vote → final single-pass merge
"""

import asyncio
import json
import os
import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
import anthropic
import uvicorn

# ── Config ────────────────────────────────────────────────────────────────────
OPENAI_API_KEY    = os.environ["OPENAI_API_KEY"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
REDIS_URL         = os.getenv("REDIS_URL", "redis://localhost:6379")

OPENAI_MODEL      = "gpt-4o"
ANTHROPIC_MODEL   = "claude-opus-4-5"
MAX_DEBATE_ROUNDS = 2        # max cross-critique loops
AGREE_THRESHOLD   = 0.85     # confidence score to consider models aligned
SESSION_TTL       = 60 * 60 * 24 * 7   # 7 days

# ── Clients ───────────────────────────────────────────────────────────────────
openai_client    = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
anthropic_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
redis_client: aioredis.Redis = None

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="DualMind — Consensus AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    global redis_client
    redis_client = await aioredis.from_url(REDIS_URL, decode_responses=True)

@app.on_event("shutdown")
async def shutdown():
    if redis_client:
        await redis_client.aclose()

# ── Redis Session Helpers ─────────────────────────────────────────────────────
async def get_session(session_id: str) -> dict:
    data = await redis_client.get(f"session:{session_id}")
    if data:
        return json.loads(data)
    return {"openai": [], "anthropic": []}

async def save_session(session_id: str, session: dict):
    await redis_client.setex(
        f"session:{session_id}",
        SESSION_TTL,
        json.dumps(session),
    )

async def delete_session(session_id: str):
    await redis_client.delete(f"session:{session_id}")

# ── Models ────────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    gpt_response: str
    claude_response: str
    final_answer: str
    debate_rounds: int
    agreed: bool
    session_id: str

# ── LLM Callers ───────────────────────────────────────────────────────────────
async def call_openai(messages: list[dict]) -> str:
    response = await openai_client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=0.7,
    )
    return response.choices[0].message.content

async def call_anthropic(messages: list[dict]) -> str:
    response = await anthropic_client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=2048,
        messages=messages,
    )
    return response.content[0].text

# ── Debate Loop Helpers ───────────────────────────────────────────────────────
async def check_agreement(gpt_answer: str, claude_answer: str, question: str) -> tuple[bool, float]:
    """
    Ask GPT-4o to judge whether two answers are substantively aligned.
    Returns (agreed: bool, confidence: float).
    """
    prompt = f"""Two AI models answered the same question. Determine if their answers are substantively aligned — meaning a user reading either would get the same essential information and conclusions.

QUESTION: {question}

ANSWER A (GPT-4o): {gpt_answer}

ANSWER B (Claude): {claude_answer}

Respond ONLY in this exact JSON format (no markdown, no extra text):
{{"agreed": true, "confidence": 0.92, "key_differences": "brief note or none"}}"""

    response = await openai_client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    raw = response.choices[0].message.content.strip()
    try:
        # Strip markdown fences if model adds them
        clean = raw.replace("```json", "").replace("```", "").strip()
        data  = json.loads(clean)
        confidence = float(data.get("confidence", 0))
        agreed     = data.get("agreed", False) or confidence >= AGREE_THRESHOLD
        return agreed, confidence
    except Exception:
        return False, 0.0


async def debate_round(
    question: str,
    gpt_answer: str,
    claude_answer: str,
    round_num: int,
) -> tuple[str, str]:
    """
    One cross-critique round — both models revise in parallel:
    - GPT reads Claude's answer, critiques it, improves its own
    - Claude reads GPT's answer, critiques it, improves its own
    """
    gpt_prompt = f"""You are in a structured debate to find the best answer to a user's question.

QUESTION: "{question}"

YOUR PREVIOUS ANSWER:
{gpt_answer}

YOUR OPPONENT (Claude) ANSWERED:
{claude_answer}

ROUND {round_num} INSTRUCTIONS:
1. Identify what Claude got right that you missed or understated
2. Identify what Claude got wrong or could improve
3. Self-critique your own previous answer honestly
4. Write a REVISED, IMPROVED answer incorporating the best of both

Output ONLY your revised answer. No preamble, no commentary."""

    claude_prompt = f"""You are in a structured debate to find the best answer to a user's question.

QUESTION: "{question}"

YOUR PREVIOUS ANSWER:
{claude_answer}

YOUR OPPONENT (GPT-4o) ANSWERED:
{gpt_answer}

ROUND {round_num} INSTRUCTIONS:
1. Identify what GPT-4o got right that you missed or understated
2. Identify what GPT-4o got wrong or could improve
3. Self-critique your own previous answer honestly
4. Write a REVISED, IMPROVED answer incorporating the best of both

Output ONLY your revised answer. No preamble, no commentary."""

    # Both revise simultaneously
    gpt_task = openai_client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": gpt_prompt}],
        temperature=0.5,
    )
    claude_task = anthropic_client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": claude_prompt}],
    )

    gpt_result, claude_result = await asyncio.gather(gpt_task, claude_task)
    return gpt_result.choices[0].message.content, claude_result.content[0].text


async def vote_for_best(question: str, gpt_answer: str, claude_answer: str) -> tuple[str, str]:
    """
    Fallback when models don't converge after max rounds.
    Both models vote on which final answer is better.
    Returns (final_answer, winner: "A" | "B" | "merged").
    """
    vote_prompt = f"""Question: {question}

ANSWER A (GPT-4o final):
{gpt_answer}

ANSWER B (Claude final):
{claude_answer}

Which answer is more accurate, complete, and useful to the user?
Reply with ONLY the single letter "A" or "B"."""

    gpt_vote_task = openai_client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": vote_prompt}],
        temperature=0,
    )
    claude_vote_task = anthropic_client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=5,
        messages=[{"role": "user", "content": vote_prompt}],
    )
    gpt_vote_r, claude_vote_r = await asyncio.gather(gpt_vote_task, claude_vote_task)

    gpt_vote   = gpt_vote_r.choices[0].message.content.strip().upper()
    claude_vote = claude_vote_r.content[0].text.strip().upper()

    # Both agree → clear winner
    if "A" in gpt_vote and "A" in claude_vote:
        return gpt_answer, "A"
    if "B" in gpt_vote and "B" in claude_vote:
        return claude_answer, "B"

    # Split vote → final merge pass
    merge_prompt = f"""Two AI models debated a question across multiple rounds but reached slightly different final answers. Both have been improved through debate. Now merge them into one definitive, concise answer.

QUESTION: {question}

GPT-4o FINAL: {gpt_answer}

CLAUDE FINAL: {claude_answer}

Output ONLY the merged answer:"""

    merge = await anthropic_client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": merge_prompt}],
    )
    return merge.content[0].text, "merged"


# ── Main Reconciler ───────────────────────────────────────────────────────────
async def reconcile(
    user_prompt: str,
    gpt_answer: str,
    claude_answer: str,
) -> tuple[str, int, bool]:
    """
    Iterative debate loop:
      - Up to MAX_DEBATE_ROUNDS rounds of parallel cross-critique
      - After each round: agreement check
      - If agreed → return the more complete of the two answers
      - If not agreed after all rounds → vote-based fallback

    Returns: (final_answer, rounds_taken, agreed)
    """
    current_gpt    = gpt_answer
    current_claude = claude_answer

    for round_num in range(1, MAX_DEBATE_ROUNDS + 1):
        # Both models cross-critique and revise in parallel
        current_gpt, current_claude = await debate_round(
            user_prompt, current_gpt, current_claude, round_num
        )

        # Check convergence
        agreed, confidence = await check_agreement(current_gpt, current_claude, user_prompt)

        if agreed:
            # Return the longer/more detailed of the two converged answers
            final = current_gpt if len(current_gpt) >= len(current_claude) else current_claude
            return final, round_num, True

    # Never converged → vote fallback
    final, _ = await vote_for_best(user_prompt, current_gpt, current_claude)
    return final, MAX_DEBATE_ROUNDS, False


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    session = await get_session(req.session_id)

    user_msg = {"role": "user", "content": req.message}
    session["openai"].append(user_msg)
    session["anthropic"].append(user_msg)

    # Step 1: Initial answers in parallel
    try:
        gpt_response, claude_response = await asyncio.gather(
            call_openai(session["openai"]),
            call_anthropic(session["anthropic"]),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {str(e)}")

    # Step 2: Debate loop reconciliation
    try:
        final_answer, rounds_taken, agreed = await reconcile(
            req.message, gpt_response, claude_response
        )
    except Exception:
        final_answer  = claude_response
        rounds_taken  = 0
        agreed        = False

    # Step 3: Store final answer in both histories
    assistant_msg = {"role": "assistant", "content": final_answer}
    session["openai"].append(assistant_msg)
    session["anthropic"].append(assistant_msg)

    await save_session(req.session_id, session)

    return ChatResponse(
        gpt_response=gpt_response,
        claude_response=claude_response,
        final_answer=final_answer,
        debate_rounds=rounds_taken,
        agreed=agreed,
        session_id=req.session_id,
    )

@app.get("/history/{session_id}")
async def get_history(session_id: str):
    return await get_session(session_id)

@app.delete("/history/{session_id}")
async def clear_history(session_id: str):
    await delete_session(session_id)
    return {"status": "cleared"}

@app.get("/health")
async def health():
    try:
        await redis_client.ping()
        redis_status = "ok"
    except Exception:
        redis_status = "error"
    return {
        "status": "ok",
        "redis": redis_status,
        "models": {"openai": OPENAI_MODEL, "anthropic": ANTHROPIC_MODEL},
        "max_debate_rounds": MAX_DEBATE_ROUNDS,
    }

# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("backend:app", host="0.0.0.0", port=port)
