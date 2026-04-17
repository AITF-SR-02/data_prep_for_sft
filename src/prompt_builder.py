"""
prompt_builder.py — Ahli Konten Belajar (Structural & Grounded)
Lengkap dengan System Prompt Selection dan Dual-Mode (Siswa/Guru).
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
# P0 TEMPLATE — The Knowledge Engine (Strict Authority)
# ============================================================
P0_TEMPLATE = """[INSTRUKSI UTAMA — PRIORITAS P0]
Kamu adalah {ai_name}, seorang Ahli Konten Belajar yang otoritatif dan sangat teknis. Tugasmu adalah melakukan ekstraksi dan strukturisasi materi secara tuntas.

== PROTOKOL ZERO FLUFF & ANTI-MENTOR (CRITICAL) ==
- DILARANG menggunakan sapaan (Halo, Hai).
- DILARANG memberikan pujian/motivasi (Bagus, Semangat). 
- DILARANG menggunakan basa-basi pembuka. Langsung ke konten teknis.

== STRUKTUR JAWABAN WAJIB ==
1. Direct Definition: 1 kalimat definisi formal yang presisi.
2. Grounded Analogy: 1 analogi sistem (mekanika, industri, sawah, pasar). Maks 2 kalimat.
3. Technical Breakdown: Gunakan **bold** untuk istilah kunci dan list bernomor.
4. Mathematical Precision: Gunakan LaTeX untuk SETIAP rumus dan simbol ilmiah ($...$).

== OUTPUT FORMAT ==
Output HARUS dalam format JSON:
{{
  "dialog": [
    {{"role": "user", "content": "..."}},
    {{"role": "assistant", "content": "..."}}
  ]
}}
"""

# ============================================================
# USER PROMPT TEMPLATES
# ============================================================

# --- MODE GURU (Structural Content Engineering) ---
USER_PROMPT_GURU_TEMPLATE = """Berdasarkan teks referensi {mata_pelajaran} (Bab: {bab_judul}), buatlah interaksi {num_turns} putaran antara GURU dan AHLI KONTEN.

ATURAN PRODUKSI GURU:
1. Turn 1 (User): "Susun draf materi pembelajaran yang terstruktur dan aplikatif untuk sub-bab {sub_bab}."
2. Jawaban Ahli (Turn 1): Sajikan modul materi dengan hierarki:
   - **Tujuan Pembelajaran**: Fokus kompetensi teknis.
   - **Peta Konsep**: Gunakan list bersarang (nested list) untuk menunjukkan hubungan antar istilah.
   - **Pembahasan Teknis**: Penjelasan mendalam per sub-poin.
   - **Aplikasi & Studi Kasus Grounded**: minimal 1 contoh riil di Indonesia (UMKM, Pertanian, Bengkel, dll).
   - **Ringkasan Deskriptif**: Intisari teknis.
3. Turn 2+ (Jika ada): Guru meminta pendalaman atau detail spesifik pada salah satu poin bahasan, dan Ahli menjawab dengan detail teknis tambahan.
"""

# --- MODE SISWA (Dynamic Inquiry) ---
USER_PROMPT_SISWA_TEMPLATE = """Berdasarkan teks referensi {mata_pelajaran} (Bab: {bab_judul}), buatlah interaksi edukatif {num_turns} putaran antara SISWA dan AHLI KONTEN.

ATURAN PERTANYAAN SISWA:
1. Gaya Bahasa: Natural siswa SMA Indonesia, tidak kaku, langsung ke inti (Direct).
2. Tipe Pertanyaan: {siswa_style_instruction}

ATURAN JAWABAN AHLI:
1. Jawaban Ahli: Tetap OTORITATIF dan TEKNIS.
2. Turn 1: Wajib bedah min. 80% esensi teks dalam 3-4 paragraf padat isi.
3. Struktur: [Direct Definition] -> [Grounded Analogy] -> [Technical Breakdown] -> [LaTeX].
"""

# ============================================================
# LOGIC FUNCTIONS (The ones that were missing)
# ============================================================

def pilih_system_prompt(mapel: str) -> str:
    """Select a system prompt ID based on subject and weighted probability."""
    is_stem = config.is_in_category(mapel, STEM_SUBJECTS)
    is_humaniora = config.is_in_category(mapel, HUMANIORA_INTI)
    
    pool = []
    if is_stem: pool.append(("SP-01", SP_WEIGHTS["SP-01"]))
    if is_humaniora: pool.append(("SP-02", SP_WEIGHTS["SP-02"]))

    # Universal prompts
    for sp_id in ["SP-03", "SP-04", "SP-05", "SP-07", "SP-08", "SP-09", "SP-10"]:
        pool.append((sp_id, SP_WEIGHTS[sp_id]))
    
    if is_stem or is_humaniora:
        pool.append(("SP-06", SP_WEIGHTS["SP-06"]))

    ids = [sp_id for sp_id, _ in pool]
    weights = [w for _, w in pool]
    return random.choices(ids, weights=weights, k=1)[0]

def build_full_system_prompt(system_prompt_id: str, ai_name: str = None) -> str:
    """Combine P0 master directive with specific style prompt."""
    if ai_name is None: ai_name = AI_NAME

    if system_prompt_id in ["SP-03", "SP-10"]:
        ekstensif_rule = "Responsif & Efisien: Berikan jawaban yang tepat sasaran dan padat."
    else:
        ekstensif_rule = "Ekstensif & Panjang: Bedah konsep secara mendalam (Minimal 3 paragraf isi)."

    p0_block = P0_TEMPLATE.format(ai_name=ai_name, ekstensif_rule=ekstensif_rule)
    sp_text = SYSTEM_PROMPTS.get(system_prompt_id, {}).get("text", "")
    return f"{p0_block}\n\n[INSTRUKSI GAYA — {system_prompt_id}]\n{sp_text}"

def build_user_prompt(mata_pelajaran, bab_judul, sub_bab, num_turns, system_prompt_id, teks_referensi, role="siswa"):
    """Build user prompt with context and role logic."""
    if role == "guru":
        template = USER_PROMPT_GURU_TEMPLATE
        siswa_style_instruction = ""
    else:
        template = USER_PROMPT_SISWA_TEMPLATE
        if random.random() < 0.5:
            siswa_style_instruction = "Pertanyaan SINGKAT & DIRECT (Contoh: 'Apa bedanya A dan B?')."
        else:
            siswa_style_instruction = "Pertanyaan DETAIL & KONTEKSTUAL (Siswa menceritakan kebingungan spesifiknya)."

    return template.format(
        mata_pelajaran=mata_pelajaran,
        bab_judul=bab_judul,
        sub_bab=sub_bab,
        num_turns=num_turns,
        siswa_style_instruction=siswa_style_instruction,
        teks_referensi=teks_referensi
    ) + f"\n\n--- TEKS REFERENSI ---\n{teks_referensi}\n--- AKHIR TEKS ---"