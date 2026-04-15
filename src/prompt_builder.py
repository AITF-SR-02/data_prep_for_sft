"""
prompt_builder.py — Build system prompt (P0 + SP) and user prompt.
Mengikuti PRD v2.1, Bagian 4.6, 5.3, 8.2, 8.3.
"""
import random
import config
from config import (
    AI_NAME,
    SYSTEM_PROMPTS,
    SP_WEIGHTS,
    STYLE_INSTRUCTIONS,
    STEM_SUBJECTS,
    HUMANIORA_INTI,
)


# ============================================================
# P0 TEMPLATE — "Ahli Konten Belajar" (v2.3)
# ============================================================
# [DIUBAH] Persona dilembutkan menjadi "Otoritatif namun Suportif"
P0_TEMPLATE = """[INSTRUKSI UTAMA — PRIORITAS P0]
Kamu adalah {ai_name}, seorang Ahli Konten Belajar. Tugasmu adalah menyampaikan materi secara tuntas, efisien, dan suportif. 

== ATURAN TURN & EFISIENSI (THE 3-TURN LIMIT) ==
- Maksimal 3 Turn. Jangan biarkan dialog berlanjut lebih dari 3 kali tanya-jawab.
- Tuntas di Awal: Di turn PERTAMA, berikan penjelasan komprehensif yang mencakup 80% konsep utama.

== STRUKTUR JAWABAN WAJIB (STRUCTURAL SOPHISTICATION) ==
1. Direct Definition: 1 kalimat definisi yang presisi.
2. Grounded Analogy: 1 analogi lokal Indonesia (pasar, sawah, bengkel). Maks 2 kalimat.
3. Technical Breakdown: Gunakan **bold** untuk istilah kunci dan list bernomor.
4. Mathematical Accuracy (OPSIONAL): Gunakan LaTeX HANYA jika ada rumus.

== CONSTRAINT PERSONA & PENDEKATAN ==
- {ekstensif_rule}
- Persona Otoritatif Suportif: Fokus pada transfer Logika dan Fakta, namun tetap gunakan nada yang mendukung pembelajaran. Dilarang basa-basi kosong ("Wah bagus sekali"), tapi boleh menggunakan jembatan pemikiran ("Mari kita bedah rumusnya...").
- Analogi Akar Rumput: HANYA gunakan analogi masyarakat Indonesia (sawah, warung, angkot). DILARANG contoh elit.

== OUTPUT FORMAT (CRITICAL) ==
Output HARUS dalam format JSON dengan skema:
{{
  "dialog": [
    {{"role": "user", "content": "..."}},
    {{"role": "assistant", "content": "..."}}
  ]
}}
DILARANG memberikan teks di luar JSON.
"""


# ============================================================
# USER PROMPT TEMPLATE (Bagian 8.2)
# ============================================================
USER_PROMPT_TEMPLATE = """Berdasarkan teks referensi berikut dari materi {mata_pelajaran} (Bab: {bab_judul}, Sub-bab: {sub_bab}), buatlah interaksi edukatif antara Siswa dan Ahli Konten Belajar sebanyak {num_turns} putaran.

Instruksi Gaya Tambahan: {instruksi_gaya}

Aturan Produksi:
1. Pertanyaan siswa harus NATURAL — seperti siswa SMA sungguhan yang ingin memahami materi secara mendalam.
2. Turn PERTAMA: Jawaban Ahli Konten Belajar WAJIB PANJANG, MENGUASAI, DAN DETAIL. Bedah mekanismenya hingga tuntas (mencakup 80% esensi teks) dalam minimal 3-4 paragraf utuh yang padat isi. Dilarang merangkum singkat.
3. Struktur setiap jawaban Ahli Konten Belajar: Direct Definition → Grounded Analogy → Technical Breakdown → (LaTeX HANYA jika ada rumus, jika tidak ada LEWATI).
4. Output HARUS dalam format: Siswa: "..." / Ahli Konten Belajar: "..."
5. JANGAN menambahkan informasi yang tidak ada di teks referensi.
6. Turn 2+: Pendalaman spesifik atau ekspansi konsep baru secara ekstensif — BUKAN apresiasi sosial atau filler.
7. Jika ada tabel rusak di referensi, rekonstruksi menjadi penjelasan naratif yang tajam.
8. DILARANG KERAS menambahkan komentar, catatan, atau kalimat apapun DI LUAR dialog Siswa/Ahli Konten Belajar. Output MURNI dialog saja.

--- TEKS REFERENSI ---
{teks_referensi}
--- AKHIR TEKS REFERENSI ---"""


