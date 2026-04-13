"""
model_selector.py — Model selection and cost optimization.
Mengikuti PRD v2.1, Bagian 7.3 (Logika Pemilihan Model).
"""
import random
import config
from config import (
    MODELS,
    FREE_MODELS,
    STEM_SUBJECTS,
    HUMANIORA_INTI,
    BAHASA_SOSIAL,
    PRIORITY_STEM_PREMIUM,
)


def pilih_model(num_turns: int, mapel: str, system_prompt_id: str) -> str:
    """
    Select the appropriate OpenRouter model based on:
    - Number of turns (1, 2, 3)
    - Subject category (STEM, Humaniora, Bahasa & Sosial, Lainnya)
    - System prompt type (reasoning vs others)

    Returns: OpenRouter model ID string.
    """
    # TEST MODE: always use free models
    if config.TEST_MODE:
        return random.choice(FREE_MODELS)

    is_stem = config.is_in_category(mapel, STEM_SUBJECTS)
    is_humaniora_inti = config.is_in_category(mapel, HUMANIORA_INTI)
    is_bahasa_sosial = config.is_in_category(mapel, BAHASA_SOSIAL)
    is_priority_premium = config.is_in_category(mapel, PRIORITY_STEM_PREMIUM)
    is_reasoning_prompt = system_prompt_id in ["SP-06", "SP-09"]

    # RULE 1: 3-Turn + priority premium STEM -> Tier S (Claude)
    if num_turns == 3 and is_priority_premium:
        return MODELS["claude"]

    # RULE 2: 3-Turn + STEM/Humaniora lain ATAU reasoning prompt -> Tier S (DeepSeek R1)
    if num_turns == 3 and (is_stem or is_humaniora_inti or is_reasoning_prompt):
        return MODELS["deepseek_r1"]

    # RULE 3: 3-Turn + non-priority -> Tier A
    if num_turns == 3:
        return random.choice([MODELS["gemini_25_flash"], MODELS["gpt4o_mini"]])

    # RULE 4: 2-Turn -> Tier A (3 model alternation)
    if num_turns == 2:
        return random.choice([
            MODELS["gpt4o_mini"],
            MODELS["gemini_25_flash"],
            MODELS["llama4_maverick"],
        ])

    # RULE 5: 1-Turn + STEM/Humaniora Inti -> Tier A
    if num_turns == 1 and (is_stem or is_humaniora_inti):
        return random.choice([MODELS["gemini_20_flash"], MODELS["gemini_25_flash"]])

    # RULE 6: 1-Turn + Bahasa & Sosial -> Tier B
    if num_turns == 1 and is_bahasa_sosial:
        return MODELS["gemini_20_flash"]

    # RULE 7: 1-Turn + lainnya -> Tier B (cheapest)
    return random.choice([MODELS["gemini_20_flash"], MODELS["deepseek_v3"]])


def get_model_tier(model_id: str) -> str:
    """Return the tier label for a given model ID."""
    tier_s = [MODELS["claude"], MODELS["deepseek_r1"]]
    tier_a = [MODELS["gemini_25_flash"], MODELS["gpt4o_mini"], MODELS["llama4_maverick"]]
    tier_b = [MODELS["gemini_20_flash"], MODELS["deepseek_v3"], MODELS["qwen"]]

    if model_id in tier_s:
        return "S"
    elif model_id in tier_a:
        return "A"
    elif model_id in tier_b:
        return "B"
    elif model_id in FREE_MODELS:
        return "F"
    return "?"


def pilih_num_turns() -> int:
    """
    Randomly determine the number of turns based on distribution.
    50% -> 1-turn, 25% -> 2-turn, 25% -> 3-turn.
    """
    r = random.random()
    if r < 0.50:
        return 1
    elif r < 0.75:
        return 2
    else:
        return 3
