"""
main.py - Entry point for SFT Data Generator.
Mengikuti PRD v2.1, Bagian 11 (Instruksi untuk Pelaksana).

Usage:
    uv run python main.py                    # Test mode (10 chunks, free models)
    uv run python main.py --production       # Production mode (all chunks)
    uv run python main.py --batch-size 20    # Custom batch size
    uv run python main.py --resume           # Resume from last progress
    uv run python main.py --test-chunks 5    # Test with N chunks
"""
import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone

from tqdm import tqdm

from config import (
    GOLD_DATASET_PATH,
    OUTPUT_DIR,
    LOG_FILE,
    REPORT_FILE,
    PROGRESS_FILE,
    BATCH_SIZE,
    TEST_MODE,
)
from matcher import load_master_mapping
from generator import create_client, process_single_chunk
from utils import (
    load_gold_dataset,
    extract_metadata,
    get_processing_order,
    load_progress,
    save_progress,
    get_batch_filename,
    write_batch,
)


def parse_args():
    parser = argparse.ArgumentParser(description="SFT Data Generator - Sekolah Rakyat")
    parser.add_argument("--production", action="store_true", help="Run in production mode (overrides TEST_MODE)")
    parser.add_argument("--batch-size", type=int, default=None, help=f"Chunks per batch (default: {BATCH_SIZE})")
    parser.add_argument("--resume", action="store_true", help="Resume from last saved progress")
    parser.add_argument("--test-chunks", type=int, default=10, help="Number of chunks for test mode (default: 10)")
    return parser.parse_args()


def generate_report(log_file: str, report_file: str):
    """Generate summary report from generation log."""
    if not os.path.exists(log_file):
        print("[WARN] No log file found, skipping report generation.")
        return

    entries = []
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    total = len(entries)
    status_counts = Counter(e["status"] for e in entries)
    model_counts = Counter(e.get("model_used", "N/A") for e in entries if e["status"] == "success")
    sp_counts = Counter(e.get("system_prompt", "N/A") for e in entries if e["status"] == "success")
    turn_counts = Counter(e.get("turns", 0) for e in entries if e["status"] == "success")
    reason_counts = Counter(e.get("reason", "N/A") for e in entries)

    report_lines = [
        "=" * 60,
        "SFT GENERATION REPORT - Sekolah Rakyat",
        f"Generated at: {datetime.now(timezone.utc).isoformat()}",
        "=" * 60,
        "",
        f"Total chunks processed: {total}",
        f"  Success: {status_counts.get('success', 0)}",
        f"  Failed:  {status_counts.get('failed', 0)}",
        f"  Skipped: {status_counts.get('skipped', 0)}",
        "",
        "--- Models Used (Success Only) ---",
    ]
    for model, count in model_counts.most_common():
        report_lines.append(f"  {model}: {count}")

    report_lines.extend(["", "--- System Prompts (Success Only) ---"])
    for sp, count in sp_counts.most_common():
        report_lines.append(f"  {sp}: {count}")

    report_lines.extend(["", "--- Turn Distribution (Success Only) ---"])
    for turns, count in turn_counts.most_common():
        report_lines.append(f"  {turns}-Turn: {count}")

    report_lines.extend(["", "--- Reasons ---"])
    for reason, count in reason_counts.most_common():
        report_lines.append(f"  {reason}: {count}")

    report_text = "\n".join(report_lines)

    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"\n{report_text}")
    print(f"\n[INFO] Report saved to {report_file}")


