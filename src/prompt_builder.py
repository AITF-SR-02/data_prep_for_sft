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
# P0 TEMPLATE (Bagian 4.6)
# ============================================================
P0_TEMPLATE = """[INSTRUKSI UTAMA — PRIORITAS P0]
Nama kamu adalah {ai_name}. Kamu adalah guru Indonesia yang menggunakan Bahasa Indonesia baku (PUEBI). Aturan ketat:
1. Maksimal 1 kalimat pembuka hangat/analogi singkat, lalu langsung ke materi. Dilarang pakai: "Nah," "Mari kita lihat," "Sekarang Ibu akan..." atau filler serupa.
2. Semua analogi HARUS dari kehidupan sehari-hari masyarakat Indonesia (pasar, sawah, bengkel, warung). DILARANG contoh elit (mall, apartemen, luar negeri).
3. Jika praktikum, gunakan bahan gratis/murah dari rumah.
4. Jangan langsung beri jawaban akhir — tuntun siswa berpikir dulu.
5. Jika siswa salah, validasi positif: "Hampir tepat, coba perhatikan lagi bagian [X] yuk."
6. Format bersih: bold untuk istilah teknis, poin bertingkat.
7. Jika ada tabel/data rusak di referensi, rekonstruksi jadi narasi yang jelas."""


# ============================================================
# USER PROMPT TEMPLATE (Bagian 8.2)
# ============================================================
USER_PROMPT_TEMPLATE = """Berdasarkan teks referensi berikut dari materi {mata_pelajaran} (Bab: {bab_judul}, Sub-bab: {sub_bab}), buatlah percakapan edukatif antara Guru dan Siswa sebanyak {num_turns} putaran.

Instruksi Gaya: {instruksi_gaya}

Aturan:
1. Pertanyaan siswa harus NATURAL — seperti siswa SMA sungguhan yang bertanya.
2. Jawaban guru harus AKURAT berdasarkan teks referensi.
3. Jika teks referensi memiliki tabel yang berantakan, abaikan kerusakan format dan rekonstruksi data tersebut menjadi penjelasan naratif yang akurat.
4. Output HARUS dalam format: Siswa: "..." / Guru: "..."
5. JANGAN menambahkan informasi yang TIDAK ADA di teks referensi.

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

    p0_block = P0_TEMPLATE.format(ai_name=ai_name)

    sp_data = SYSTEM_PROMPTS.get(system_prompt_id, {})
    sp_text = sp_data.get("text", "")

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
