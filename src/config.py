"""
config.py — Semua konstanta untuk SFT Data Generator Sekolah Rakyat.
Mengikuti PRD v2.1, Bagian 4.7, 5.2, 7.2, 11.4.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "50"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "5"))
TEST_MODE = os.getenv("TEST_MODE", "true").lower() == "true"

# ============================================================
# PATHS
# ============================================================
GOLD_DATASET_PATH = "data/cpt_dataset/sr_sma_sibi_gold.jsonl"
MAPPING_DIR = "data/mapping_instruct"
MAPPING_FILES = {
    "Kelas 10": os.path.join(MAPPING_DIR, "daftar_materi_kurikulum_merdeka_kelas_10.json"),
    "Kelas 11": os.path.join(MAPPING_DIR, "daftar_materi_kurikulum_merdeka_kelas_11 copy.json"),
    "Kelas 12": os.path.join(MAPPING_DIR, "daftar_materi_kurikulum_merdeka_kelas_12.json"),
}
OUTPUT_DIR = "data/sft_dataset"
LOG_FILE = os.path.join(OUTPUT_DIR, "generation_log.jsonl")
REPORT_FILE = os.path.join(OUTPUT_DIR, "sft_generation_report.txt")
PROGRESS_FILE = os.path.join(OUTPUT_DIR, ".progress.json")

# ============================================================
# P0 CONFIG — Master Directive (Bagian 4.7)
# ============================================================
AI_NAME = "Ahli Konten Belajar"  # Ubah nama di sini saja jika perlu ganti

BANNED_OPENING_WORDS = [
    "Nah,", "Mari kita lihat,", "Sekarang Ibu akan",
    "Oke, jadi", "Baiklah anak-anak", "Halo anak-anak",
    "Selamat pagi anak-anak",
]

BANNED_ELITE_KEYWORDS = [
    "mall", "apartemen", "hotel", "resort", "iPhone",
    "laptop gaming", "luar negeri", "Eropa", "Amerika",
]

# ============================================================
# SUBJECT TIERS & DYNAMIC HELPERS (Bagian 3.4)
# ============================================================
STEM_SUBJECTS = [
    "matematika", "fisika", "biologi", "kimia", 
    "informatika"
]

HUMANIORA_INTI = ["sejarah", "ekonomi", "geografi"]

BAHASA_SOSIAL = [
    "bahasa indonesia", "bahasa inggris", "sosiologi", 
    "antropologi", "ipa", "ips", "pancasila", "pkn", "kewarganegaraan"
]

# Premium STEM subjects (get Claude for 3-turn)
PRIORITY_STEM_PREMIUM = ["matematika", "fisika", "kimia", "biologi", "informatika", "ekonomi", "geografi", "sejarah"]

def is_in_category(mapel_name: str, category_keywords: list) -> bool:
    """Check if any keyword dynamically matches inside the subject string."""
    if not mapel_name:
        return False
    mapel_lower = mapel_name.lower()
    return any(kw in mapel_lower for kw in category_keywords)

def get_tier_order(mapel: str) -> int:
    """Return the precedence digit for sorting processing order."""
    if is_in_category(mapel, STEM_SUBJECTS): return 1
    if is_in_category(mapel, HUMANIORA_INTI): return 2
    if is_in_category(mapel, BAHASA_SOSIAL): return 3
    return 4

# ============================================================
# MATCHER THRESHOLDS (Bagian 3.3)
# ============================================================
EXACT_MATCH_MIN_KEYWORDS = 2
FUZZY_MATCH_THRESHOLD = 80       # partial_ratio >= 80
FUZZY_MATCH_MIN_KEYWORDS = 2
TFIDF_SIMILARITY_THRESHOLD = 0.15

# ============================================================
# MODEL IDS (Bagian 7.2 — OpenRouter April 2026)
# ============================================================
MODELS = {
    # Tier S — Premium (Rank 1/2 Intel)
    "engine_s": "google/gemini-3.1-pro-preview",
    "engine_a": "openai/gpt-5.4",
    # Tier A — Standard (Rank 5/8 Intel)
    "engine_b": "anthropic/claude-4.6-sonnet",
    "engine_local": "qwen/qwen3.6-plus",
    # Tier B — Budget (Rank 19 Intel / Open Source)
    "engine_flash": "google/gemini-3-flash-preview",
    "engine_deepseek": "deepseek/deepseek-v3.2",
}

# For TEST_MODE, override all model selections to free tier
FREE_MODELS = [
    "nvidia/nemotron-3-super-120b-a12b:free",
    "openai/gpt-oss-20b:free",
]

# ============================================================
# SYSTEM PROMPTS — Style Instructions (Bagian 5.2)
# Ini HANYA bagian "INSTRUKSI GAYA" — P0 di-inject oleh prompt_builder.
# ============================================================
SYSTEM_PROMPTS = {
    "SP-01": {
        "name": "Default STEM",
        "text": (
            "Fokus pada akurasi rumus, langkah-langkah penyelesaian "
            "(step-by-step reasoning), dan logika ilmiah. "
            "Gunakan notasi matematika yang benar."
        ),
        "condition": "stem",  # Only for STEM subjects
    },
    "SP-02": {
        "name": "Default Humaniora",
        "text": (
            "Fokus pada analisis sosial, konteks sejarah, hubungan sebab-akibat, "
            "dan pemikiran kritis. Hubungkan materi dengan konteks kehidupan nyata "
            "di Indonesia."
        ),
        "condition": "humaniora",  # Only for Humaniora Inti
    },
    "SP-03": {
        "name": "Penjelasan Singkat",
        "text": (
            "Jawab pertanyaan siswa dengan SINGKAT dan PADAT — maksimal 3-4 kalimat "
            "per jawaban. Langsung ke inti materi tanpa basa-basi."
        ),
        "condition": "all",
    },
    "SP-04": {
        "name": "Penjelasan Sederhana",
        "text": (
            "Jelaskan materi dengan BAHASA SEDERHANA yang mudah dipahami anak SMA. "
            "Hindari istilah teknis yang rumit — jika harus menggunakan istilah teknis, "
            "langsung jelaskan artinya dengan kata-kata sehari-hari."
        ),
        "condition": "all",
    },
    "SP-05": {
        "name": "Penjelasan Panjang dan Mendetail",
        "text": (
            "Berikan penjelasan PANJANG, MENDETAIL, dan KOMPREHENSIF. "
            "Bahas materi dari segala sisi: definisi, penjelasan konsep, contoh, "
            "hubungan dengan materi lain, dan penerapan dalam kehidupan nyata. "
            "Setiap jawaban minimal 3-5 paragraf."
        ),
        "condition": "all",
    },
    "SP-06": {
        "name": "Step-by-Step Reasoning",
        "text": (
            "Ajarkan materi dengan pendekatan LANGKAH DEMI LANGKAH (step-by-step). "
            "Setiap penjelasan harus dipecah menjadi langkah bernomor yang jelas. "
            "Untuk soal hitungan, tunjukkan setiap tahap perhitungan. "
            "Untuk konsep teori, buat outline berurutan dari konsep dasar ke kompleks."
        ),
        "condition": "stem_humaniora_inti",  # STEM + Ekonomi + Geografi
    },
    "SP-07": {
        "name": "Analogi dan Contoh Nyata",
        "text": (
            "SELALU gunakan analogi dan contoh nyata dari kehidupan sehari-hari untuk "
            "menjelaskan konsep. Setiap konsep abstrak harus diiringi minimal 1 analogi "
            "yang relatable untuk siswa SMA. "
            "Contoh: jelaskan osmosis dengan analogi teh celup di warung."
        ),
        "condition": "all",
    },
    "SP-08": {
        "name": "Perbandingan Antar Konsep",
        "text": (
            "Jelaskan materi dengan cara MEMBANDINGKAN konsep satu dengan konsep lainnya. "
            "Gunakan format 'perbedaan dan persamaan'. "
            "Jika memungkinkan, buat tabel perbandingan sederhana dalam bentuk teks. "
            "Contoh: bandingkan mitosis vs meiosis."
        ),
        "condition": "all",
    },
    "SP-09": {
        "name": "Gaya Tanya-Jawab Socrates",
        "text": (
            "Gunakan METODE SOCRATES — jawab pertanyaan siswa dengan pertanyaan balik "
            "yang memancing siswa berpikir sendiri, lalu berikan penjelasan setelah "
            "siswa mencoba menjawab. Bantu siswa menemukan jawaban melalui proses "
            "berpikir, bukan langsung memberikan jawaban."
        ),
        "condition": "all",
    },
    "SP-10": {
        "name": "Rangkuman dan Poin Penting",
        "text": (
            "Jelaskan materi dalam bentuk RANGKUMAN dan POIN-POIN PENTING. "
            "Gunakan format bullet points atau numbering. "
            "Setiap poin harus ringkas tapi informatif. "
            "Di akhir, berikan 'Hal yang Perlu Diingat' sebagai highlight."
        ),
        "condition": "all",
    },
}

# Weights for system prompt selection (Bagian 5.3)
# NOTE: Biased toward long/detailed explanations for richer SFT data.
#       SP-03 (Singkat) and SP-10 (Rangkuman) kept minimal.
SP_WEIGHTS = {
    "SP-01": 15,   # Default STEM
    "SP-02": 15,   # Default Humaniora
    "SP-03": 3,    # Penjelasan Singkat (↓ dari 12)
    "SP-04": 10,   # Penjelasan Sederhana
    "SP-05": 18,   # Penjelasan Panjang dan Mendetail (↑ dari 10)
    "SP-06": 14,   # Step-by-Step Reasoning (↑ dari 10)
    "SP-07": 12,   # Analogi dan Contoh Nyata (↑ dari 8)
    "SP-08": 8,    # Perbandingan Antar Konsep
    "SP-09": 5,    # Gaya Tanya-Jawab Socrates
    "SP-10": 2,    # Rangkuman dan Poin Penting (↓ dari 5)
}

# Style instructions for user prompt (Bagian 8.3)
STYLE_INSTRUCTIONS = {
    "SP-01": "Fokus pada rumus dan penyelesaian soal.",
    "SP-02": "Fokus pada analisis sosial dan konteks sejarah.",
    "SP-03": "Jawaban guru harus SINGKAT, maksimal 3-4 kalimat.",
    "SP-04": "Gunakan bahasa sederhana yang mudah dipahami, tanpa istilah rumit.",
    "SP-05": "Jawaban guru harus PANJANG dan MENDETAIL, minimal 3-5 paragraf.",
    "SP-06": "Gunakan format LANGKAH DEMI LANGKAH bernomor.",
    "SP-07": "Gunakan ANALOGI dan CONTOH NYATA dari kehidupan sehari-hari.",
    "SP-08": "Bandingkan konsep yang berbeda — buat tabel perbandingan jika memungkinkan.",
    "SP-09": "Guru menjawab dengan PERTANYAAN BALIK dulu, baru menjelaskan.",
    "SP-10": "Jawaban dalam format POIN-POIN PENTING / bullet points.",
}

# ============================================================
# TURN DISTRIBUTION (Bagian 6.1 — JANGAN DIUBAH)
# ============================================================
TURN_THRESHOLDS = {
    1: 0.50,  # random() < 0.50 -> 1-turn
    2: 0.75,  # random() < 0.75 -> 2-turn
    3: 1.00,  # sisanya -> 3-turn
}
