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
    # TEST MODE: Use deepest Tier B model if running in test (since free models were removed)
    if config.TEST_MODE:
        return config.MODELS["engine_flash"]

    is_stem = config.is_in_category(mapel, STEM_SUBJECTS)
    is_humaniora_inti = config.is_in_category(mapel, HUMANIORA_INTI)
    is_bahasa_sosial = config.is_in_category(mapel, BAHASA_SOSIAL)
    is_priority_premium = config.is_in_category(mapel, PRIORITY_STEM_PREMIUM)
    is_reasoning_prompt = system_prompt_id in ["SP-06", "SP-09"]

    # RULE 1: 3-Turn + priority premium STEM -> Tier S
    if num_turns == 3 and is_priority_premium:
        return random.choice([MODELS["engine_s"], MODELS["engine_a"]])

    # RULE 2: 3-Turn + STEM/Humaniora lain ATAU reasoning prompt -> Tier S
    if num_turns == 3 and (is_stem or is_humaniora_inti or is_reasoning_prompt):
        return random.choice([MODELS["engine_s"], MODELS["engine_a"]])

    # RULE 3: 3-Turn + non-priority -> Tier A
    if num_turns == 3:
        return random.choice([MODELS["engine_b"], MODELS["engine_local"]])

    # RULE 4: 2-Turn + Priority Premium -> 85% Chance for Tier S
    if num_turns == 2 and is_priority_premium:
        if random.random() < 0.85:
            return random.choice([MODELS["engine_s"], MODELS["engine_a"]])
        else:
            return random.choice([MODELS["engine_b"], MODELS["engine_local"]])

    # RULE 4.1: 2-Turn (Non-Priority) -> Tier A
    if num_turns == 2:
        return random.choice([MODELS["engine_b"], MODELS["engine_local"]])

    # RULE 4.5: 1-Turn + Priority Premium -> 85% Chance for Tier S
    if num_turns == 1 and is_priority_premium:
        if random.random() < 0.85:
            # 85% chance to use premium models
            return random.choice([MODELS["engine_s"], MODELS["engine_a"]])
        else:
            # 15% fallback to high-end Tier A
            return random.choice([MODELS["engine_b"], MODELS["engine_local"]])

    # RULE 5: 1-Turn + STEM/Humaniora Inti (Non-Priority) -> Mix Tier A & B
    if num_turns == 1 and (is_stem or is_humaniora_inti):
        return random.choice([
            MODELS["engine_b"], MODELS["engine_local"], 
            MODELS["engine_flash"], MODELS["engine_deepseek"]
        ])

    # RULE 6: 1-Turn + Bahasa & Sosial -> Tier B
    if num_turns == 1 and is_bahasa_sosial:
        return random.choice([MODELS["engine_flash"], MODELS["engine_deepseek"]])

    # RULE 7: 1-Turn + lainnya -> Tier B (cheapest)
    return random.choice([MODELS["engine_flash"], MODELS["engine_deepseek"]])


def get_model_tier(model_id: str) -> str:
    """Return the tier label for a given model ID."""
    tier_s = [MODELS["engine_s"], MODELS["engine_a"]]
    tier_a = [MODELS["engine_b"], MODELS["engine_local"]]
    tier_b = [MODELS["engine_flash"], MODELS["engine_deepseek"]]

    if model_id in tier_s:
        return "S"
    elif model_id in tier_a:
        return "A"
    elif model_id in tier_b:
        return "B"
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
