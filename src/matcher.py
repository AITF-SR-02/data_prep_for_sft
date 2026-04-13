"""
matcher.py — 3-Layer Metadata Injection Matcher.
Mengikuti PRD v2.1, Bagian 3.3 (Algoritma Matching Baru).

Layer 1: Exact Keyword Match
Layer 2: Fuzzy Keyword Match (rapidfuzz)
Layer 3: TF-IDF Cosine Similarity (scikit-learn)
"""
import json
import os
from typing import Optional

from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import (
    MAPPING_FILES,
    EXACT_MATCH_MIN_KEYWORDS,
    FUZZY_MATCH_THRESHOLD,
    FUZZY_MATCH_MIN_KEYWORDS,
    TFIDF_SIMILARITY_THRESHOLD,
)


# ============================================================
# DATA STRUCTURES
# ============================================================
class MatchResult:
    """Result from the matching algorithm."""

    def __init__(
        self,
        matched: bool,
        bab_judul: str = "Tidak Teridentifikasi",
        bab_nomor: int = 0,
        sub_bab: str = "Tidak Teridentifikasi",
        keywords: list = None,
        layer: str = "none",
        score: float = 0.0,
    ):
        self.matched = matched
        self.bab_judul = bab_judul
        self.bab_nomor = bab_nomor
        self.sub_bab = sub_bab
        self.keywords = keywords or []
        self.layer = layer   # "exact", "fuzzy", "tfidf", "none"
        self.score = score

    def to_dict(self):
        return {
            "matched": self.matched,
            "bab_judul": self.bab_judul,
            "bab_nomor": self.bab_nomor,
            "sub_bab": self.sub_bab,
            "keywords": self.keywords,
            "layer": self.layer,
            "score": self.score,
        }


# ============================================================
# LOAD MASTER MAPPING
# ============================================================
def load_master_mapping() -> list[dict]:
    """Load all mapping files and return a flat list of entries."""
    all_entries = []

    for kelas_label, filepath in MAPPING_FILES.items():
        if not os.path.exists(filepath):
            print(f"[WARN] Mapping file not found: {filepath}")
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Handle both list and dict formats
        entries = data if isinstance(data, list) else data.get("data", data.get("entries", []))

        for entry in entries:
            # Normalize entry structure
            normalized = {
                "kurikulum": entry.get("kurikulum", "Kurikulum Merdeka"),
                "jenjang": entry.get("jenjang", "SMA/SMK/MA"),
                "kelas": entry.get("kelas", kelas_label),
                "mata_pelajaran": entry.get("mata_pelajaran", ""),
                "bab_nomor": entry.get("bab_nomor", 0),
                "bab_judul": entry.get("bab_judul", ""),
                "sub_bab": entry.get("sub_bab", ""),
                "keywords": entry.get("keywords", []),
            }
            all_entries.append(normalized)

    print(f"[INFO] Loaded {len(all_entries)} mapping entries from {len(MAPPING_FILES)} files.")
    return all_entries


def filter_mapping_by_kelas(mapping: list[dict], kelas: str) -> list[dict]:
    """Filter mapping entries to only those matching the chunk's kelas."""
    if not kelas:
        return mapping

    # Normalize: "10" matches "Kelas 10", "kelas 10", etc.
    kelas_num = "".join(filter(str.isdigit, str(kelas)))
    return [
        e for e in mapping
        if kelas_num and kelas_num in "".join(filter(str.isdigit, str(e.get("kelas", ""))))
    ]


def filter_mapping_by_mapel(mapping: list[dict], mapel: str) -> list[dict]:
    """Filter mapping entries to only those matching the chunk's mata_pelajaran."""
    if not mapel:
        return mapping
    mapel_lower = mapel.lower().strip()
    return [
        e for e in mapping
        if mapel_lower in e.get("mata_pelajaran", "").lower()
    ]


# ============================================================
# LAYER 1: EXACT KEYWORD MATCH
# ============================================================
def _exact_match(chunk_text: str, mapping: list[dict]) -> Optional[MatchResult]:
    """
    Layer 1: Exact keyword match.
    - Lowercase everything.
    - Count how many keywords from each entry appear in chunk_text.
    - Need >= EXACT_MATCH_MIN_KEYWORDS.
    - Pick entry with most keyword matches (tie-break: lowest bab_nomor).
    """
    chunk_lower = chunk_text.lower()
    best_entry = None
    best_count = 0
    best_bab_nomor = float("inf")

    for entry in mapping:
        keywords = entry.get("keywords", [])
        if not keywords:
            continue

        matched_count = 0
        for kw in keywords:
            if kw.lower() in chunk_lower:
                matched_count += 1

        if matched_count >= EXACT_MATCH_MIN_KEYWORDS:
            bab_nomor = entry.get("bab_nomor", 999)
            # Pick highest count, then lowest bab_nomor as tiebreak
            if (matched_count > best_count) or (
                matched_count == best_count and bab_nomor < best_bab_nomor
            ):
                best_entry = entry
                best_count = matched_count
                best_bab_nomor = bab_nomor

    if best_entry:
        return MatchResult(
            matched=True,
            bab_judul=best_entry["bab_judul"],
            bab_nomor=best_entry.get("bab_nomor", 0),
            sub_bab=best_entry.get("sub_bab", ""),
            keywords=best_entry.get("keywords", []),
            layer="exact",
            score=float(best_count),
        )
    return None


