"""
prompt_builder.py — Ahli Konten Belajar (Structural & Grounded)
Fokus: Materi Murni + Studi Kasus Lokal Indonesia.
"""
import random
import config

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
   - **Aplikasi & Studi Kasus Grounded**: 1 contoh riil di Indonesia (UMKM, Pertanian, Bengkel, dll).
   - **Ringkasan Deskriptif**: Intisari teknis.
3. Turn 2+ (Jika ada): Guru meminta pendalaman atau detail spesifik pada salah satu poin bahasan, dan Ahli menjawab dengan detail teknis tambahan.
"""

# --- MODE SISWA (Direct Inquiry) ---
USER_PROMPT_SISWA_TEMPLATE = """Berdasarkan teks referensi {mata_pelajaran} (Bab: {bab_judul}), buatlah interaksi edukatif {num_turns} putaran antara SISWA dan AHLI KONTEN.

ATURAN PERTANYAAN SISWA:
1. Gaya Bahasa: Natural siswa SMA Indonesia, tidak kaku, langsung ke inti (Direct).
2. Tipe Pertanyaan: {siswa_style_instruction}

ATURAN JAWABAN AHLI:
1. Jawaban Ahli: Tetap OTORITATIF dan TEKNIS.
2. Turn 1: Wajib bedah min. 80% esensi teks dalam 3-4 paragraf padat isi.
3. Struktur: [Direct Definition] -> [Grounded Analogy] -> [Technical Breakdown] -> [LaTeX].
"""

def build_user_prompt(mata_pelajaran, bab_judul, sub_bab, num_turns, teks_referensi, role="siswa"):
    if role == "guru":
        template = USER_PROMPT_GURU_TEMPLATE
        siswa_style_instruction = "" # Tidak dipakai di guru
    else:
        template = USER_PROMPT_SISWA_TEMPLATE
        # KONTROL 50/50 DARI KODE:
        if random.random() < 0.5:
            siswa_style_instruction = "Pertanyaan SINGKAT & DIRECT (Contoh: 'Apa bedanya A dan B?')."
        else:
            siswa_style_instruction = "Pertanyaan DETAIL & KONTEKSTUAL (Siswa menceritakan kebingungan atau skenario real-life)."

    prompt = template.format(
        mata_pelajaran=mata_pelajaran,
        bab_judul=bab_judul,
        sub_bab=sub_bab,
        num_turns=num_turns,
        siswa_style_instruction=siswa_style_instruction
    )
    
    return f"{prompt}\n\n--- TEKS REFERENSI ---\n{teks_referensi}\n--- AKHIR TEKS ---"