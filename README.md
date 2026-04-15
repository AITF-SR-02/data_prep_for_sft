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

We recommend navigating to the `src` directory to run this script safely, as it relies on relative paths and imports in `src/`.

```bash
cd src
```

**Common Examples:**

- **Test Mode** (Uses free models and limits to 10 chunks by default)
  ```bash
  uv run python main.py
  ```
- **Production Mode** (Uses paid top-tier models and processes all chunks)
  ```bash
  uv run python main.py --production
  ```
- **Resume Generation** (Pick up where you left off if it crashes or stops)
  ```bash
  uv run python main.py --resume
  ```
  *(You can combine flags, e.g., `uv run python main.py --production --resume`)*
- **Re-generate 1-Turn to Multi-Turn** (Fix outputs that only yielded 1 turn)
  ```bash
  uv run python main.py --production --multi-turn-only
  ```

**All Available Flags (`src/main.py`):**

| Flag | Description |
|------|-------------|
| `--production` | Run in production mode. Overrides `TEST_MODE` to `False` and utilizes paid models. |
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