# ============================================================
# SYSTEM PROMPT SELECTION (Bagian 5.3)
# ============================================================
def pilih_system_prompt(mapel: str) -> str:
    """
    Select a system prompt ID based on subject and weighted probability.
    Returns: SP ID string (e.g., "SP-01").
    """
    is_stem = config.is_in_category(mapel, STEM_SUBJECTS)
    is_humaniora = config.is_in_category(mapel, HUMANIORA_INTI)
    is_stem_or_humaniora_inti = is_stem or is_humaniora

    # Build pool of valid SPs for this subject
    pool = []

    if is_stem:
        pool.append(("SP-01", SP_WEIGHTS["SP-01"]))
    if is_humaniora:
        pool.append(("SP-02", SP_WEIGHTS["SP-02"]))

    # Universal prompts
    pool.append(("SP-03", SP_WEIGHTS["SP-03"]))
    pool.append(("SP-04", SP_WEIGHTS["SP-04"]))
    pool.append(("SP-05", SP_WEIGHTS["SP-05"]))

    if is_stem_or_humaniora_inti:
        pool.append(("SP-06", SP_WEIGHTS["SP-06"]))

    pool.append(("SP-07", SP_WEIGHTS["SP-07"]))
    pool.append(("SP-08", SP_WEIGHTS["SP-08"]))
    pool.append(("SP-09", SP_WEIGHTS["SP-09"]))
    pool.append(("SP-10", SP_WEIGHTS["SP-10"]))

    ids = [sp_id for sp_id, _ in pool]
    weights = [w for _, w in pool]

    return random.choices(ids, weights=weights, k=1)[0]


# ============================================================
# BUILD FULL SYSTEM PROMPT (P0 + SP)
# ============================================================
def build_full_system_prompt(system_prompt_id: str, ai_name: str = None) -> str:
    """
    Combine P0 master directive with specific style prompt.
    Returns the complete system prompt string.
    """
    if ai_name is None:
        ai_name = AI_NAME

    if system_prompt_id in ["SP-03", "SP-10"]:
        ekstensif_rule = "Responsif & Efisien: Berikan jawaban yang tepat sasaran dan padat, JANGAN bertele-tele."
    else:
        ekstensif_rule = "Ekstensif & Panjang: Bedah konsep secara mendalam (Minimal 3 paragraf isi yang padat materi) jika user bertanya hal konseptual."

    p0_block = P0_TEMPLATE.format(ai_name=ai_name, ekstensif_rule=ekstensif_rule)
    sp_text = SYSTEM_PROMPTS.get(system_prompt_id, {}).get("text", "")
    style_block = f"[INSTRUKSI GAYA — {system_prompt_id}]\n{sp_text}"

    return p0_block + "\n\n" + style_block


# ============================================================
# BUILD USER PROMPT
# ============================================================
def build_user_prompt(
    mata_pelajaran: str,
    bab_judul: str,
    sub_bab: str,
    num_turns: int,
    system_prompt_id: str,
    teks_referensi: str,
) -> str:
    """
    Build the user prompt with context and style instructions.
    """
    instruksi_gaya = STYLE_INSTRUCTIONS.get(system_prompt_id, "")

    return USER_PROMPT_TEMPLATE.format(
        mata_pelajaran=mata_pelajaran,
        bab_judul=bab_judul,
        sub_bab=sub_bab,
        num_turns=num_turns,
        instruksi_gaya=instruksi_gaya,
        teks_referensi=teks_referensi,
    )
