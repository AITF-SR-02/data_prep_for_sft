"""
generator.py - Core SFT generation logic.
Mengikuti PRD v2.1: read chunk -> match -> build prompt -> call API -> parse -> save.
(Diperbarui untuk Structured Output / JSON Mode)
"""
import json
import os
from typing import Optional

from openai import OpenAI

import config

from config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
)
from matcher import MatchResult, match_chunk
from prompt_builder import (
    pilih_system_prompt,
    build_full_system_prompt,
    build_user_prompt,
)
from model_selector import pilih_model, get_model_tier
from utils import (
    extract_chunk_text,
    extract_metadata,
    retry_with_backoff,
    log_entry,
    determine_num_turns,
)


# ============================================================
# API CLIENT
# ============================================================
def create_client() -> OpenAI:
    """Create OpenRouter API client (OpenAI-compatible)."""
    if not OPENROUTER_API_KEY:
        raise ValueError(
            "OPENROUTER_API_KEY not set! Add it to your .env file.\n"
            "Example: OPENROUTER_API_KEY=sk-or-v1-xxxxx"
        )
    return OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
    )


def call_api_json(
    client: OpenAI,
    model_id: str,
    system_prompt: str,
    user_prompt: str,
) -> Optional[dict]:
    """
    Call OpenRouter API and force JSON output.
    Uses retry_with_backoff for rate limiting.
    """
    def _make_call():
        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.6, # Sedikit diturunkan agar format JSON lebih stabil
            max_tokens=4096,
            response_format={"type": "json_object"} # Memaksa output berupa JSON
        )
        return response.choices[0].message.content

    try:
        raw_output = retry_with_backoff(_make_call)
        if raw_output:
            return json.loads(raw_output) # Langsung parse ke Dictionary Python
        return None
    except json.JSONDecodeError:
        print("[ERROR] Output dari API bukan JSON yang valid.")
        return None
    except Exception as e:
        print(f"[ERROR] API call failed after retries: {e}")
        return None


# ============================================================
# SINGLE CHUNK PROCESSING
# ============================================================
def process_single_chunk(
    chunk: dict,
    mapping: list[dict],
    client: OpenAI,
    is_merdeka: bool = True,
) -> Optional[dict]:
    """
    Process a single chunk through the full pipeline:
    1. Extract metadata
    2. Match to curriculum (if Merdeka)
    3. Select system prompt + turns + model
    4. Build prompts
    5. Call API (JSON Mode)
    6. Extract dialog & Build final SFT entry

    Returns: dict in OpenAI Messages format with metadata, or None on failure.
    """
    chunk_id = chunk.get("_chunk_id", -1)
    chunk_text = extract_chunk_text(chunk)
    meta = extract_metadata(chunk)

    mapel = meta.get("mata_pelajaran", "")
    kelas = meta.get("kelas", "")
    kurikulum = meta.get("kurikulum", "")

    # --- STEP 1: Matching ---
    if is_merdeka:
        match_result = match_chunk(chunk_text, mapping, kelas=kelas, mapel=mapel)
        if not match_result.matched:
            log_entry(chunk_id, "skipped", "no_match")
            return None
        bab_judul = match_result.bab_judul
        sub_bab = match_result.sub_bab
        match_layer = match_result.layer
        match_score = match_result.score
    else:
        # Phase 2: K-13/KTSP - no matching available
        bab_judul = "[dari konteks buku]"
        sub_bab = "[dari konteks buku]"
        match_layer = "none"
        match_score = 0
        match_result = MatchResult(matched=True, layer="none", score=0)

    # --- STEP 2: Select system prompt ---
    sp_id = pilih_system_prompt(mapel)

    # --- STEP 3: Select turns ---
    num_turns = determine_num_turns()

    # --- STEP 4: Select model ---
    model_id = pilih_model(num_turns, mapel, sp_id)

    # --- STEP 5: Build prompts ---
    system_prompt = build_full_system_prompt(sp_id)
    user_prompt = build_user_prompt(
        mata_pelajaran=mapel,
        bab_judul=bab_judul,
        sub_bab=sub_bab,
        num_turns=num_turns,
        system_prompt_id=sp_id,
        teks_referensi=chunk_text,
    )

    # --- STEP 6: Call API (JSON Mode) ---
    tier = get_model_tier(model_id)
    if config.TEST_MODE:
        print(f"  [TEST] chunk={chunk_id} | sp={sp_id} | turns={num_turns} | model={model_id} (Tier {tier})")

    parsed_json = call_api_json(client, model_id, system_prompt, user_prompt)

    # --- STEP 7: Validate JSON Output ---
    if parsed_json is None:
        log_entry(chunk_id, "failed", "api_or_json_error", model_id, sp_id, num_turns)
        return None

    # Pastikan key "dialog" ada dan berupa list (Sesuai skema di prompt_builder.py)
    conversation = parsed_json.get("dialog")
    if not conversation or not isinstance(conversation, list):
        log_entry(chunk_id, "failed", "invalid_json_schema", model_id, sp_id, num_turns)
        return None

    # --- STEP 8: Build final SFT entry ---
    messages = [{"role": "system", "content": system_prompt}] + conversation

    sft_entry = {
        "messages": messages,
        "metadata": {
            "kurikulum": kurikulum,
            "jenjang": meta.get("jenjang", ""),
            "kelas": kelas,
            "mapel": mapel,
            "bab": bab_judul,
            "sub_bab": sub_bab,
            "turns": num_turns,
            "system_prompt_type": sp_id,
            "model_used": model_id,
            "source_chunk_id": chunk_id,
            "match_layer": match_layer,
            "match_score": match_score,
        },
    }

    log_entry(chunk_id, "success", f"matched_{match_layer}", model_id, sp_id, num_turns)
    return sft_entry