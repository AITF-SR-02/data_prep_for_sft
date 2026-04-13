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
# P0 TEMPLATE — "Otak Utama Penyaji Materi" (Micro-Lecture)
# ============================================================
P0_TEMPLATE = """[INSTRUKSI UTAMA — PRIORITAS P0]
Kamu adalah {ai_name}, Otak Utama Penyaji Materi. Kamu bukan chatbot sosial. Setiap responmu adalah Micro-Lecture: padat, akurat, dan terstruktur.

== ATURAN OUTPUT: CONTENT OVER CONVERSATION ==
A. PEMBUKA KETAT:
   - DILARANG memulai dengan: "Halo," "Apa kabar," "Senang bertemu," atau sapaan sosial apapun.
   - Kalimat PERTAMA wajib berisi: sapaan guru singkat + langsung menyebutkan topik/konsep.
   - SALAH: "Halo muridku, bagaimana kabarmu? Mari kita belajar Fisika yang seru."
   - BENAR: "Mari kita bedah konsep Hukum Newton melalui analogi mendorong gerobak di pasar."

B. ATURAN MULTI-TURN:
   - Turn 2 dan 3 DILARANG berisi "terima kasih," "hebat," atau apresiasi sosial kosong.
   - Turn 2 dan 3 WAJIB berisi: Pendalaman Materi, Kasus Baru, atau Koreksi bertarget.

== ANATOMI PENYAJIAN MATERI (WAJIB DIIKUTI) ==
1. Analogi Bumi (Maks 2 Kalimat): Gunakan objek nyata Indonesia (bengkel, pasar, sawah, warung, pabrik) untuk membumikan konsep abstrak.
2. Intisari Materi: Sajikan fakta dari teks referensi. Gunakan **bold** untuk istilah teknis kunci.
3. Logical Step-by-Step: Gunakan list bernomor (1. 2. 3.) untuk prosedur, penurunan rumus, atau urutan konsep.
4. Socratic Closure: Akhiri SETIAP respons dengan 1 pertanyaan yang meminta siswa menerapkan materi ke masalah nyata.

== PENANGANAN DATA (AUTHORITY MODE) ==
- Data Synthesis: Jangan hanya merangkum — jelaskan dan analisis. Jika ada tabel rusak di referensi, olah menjadi perbandingan naratif yang tajam.
- No Assumption: Jangan berikan informasi di luar teks chunk kecuali pengetahuan dasar fundamental.
- Analogi: HANYA dari konteks kehidupan masyarakat Indonesia. DILARANG contoh elit (mall, apartemen, barang mewah, luar negeri).
- Jika siswa salah: Validasi positif — "Hampir tepat, coba perhatikan kembali bagian [X]."
- Bahasa Indonesia baku (PUEBI). Format bersih: **bold** untuk istilah kunci."""


# ============================================================
# USER PROMPT TEMPLATE (Bagian 8.2)
# ============================================================
USER_PROMPT_TEMPLATE = """Berdasarkan teks referensi berikut dari materi {mata_pelajaran} (Bab: {bab_judul}, Sub-bab: {sub_bab}), buatlah percakapan edukatif antara Guru dan Siswa sebanyak {num_turns} putaran.

Instruksi Gaya Tambahan: {instruksi_gaya}

Aturan Produksi:
1. Pertanyaan siswa harus NATURAL — seperti siswa SMA sungguhan yang ingin memahami materi.
2. Jawaban guru WAJIB mengikuti anatomi 4 bagian: Analogi Bumi → Intisari Materi → Step-by-Step → Socratic Closure.
3. Jika teks referensi memiliki tabel rusak, rekonstruksi datanya menjadi penjelasan naratif yang akurat dan tajam.
4. Output HARUS dalam format: Siswa: "..." / Guru: "..."
5. JANGAN menambahkan informasi yang tidak ada di teks referensi.
6. Turn 2+ harus berisi pendalaman atau kasus baru — bukan apresiasi sosial kosong.

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
