"""
utils.py - Helper functions: logging, retry, validation, data loading.
Mengikuti PRD v2.1, Bagian 10.1-10.4.
"""
import json
import os
import re
import time
from datetime import datetime, timezone
from typing import Optional

from config import LOG_FILE, MAX_RETRIES, BANNED_OPENING_WORDS, BANNED_ELITE_KEYWORDS


# ============================================================
# DATA LOADING
# ============================================================
def load_gold_dataset(filepath: str) -> list[dict]:
    """Load the gold JSONL dataset. Returns list of dicts with text, metadata, chunk_id."""
    chunks = []
    with open(filepath, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                data["_chunk_id"] = idx
                chunks.append(data)
            except json.JSONDecodeError as e:
                print(f"[WARN] Skipping line {idx}: {e}")
    print(f"[INFO] Loaded {len(chunks)} chunks from {filepath}")
    return chunks


def extract_chunk_text(chunk: dict) -> str:
    """Extract the text content from a chunk, removing endoftext token."""
    text = chunk.get("text", "")
    # Remove endoftext token variants
    text = re.sub(r"<\|endoftext\|>", "", text)
    text = re.sub(r"<\\?\|endoftext\\?\|>", "", text)
    return text.strip()


def extract_metadata(chunk: dict) -> dict:
    """Extract metadata from a chunk. Supports both embedded and field-level metadata."""
    # Try direct metadata field first
    meta = chunk.get("metadata", {})
    if meta:
        return {
            "kurikulum": meta.get("kurikulum", ""),
            "jenjang": meta.get("jenjang", ""),
            "kelas": meta.get("kelas", ""),
            "mata_pelajaran": meta.get("mata_pelajaran", ""),
            "sumber": meta.get("sumber", ""),
            "chunk": meta.get("chunk", ""),
        }

    # Fallback: parse from text header "### KONTEKS"
    text = chunk.get("text", "")
    result = {
        "kurikulum": "",
        "jenjang": "",
        "kelas": "",
        "mata_pelajaran": "",
        "sumber": "",
        "chunk": "",
    }

    patterns = {
        "kurikulum": r"Kurikulum:\s*(.+)",
        "jenjang": r"Jenjang:\s*(.+)",
        "kelas": r"Kelas:\s*(.+)",
        "mata_pelajaran": r"Mata Pelajaran:\s*(.+)",
        "sumber": r"Sumber:\s*(.+)",
        "chunk": r"Chunk:\s*(.+)",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result[key] = match.group(1).strip()

    return result


# ============================================================
# PROCESSING ORDER (Bagian 3.4)
# ============================================================
def get_processing_order(all_chunks: list[dict], tier_order: dict) -> list[dict]:
    """
    Order chunks: Phase 1 (Kurikulum Merdeka, sorted by tier) then Phase 2 (K-13/KTSP).
    """
    merdeka_chunks = []
    legacy_chunks = []

    for chunk in all_chunks:
        meta = extract_metadata(chunk)
        kurikulum = meta.get("kurikulum", "")
        if "merdeka" in kurikulum.lower():
            merdeka_chunks.append(chunk)
        else:
            legacy_chunks.append(chunk)

    # Sort merdeka by subject tier using dynamic lowercase matching
    def tier_sort_key(chunk):
        meta = extract_metadata(chunk)
        mapel = meta.get("mata_pelajaran", "")
        import config
        return config.get_tier_order(mapel)

    merdeka_sorted = sorted(merdeka_chunks, key=tier_sort_key)

    print(f"[INFO] Processing order: {len(merdeka_sorted)} Merdeka (Phase 1) + {len(legacy_chunks)} Legacy (Phase 2)")
    return merdeka_sorted + legacy_chunks


# ============================================================
# TURN DISTRIBUTION (Bagian 6.2)
# ============================================================
def determine_num_turns() -> int:
    """50% -> 1-turn, 25% -> 2-turn, 25% -> 3-turn."""
    import random
    r = random.random()
    if r < 0.50:
        return 1
    elif r < 0.75:
        return 2
    else:
        return 3


# ============================================================
# OUTPUT VALIDATION (Bagian 10.2)
# ============================================================
def validate_output(response_text: str) -> bool:
    """Check if API response contains valid Siswa/Guru or Siswa/Ahli Konten Belajar format."""
    if not response_text or not response_text.strip():
        return False
    has_siswa = bool(re.search(r"Siswa\s*:", response_text, re.IGNORECASE))
    has_guru = bool(re.search(r"Guru\s*:", response_text, re.IGNORECASE))
    has_ahli = bool(re.search(r"Ahli Konten Belajar\s*:", response_text, re.IGNORECASE))
    return has_siswa and (has_guru or has_ahli)


def parse_conversation(response_text: str, num_turns: int) -> Optional[list[dict]]:
    """
    Parse the API response into OpenAI Messages format.
    Expected format: Siswa: "..." / Guru: "..." OR Siswa: "..." / Ahli Konten Belajar: "..."

    Returns list of {role, content} dicts, or None if parsing fails.
    """
    messages = []

    # Split by Siswa:/Guru:/Ahli Konten Belajar: markers
    # Pattern matches these markers at the start of a line or after newlines
    parts = re.split(
        r"\n*(?=(?:Siswa|Guru|Ahli Konten Belajar)\s*:)",
        response_text.strip()
    )
    parts = [p.strip() for p in parts if p.strip()]

    for part in parts:
        if re.match(r"^Siswa\s*:", part, re.IGNORECASE):
            content = re.sub(r"^Siswa\s*:\s*", "", part, flags=re.IGNORECASE).strip()
            content = content.strip('"').strip("'").strip()
            if content:
                messages.append({"role": "user", "content": content})
        elif re.match(r"^(?:Guru|Ahli Konten Belajar)\s*:", part, re.IGNORECASE):
            content = re.sub(
                r"^(?:Guru|Ahli Konten Belajar)\s*:\s*", "",
                part, flags=re.IGNORECASE
            ).strip()
            content = content.strip('"').strip("'").strip()
            if content:
                messages.append({"role": "assistant", "content": content})

    # Validate: should have alternating user/assistant pairs
    if len(messages) < 2:
        return None

    # Check alternation
    for i, msg in enumerate(messages):
        expected_role = "user" if i % 2 == 0 else "assistant"
        if msg["role"] != expected_role:
            return None

    return messages


# ============================================================
# QUALITY CHECKS (Post-generation)
# ============================================================
def check_banned_opening(text: str) -> list[str]:
    """Check if response contains banned opening words. Returns list of violations."""
    violations = []
    text_lower = text.lower()
    for word in BANNED_OPENING_WORDS:
        if text_lower.startswith(word.lower()):
            violations.append(f"Banned opening: '{word}'")
    return violations


def check_elite_content(text: str) -> list[str]:
    """Check if response contains elite/privileged content. Returns list of violations."""
    violations = []
    text_lower = text.lower()
    for keyword in BANNED_ELITE_KEYWORDS:
        if keyword.lower() in text_lower:
            violations.append(f"Elite keyword found: '{keyword}'")
    return violations


# ============================================================
# API RETRY WITH EXPONENTIAL BACKOFF (Bagian 10.1)
# ============================================================
def retry_with_backoff(func, *args, max_retries: int = None, **kwargs):
    """
    Call func with exponential backoff on failure.
    Formula: wait_time = min(2^retry_count * 1.0, 60.0)
    """
    if max_retries is None:
        max_retries = MAX_RETRIES

    last_error = None
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            error_str = str(e)

            # Check if rate limited (429)
            if "429" in error_str or "rate" in error_str.lower():
                wait_time = min(2 ** attempt * 1.0, 60.0)
                print(f"[RETRY {attempt + 1}/{max_retries}] Rate limited. Waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
            else:
                wait_time = min(2 ** attempt * 0.5, 30.0)
                print(f"[RETRY {attempt + 1}/{max_retries}] Error: {error_str[:100]}. Waiting {wait_time:.1f}s...")
                time.sleep(wait_time)

    raise last_error


# ============================================================
# LOGGING (Bagian 10.3)
# ============================================================
def log_entry(
    chunk_id: int,
    status: str,
    reason: str,
    model_used: str = "",
    system_prompt: str = "",
    turns: int = 0,
    log_file: str = None,
):
    """Append a log entry to generation_log.jsonl."""
    if log_file is None:
        log_file = LOG_FILE

    entry = {
        "chunk_id": chunk_id,
        "status": status,
        "reason": reason,
        "model_used": model_used,
        "system_prompt": system_prompt,
        "turns": turns,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ============================================================
# PROGRESS TRACKING (Bagian 11.3 - Resume from last batch)
# ============================================================
def load_progress(progress_file: str) -> dict:
    """Load progress from file. Returns dict with last_chunk_id processed."""
    if os.path.exists(progress_file):
        with open(progress_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_chunk_id": -1, "processed_count": 0, "batch_number": 0}


def save_progress(progress_file: str, last_chunk_id: int, processed_count: int, batch_number: int):
    """Save progress to file for resume capability."""
    os.makedirs(os.path.dirname(progress_file), exist_ok=True)
    data = {
        "last_chunk_id": last_chunk_id,
        "processed_count": processed_count,
        "batch_number": batch_number,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(progress_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ============================================================
# BATCH FILE HELPERS
# ============================================================
def get_batch_filename(output_dir: str, batch_number: int) -> str:
    """Generate batch filename like sft_batch_001.jsonl."""
    return os.path.join(output_dir, f"sft_batch_{batch_number:03d}.jsonl")


def write_batch(filepath: str, entries: list[dict]):
    """Write a list of SFT entries to a JSONL file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "a", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"[INFO] Wrote {len(entries)} entries to {filepath}")