def main():
    args = parse_args()

    # Determine mode
    is_production = args.production
    batch_size = args.batch_size or BATCH_SIZE

    if is_production:
        # Override TEST_MODE in config
        import config
        config.TEST_MODE = False
        print("[MODE] PRODUCTION - using paid models")
    elif TEST_MODE:
        print("[MODE] TEST - using free models only")

    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # --- STEP 1: Load data ---
    print("\n[STEP 1] Loading gold dataset...")
    all_chunks = load_gold_dataset(GOLD_DATASET_PATH)

    print("[STEP 1] Loading master mapping...")
    mapping = load_master_mapping()

    # --- STEP 2: Order chunks (Phase 1: Merdeka, Phase 2: Legacy) ---
    print("\n[STEP 2] Ordering chunks by priority...")
    ordered_chunks = get_processing_order(all_chunks, {})

    # In test mode, limit to test_chunks
    if not is_production and TEST_MODE:
        ordered_chunks = ordered_chunks[: args.test_chunks]
        print(f"[TEST] Limited to {len(ordered_chunks)} chunks")

    # --- STEP 3: Resume from progress if requested ---
    progress = {"last_chunk_id": -1, "processed_count": 0, "batch_number": 0}
    if args.resume:
        progress = load_progress(PROGRESS_FILE)
        print(f"[RESUME] Resuming from chunk_id={progress['last_chunk_id']}, "
              f"processed={progress['processed_count']}, batch={progress['batch_number']}")

    # --- STEP 4: Create API client ---
    print("\n[STEP 3] Creating API client...")
    client = create_client()

    # --- STEP 5: Process chunks in batches ---
    print(f"\n[STEP 4] Processing {len(ordered_chunks)} chunks in batches of {batch_size}...")
    batch_number = progress["batch_number"]
    processed_count = progress["processed_count"]
    current_batch = []
    last_chunk_id = progress["last_chunk_id"]

    # Track stats
    stats = {"success": 0, "failed": 0, "skipped": 0}

    # Filter out already-processed chunks if resuming
    start_idx = 0
    if args.resume and progress["last_chunk_id"] >= 0:
        for i, chunk in enumerate(ordered_chunks):
            if chunk.get("_chunk_id", -1) == progress["last_chunk_id"]:
                start_idx = i + 1
                break

    chunks_to_process = ordered_chunks[start_idx:]

    with tqdm(total=len(chunks_to_process), desc="Generating SFT", unit="chunk") as pbar:
        for chunk in chunks_to_process:
            chunk_id = chunk.get("_chunk_id", -1)
            last_chunk_id = chunk_id
            meta = extract_metadata(chunk)
            kurikulum = meta.get("kurikulum", "")
            is_merdeka = "merdeka" in kurikulum.lower()

            # Process the chunk
            sft_entry = process_single_chunk(
                chunk=chunk,
                mapping=mapping,
                client=client,
                is_merdeka=is_merdeka,
            )

            if sft_entry:
                current_batch.append(sft_entry)
                stats["success"] += 1
            else:
                stats["failed"] += 1

            processed_count += 1

            # Write batch when full
            if len(current_batch) >= batch_size:
                batch_number += 1
                batch_file = get_batch_filename(OUTPUT_DIR, batch_number)
                write_batch(batch_file, current_batch)
                current_batch = []

                # Save progress
                save_progress(PROGRESS_FILE, last_chunk_id, processed_count, batch_number)

            pbar.update(1)
            pbar.set_postfix(
                ok=stats["success"],
                fail=stats["failed"],
                batch=batch_number,
            )

    # Write remaining entries
    if current_batch:
        batch_number += 1
        batch_file = get_batch_filename(OUTPUT_DIR, batch_number)
        write_batch(batch_file, current_batch)
        save_progress(PROGRESS_FILE, last_chunk_id, processed_count, batch_number)

    # --- STEP 6: Generate report ---
    print("\n[STEP 5] Generating report...")
    generate_report(LOG_FILE, REPORT_FILE)

    print(f"\n{'=' * 40}")
    print(f"DONE! Processed {processed_count} chunks.")
    print(f"  Success: {stats['success']}")
    print(f"  Failed/Skipped: {stats['failed']}")
    print(f"  Batches written: {batch_number}")
    print(f"  Output: {OUTPUT_DIR}/")
    print(f"{'=' * 40}")


if __name__ == "__main__":
    main()
