# ML/Deep Learning Setup

**Philosophy**: Production-ready ML tooling that integrates with the Python stack.

> **Note**: This extends the Python STACK.md. Start with the base Python setup, add ML tools as needed.

---

## Installation Phases

```
Phase 1 - CORE ML                       Phase 2 - PRODUCTION
├── PyTorch / JAX                       ├── vLLM (serving)
├── transformers + datasets             ├── ONNX Runtime
├── Weights & Biases                    └── FastAPI (APIs)
└── Lightning (high-level training)

Phase 3 - SCALE / RESEARCH
├── DVC (data versioning)
├── Modal / Replicate (cloud GPUs)
└── Custom training loops
```

---

## Core Frameworks

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Deep Learning** | PyTorch | TensorFlow is declining. PyTorch is the research standard. |
| **Alternative** | JAX | For research requiring JIT compilation, GPU optimization. Used by Google/DeepMind. |
| **High-Level** | Lightning | Reduces boilerplate. Clean training loops, built-in logging, multi-GPU. |

### Installation

```bash
# PyTorch (auto-detects MPS on Apple Silicon, CUDA on Linux)
uv pip install torch torchvision torchaudio

# JAX (if needed)
uv pip install jax jaxlib

# Lightning (recommended wrapper)
uv pip install lightning
```

---

## Data & Preprocessing

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **DataFrames** | Polars | Pandas is slow. Polars is 10-100x faster. |
| **Datasets** | Hugging Face datasets | Streaming, caching, standard format. |
| **Transformers** | Hugging Face transformers | De facto standard for pretrained models. |

### Hugging Face Setup

```bash
# Install core packages
uv pip install datasets transformers accelerate

# Login for gated models (Llama, etc.)
huggingface-cli login
```

```python
from transformers import AutoModel, AutoTokenizer
from datasets import load_dataset

# Load model
model = AutoModel.from_pretrained("meta-llama/Llama-3.2-3B-Instruct")
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.2-3B-Instruct")

# Load dataset
dataset = load_dataset("imdb", split="train")
```

---

## Experiment Tracking

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **Primary** | Weights & Biases | Best UX, great integrations, used by Anthropic/OpenAI. |
| **Self-Hosted** | MLflow | Open-source, self-hosted. More setup but full control. |
| **Alternative** | Aim | Beautiful UI, handles large-scale runs well. |

### Weights & Biases

```bash
uv pip install wandb
wandb login
```

```python
import wandb

wandb.init(
    project="my-project",
    config={
        "learning_rate": 0.001,
        "epochs": 10,
        "batch_size": 32,
    }
)

# Training loop
for epoch in range(epochs):
    loss = train_epoch()
    wandb.log({"loss": loss, "epoch": epoch})

wandb.finish()
```

### Self-Hosted Alternative (MLflow)

```bash
uv pip install mlflow
mlflow server --backend-store-uri sqlite:///mlflow.db
```

---

## Model Serving

| Category | Choice | Why Not Alternatives |
|----------|--------|---------------------|
| **LLM Serving** | vLLM | Fastest open-source LLM serving. PagedAttention, continuous batching. |
| **General Inference** | ONNX Runtime | Optimized cross-platform inference. |
| **APIs** | FastAPI | Async, type-safe, auto-docs. (Already in Python stack) |

### vLLM Setup

```bash
uv pip install vllm

# Serve a model
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-3.2-3B-Instruct \
    --port 8000
```

```python
# Client usage (OpenAI-compatible)
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="dummy")
response = client.chat.completions.create(
    model="meta-llama/Llama-3.2-3B-Instruct",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

---

## Local Development (Ollama)

For local model experimentation without cloud costs:

```bash
# Already installed via Homebrew
ollama serve

# Pull models
ollama pull llama3.2
ollama pull mistral
ollama pull codellama

# Run inference
ollama run llama3.2 "Explain transformers"
```

```python
# Python client
import httpx

