# Sekolah Rakyat - SFT Data Generator

This repository contains the data preparation and Supervised Fine-Tuning (SFT) data generation pipeline for the Sekolah Rakyat project. It contains scripts to pull raw data from Hugging Face, run a pipeline to generate high-quality multi-turn SFT data using various AI models (via OpenRouter), and push the final generated data back to Hugging Face.

## Prerequisites

- [uv](https://github.com/astral-sh/uv) (for dependency management and fast Python execution)
- Python (managed automatically via `uv` according to `.python-version`)
- A Hugging Face account and an Access Token (`HF_TOKEN` or `HUGGINGFACE_HUB_TOKEN`)

## Setup

Create a `.env` file in the root directory to store your Hugging Face token and your OpenRouter API keys (which are used by the underlying `config.py`):

```env
HF_TOKEN=your_huggingface_token
# Add your OpenRouter API keys or other keys required by src/config.py
OPENROUTER_API_KEY=your_key_here
```

Dependencies are managed by `uv` (via `pyproject.toml` and `uv.lock`) and will be installed or utilized automatically when you use `uv run`.

## Pipeline Scripts and Usage

### 1. Generating SFT Data (`src/main.py`)

The main generation script is located in `src/main.py`. It reads the gold dataset, formats prompts, requests model completions, handles multi-turn conversation generation, and saves the outputs in batches.

Run this script from the project root, because the input/output paths in `src/config.py` are relative to the repository root (e.g., `data/...`).

**Common Examples:**

- **Test Mode** (Uses free models and limits to 10 chunks by default)

  ```bash
  uv run python .\src\main.py --test
  ```

- **Production Mode** (Uses paid top-tier models and processes all chunks)

  ```bash
  uv run python .\src\main.py --production
  ```

- **Resume Generation** (Pick up where you left off if it crashes or stops)

  ```bash
  uv run python .\src\main.py --resume
  ```

  *(You can combine flags, e.g., `uv run python .\src\main.py --production --resume`)*

- **Re-generate 1-Turn to Multi-Turn** (Fix outputs that only yielded 1 turn)

  ```bash
  uv run python .\src\main.py --production --multi-turn-only
  ```

**All Available Flags (`src/main.py`):**

| Flag | Description |
| ------ | ----------- |
| `--production` | Run in production mode. Overrides `TEST_MODE` to `False` and utilizes paid models. |
| `--test` | Force test mode (free models only), using `FREE_MODELS`. |
| `--batch-size N` | Overrides the batch size defined in config. Saves data to disk every `N` chunks. |
| `--resume` | Resume the dataset generation from the last saved progress (`last_chunk_id`). |
| `--test-chunks N` | Limit the number of chunks processed in test mode (default is 10). |
| `--multi-turn-only` | Target generation specifically for chunks that only yielded a 1-turn conversation, re-generating them as 2 or 3 turns. |
| `-h`, `--help` | Show the help message and available arguments. |

---

### 2. Pulling Data from Hugging Face (`pull_data_from_hf.py`)

Use this script to download dataset files (like `.json`, `.jsonl`, or `.md`) from the Hugging Face hub (specifically `AITF-SR-02/` repo) into your local `data/` folder.

**From the project root:**

```bash
uv run python pull_data_from_hf.py
```

*Note: This script enforces a "safe mode" on Windows to prevent invalid trailing space/dot directory names that Hugging Face repos might contain.*

---

### 3. Pushing Data to Hugging Face (`push_data_to_hf.py`)

Once you have reviewed and verified your generated SFT data in the `./data` folder, use this script to push the local folder back to the Hugging Face hub.

**From the project root:**

```bash
uv run python push_data_to_hf.py
```

This will upload all files from the `./data` folder to your target Hugging Face repository, updating the final SFT dataset.

## Data Pipeline Workflow (Mermaid)

```mermaid
flowchart TD
  Start([Start]) --> Pull[Optional: Pull / sync datasets<br/>pull_data_from_hf.py]
  Pull --> LocalData[(Local data/<br/>gold + mapping)]

  LocalData --> Run[Run generator<br/>uv run python .\\src\\main.py --test / --production]
  Run --> Mode{Mode?}
  Mode -->|--test or TEST_MODE=true| Free[Force FREE_MODELS<br/>(free-tier only)]
  Mode -->|--production| Paid[Allow MODELS tiers<br/>(paid allowed)]

  Run --> LoadGold[Load gold dataset<br/>data/cpt_dataset/*.jsonl]
  Run --> LoadMap[Load mapping<br/>data/mapping_instruct/*.json]
  LoadGold --> Order[Order chunks<br/>Merdeka → Legacy]
  LoadMap --> Order

  Order --> Loop[Process chunks concurrently]
  Loop --> Meta[Extract metadata + text]
  Meta --> IsMerdeka{Kurikulum Merdeka?}

  IsMerdeka -- Yes --> Match[Matcher 3-layer<br/>exact → fuzzy → bm25]
  IsMerdeka -- No --> NoMatch[Skip matching<br/>placeholder bab/sub-bab]

  Match --> Prompt[Select system prompt + turns]
  NoMatch --> Prompt

  Prompt --> SelectModel[Select model<br/>(Free or Paid)]
  SelectModel --> Build[Build prompts<br/>(system + user)]
  Build --> Call[Call OpenRouter API<br/>(JSON mode)]
  Call --> Valid{Valid JSON schema?}

  Valid -- Yes --> SFT[Build SFT entry<br/>messages + metadata]
  Valid -- No --> Fail[Log failed / skipped]

  SFT --> Batch[Write batch JSONL<br/>data/sft_dataset/sft_batch_###.jsonl]
  SFT --> Log[Append log + progress<br/>generation_log.jsonl + .progress.json]
  Fail --> Log

  Batch --> Report[Generate report<br/>sft_generation_report.txt]
  Report --> Push[Optional: Push results to HF<br/>push_data_to_hf.py]
  Push --> Done([Done])
```