# ============================================================
# LAYER 2: FUZZY KEYWORD MATCH
# ============================================================
def _fuzzy_match(chunk_text: str, mapping: list[dict]) -> Optional[MatchResult]:
    """
    Layer 2: Fuzzy keyword match using rapidfuzz.
    - For each keyword, compute fuzz.partial_ratio(keyword, chunk_text).
    - Score >= FUZZY_MATCH_THRESHOLD counts as match.
    - Need >= FUZZY_MATCH_MIN_KEYWORDS fuzzy matches.
    - Pick entry with highest cumulative fuzzy score.
    """
    chunk_lower = chunk_text.lower()
    best_entry = None
    best_fuzzy_count = 0
    best_cumulative_score = 0.0
    best_bab_nomor = float("inf")

    for entry in mapping:
        keywords = entry.get("keywords", [])
        if not keywords:
            continue

        fuzzy_count = 0
        cumulative_score = 0.0

        for kw in keywords:
            score = fuzz.partial_ratio(kw.lower(), chunk_lower)
            if score >= FUZZY_MATCH_THRESHOLD:
                fuzzy_count += 1
                cumulative_score += score

        if fuzzy_count >= FUZZY_MATCH_MIN_KEYWORDS:
            bab_nomor = entry.get("bab_nomor", 999)
            if (cumulative_score > best_cumulative_score) or (
                cumulative_score == best_cumulative_score
                and bab_nomor < best_bab_nomor
            ):
                best_entry = entry
                best_fuzzy_count = fuzzy_count
                best_cumulative_score = cumulative_score
                best_bab_nomor = bab_nomor

    if best_entry:
        return MatchResult(
            matched=True,
            bab_judul=best_entry["bab_judul"],
            bab_nomor=best_entry.get("bab_nomor", 0),
            sub_bab=best_entry.get("sub_bab", ""),
            keywords=best_entry.get("keywords", []),
            layer="fuzzy",
            score=round(best_cumulative_score, 2),
        )
    return None


# ============================================================
# LAYER 3: TF-IDF COSINE SIMILARITY
# ============================================================
def _tfidf_match(chunk_text: str, mapping: list[dict]) -> Optional[MatchResult]:
    """
    Layer 3: TF-IDF cosine similarity as semantic fallback.
    - Build corpus: chunk_text + concatenated (keywords + bab_judul + sub_bab) per entry.
    - Compute cosine similarity.
    - Need >= TFIDF_SIMILARITY_THRESHOLD.
    """
    if not mapping:
        return None

    # Build corpus: [chunk_text, entry_0_text, entry_1_text, ...]
    corpus = [chunk_text.lower()]
    for entry in mapping:
        entry_text = " ".join([
            entry.get("bab_judul", ""),
            entry.get("sub_bab", ""),
            " ".join(entry.get("keywords", [])),
        ]).lower()
        corpus.append(entry_text)

    try:
        vectorizer = TfidfVectorizer(max_features=5000)
        tfidf_matrix = vectorizer.fit_transform(corpus)

        # Compute similarity between chunk (index 0) and all entries
        similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()

        best_idx = similarities.argmax()
        best_score = similarities[best_idx]

        if best_score >= TFIDF_SIMILARITY_THRESHOLD:
            best_entry = mapping[best_idx]
            return MatchResult(
                matched=True,
                bab_judul=best_entry["bab_judul"],
                bab_nomor=best_entry.get("bab_nomor", 0),
                sub_bab=best_entry.get("sub_bab", ""),
                keywords=best_entry.get("keywords", []),
                layer="tfidf",
                score=round(float(best_score), 4),
            )
    except Exception as e:
        print(f"[WARN] TF-IDF matching failed: {e}")

    return None


# ============================================================
# MAIN MATCHING FUNCTION
# ============================================================
def match_chunk(
    chunk_text: str,
    mapping: list[dict],
    kelas: str = "",
    mapel: str = "",
) -> MatchResult:
    """
    Run 3-layer matching. Stop at the first layer that produces a match.

    Args:
        chunk_text: The text content of the chunk.
        mapping: Full master mapping (list of dicts).
        kelas: Optional kelas filter (e.g., "Kelas 10").
        mapel: Optional mata_pelajaran filter.

    Returns:
        MatchResult with layer info.
    """
    # Filter mapping for faster/more accurate matching
    filtered = mapping
    if kelas:
        filtered = filter_mapping_by_kelas(filtered, kelas)
    if mapel:
        filtered = filter_mapping_by_mapel(filtered, mapel)

    # If no filtered entries, try full mapping as fallback
    if not filtered:
        filtered = mapping

    # Layer 1: Exact
    result = _exact_match(chunk_text, filtered)
    if result:
        return result

    # Layer 2: Fuzzy
    result = _fuzzy_match(chunk_text, filtered)
    if result:
        return result

    # Layer 3: TF-IDF
    result = _tfidf_match(chunk_text, filtered)
    if result:
        return result

    # No match found
    return MatchResult(matched=False, layer="none", score=0.0)
