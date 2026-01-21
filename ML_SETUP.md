# ML/DL Development Setup

This guide covers tools and packages recommended for deep learning and ML development, including what teams like Anthropic use in their workflows.

## CLI Tools (via Homebrew)

These are installed via `macos/brew.sh` in the `ai_cli` and `dev_cli` sections:

- **ollama** - Local LLM runtime (already included)
- **claude-code** - Anthropic CLI (already included)
- **gemini-cli** - Google Gemini CLI (already included)
- **huggingface-cli** - Hugging Face CLI for model management (recommended)
- **duckdb** - Fast analytical SQL database (CLI for quick data explorations)
- **hyperfine** - Command-line benchmarking tool (compare script performance)
- **py-spy** - Sampling profiler for Python programs (profile training/inference)

## Python Packages (via `uv`)

These are typically installed per-project, not globally. Use `uv` for fast, reliable package management:

### Core Frameworks

```bash
# PyTorch (most common for research & production)
uv pip install torch torchvision torchaudio

# JAX (used by Google/DeepMind, increasingly popular for research)
uv pip install jax jaxlib

# TensorFlow (if needed for specific projects)
uv pip install tensorflow

# NumPy, SciPy (foundational)
uv pip install numpy scipy
```

### Experiment Tracking & Monitoring

**Considerations (open source, self-hosted alternatives):**

```bash
# MLflow (open source, self-hosted, more bare-bones)
# Great ML lifecycle support: experiment tracking, model registry & deployment
uv pip install mlflow

# Aim (open source, faster than MLflow, beautiful UI)
# Handles large-scale runs well; integrates nicely with existing workflows
uv pip install aim

# Weights & Biases (industry standard, but requires account)
# Used by Anthropic/OpenAI; polished UI but cloud-hosted
# uv pip install wandb

# TensorBoard (PyTorch/TensorFlow visualization)
uv pip install tensorboard
```

### Data & Preprocessing

```bash
# Pandas (data manipulation)
uv pip install pandas

# Polars (faster alternative to pandas)
uv pip install polars

# DuckDB (fast analytical SQL database, great for large datasets)
# CLI already installed via Homebrew; Python bindings:
uv pip install duckdb

# Hugging Face datasets & transformers
uv pip install datasets transformers accelerate

# PyTorch Lightning (high-level PyTorch wrapper)
uv pip install lightning
```

### DuckDB CLI for Quick Data Explorations

DuckDB CLI (already installed via Homebrew) is great for quick data analysis:

```bash
# Quick CSV analysis
duckdb -c "SELECT * FROM read_csv_auto('data.csv') LIMIT 10"

# Query Parquet files directly
duckdb -c "SELECT COUNT(*) FROM 'data.parquet'"

# Interactive mode
duckdb
> .tables
> SELECT * FROM read_csv_auto('data.csv') WHERE column > 100;
```

For Python integration:
```python
import duckdb
conn = duckdb.connect()
conn.execute("SELECT * FROM read_csv_auto('data.csv')")
```

### Model Serving & Inference

```bash
# vLLM (fast LLM serving, used by many production teams)
uv pip install vllm

# FastAPI (for model APIs)
uv pip install fastapi uvicorn

# ONNX Runtime (optimized inference)
uv pip install onnxruntime
```

### Development Tools

```bash
# Jupyter (installed via `uv tool install jupyter` in install.sh)
# For compatibility with traditional notebooks
# Already configured in install.sh

# Marimo (already installed globally, reactive notebooks)
# Already configured in install.sh

# DVC (data version control)
uv pip install dvc

# Pre-commit hooks for ML projects
uv pip install pre-commit
```

### Performance & Profiling Tools

```bash
# py-spy (already installed via Homebrew)
# Profile running Python processes without modifying code
py-spy record -o profile.svg -- python train.py

# hyperfine (already installed via Homebrew)
# Benchmark different commands/scripts
hyperfine 'python script_v1.py' 'python script_v2.py'
```

## VS Code / Cursor Extensions

Recommended extensions for ML development (add to `editors/extensions.sh`):

- **Python** - Already included (`ms-python.python`)
- **Ruff** - Already included (`charliermarsh.ruff`)
- **Jupyter** - For notebook support (`ms-toolsai.jupyter`)
- **TensorBoard** - TensorBoard integration (`ms-toolsai.vscode-tensorboard`)

## Workflow Recommendations

### Project Structure

```bash
# Create a new ML project
mkdir my-ml-project && cd my-ml-project
uv venv
source .venv/bin/activate  # or use uv run
uv pip install torch wandb transformers
```

### Experiment Tracking (Weights & Biases)

```python
import wandb

wandb.init(project="my-project", config={"learning_rate": 0.001})
# Your training code...
wandb.log({"loss": loss, "accuracy": acc})
```

### Local Model Development (Ollama)

```bash
# Pull models
ollama pull llama3.2
ollama pull mistral
ollama pull codellama

# Run inference
ollama run llama3.2 "Explain transformers"
```

### Hugging Face Workflow

```bash
# Login to Hugging Face
huggingface-cli login

# Download models
huggingface-cli download meta-llama/Llama-3.2-3B-Instruct

# Or use in Python
from transformers import AutoModel, AutoTokenizer
model = AutoModel.from_pretrained("meta-llama/Llama-3.2-3B-Instruct")
```

## Containers: OrbStack vs Docker Desktop

**OrbStack** (recommended for macOS) is installed via Homebrew as a Docker Desktop alternative:

- **Faster startup** (~2 seconds vs Docker Desktop's slower boot)
- **Lower resource usage** (CPU + memory footprint)
- **Better macOS integration** (VirtioFS for file mounts, Rosetta emulation for x86 images)
- **Drop-in replacement** (Docker CLI & Compose compatible)
- **Trade-offs**: Newer, fewer edge-case integrations; commercial licensing for organizations

If you're on macOS (especially Apple Silicon), OrbStack is highly recommended over Docker Desktop.

## What Teams Like Anthropic Use

Based on industry practices:

1. **PyTorch** - Primary framework for model development
2. **JAX** - For research requiring JIT compilation and GPU optimization
3. **Experiment Tracking** - MLflow or Aim (self-hosted) or Weights & Biases (cloud)
4. **Hugging Face** - Model hub and transformers library
5. **vLLM** - For serving LLMs in production
6. **DuckDB** - Fast analytical queries on large datasets
7. **Custom tooling** - Often build internal tools on top of these

## Quick Start: PyTorch Project

```bash
# Create project
mkdir pytorch-project && cd pytorch-project
uv venv
source .venv/bin/activate

# Install core packages
uv pip install torch torchvision wandb

# Create a simple training script
cat > train.py << 'EOF'
import torch
import wandb

wandb.init(project="pytorch-quickstart")
# Your training code here
EOF

# Run
python train.py
```

## Notes

- **GPU Support**: PyTorch will auto-detect MPS (Metal Performance Shaders) on Apple Silicon. For CUDA, you'll need a Linux machine with NVIDIA GPUs.
- **Memory**: Large models may require significant RAM. Consider using quantization or smaller models for local development.
- **Project-specific**: Most ML packages should be installed per-project using `uv`, not globally, to avoid conflicts.