response = httpx.post(
    "http://localhost:11434/api/generate",
    json={"model": "llama3.2", "prompt": "Hello!"}
)
```

---

## GPU Cloud Options

| Category | Choice | When to Use |
|----------|--------|-------------|
| **Serverless GPU** | Modal | Python-native, excellent DX, auto-scaling. |
| **Pre-trained Models** | Replicate | Run models via API. No infra management. |
| **Enterprise** | Baseten | Self-hosted option, more customization. |

### Modal Example

```python
import modal

app = modal.App("my-ml-service")
image = modal.Image.debian_slim().pip_install("torch", "transformers")

@app.function(gpu="A10G", image=image)
def run_inference(prompt: str) -> str:
    from transformers import pipeline
    pipe = pipeline("text-generation", model="gpt2")
    return pipe(prompt)[0]["generated_text"]
```

---

## Data Versioning

| Category | Choice | Notes |
|----------|--------|-------|
| **Data Versioning** | DVC | Git for data. Tracks large files, integrates with remote storage. |

### DVC Setup

```bash
uv pip install dvc dvc-s3  # or dvc-gcs, dvc-azure

dvc init
dvc remote add -d storage s3://my-bucket/dvc

# Track data
dvc add data/train.parquet
git add data/train.parquet.dvc .gitignore
git commit -m "Add training data"
dvc push
```

---

## Profiling & Debugging

| Tool | Purpose | Usage |
|------|---------|-------|
| **py-spy** | Sampling profiler | `py-spy record -o profile.svg -- python train.py` |
| **Scalene** | CPU/Memory/GPU profiler | `scalene train.py` |
| **hyperfine** | Benchmarking | `hyperfine 'python v1.py' 'python v2.py'` |

### Scalene (Recommended)

```bash
uv pip install scalene
scalene --web train.py  # Opens browser with profile
```

---

## Notebooks

| Category | Choice | Why |
|----------|--------|-----|
| **Primary** | Marimo | Reactive, git-friendly (.py files), reproducible. |
| **Fallback** | Jupyter | Industry standard, broad compatibility. |

Both are installed via the base Python setup.

```bash
# Marimo (preferred)
marimo edit notebook.py

# Jupyter (fallback)
jupyter lab
```

---

## Quick Start: Training Pipeline

```bash
# Create project
mkdir ml-project && cd ml-project
uv init
uv add torch lightning wandb transformers datasets

# Create training script
cat > train.py << 'EOF'
import lightning as L
import torch
import wandb
from torch.utils.data import DataLoader

class LitModel(L.LightningModule):
    def __init__(self):
        super().__init__()
        self.model = torch.nn.Linear(10, 1)

    def training_step(self, batch, batch_idx):
        x, y = batch
        loss = torch.nn.functional.mse_loss(self.model(x), y)
        self.log("train_loss", loss)
        return loss

    def configure_optimizers(self):
        return torch.optim.Adam(self.parameters(), lr=0.001)

if __name__ == "__main__":
    wandb.init(project="my-project")
    trainer = L.Trainer(max_epochs=10, logger=L.loggers.WandbLogger())
    trainer.fit(LitModel(), train_dataloader)
EOF

# Run
uv run python train.py
```

---

## Hardware Notes

- **Apple Silicon**: PyTorch auto-detects MPS (Metal Performance Shaders). GPU acceleration works out of the box.
- **CUDA**: Requires Linux with NVIDIA GPU. Install PyTorch with CUDA support.
- **Memory**: Large models need significant RAM. Use quantization or smaller models for local dev.

---

## What Teams Use

Based on industry practices:

1. **PyTorch** — Primary framework for model development
2. **JAX** — For research requiring JIT compilation and GPU optimization
3. **Weights & Biases** — Experiment tracking (or MLflow for self-hosted)
4. **Hugging Face** — Model hub and transformers library
5. **vLLM** — Serving LLMs in production
6. **DuckDB** — Fast analytical queries on training data
7. **Modal** — Serverless GPU compute for training/inference
