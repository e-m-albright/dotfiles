# Python — ML / Data Science

> Curated taste, not mandate — read this to derive per-project choices.
> Extends [the base Python stack](README.md): start with the base Python stack, add ML tools as needed. Install with `uv add` / `uv pip install`.

## Selection (by phase)

```
Phase 1 — CORE ML                  Phase 2 — PRODUCTION
├── PyTorch / JAX                  ├── vLLM (serving)
├── transformers + datasets        ├── ONNX Runtime
├── Weights & Biases               └── FastAPI (APIs)
└── Lightning (training)

Phase 3 — SCALE / RESEARCH
├── DVC (data versioning)
├── Modal / Replicate (cloud GPUs)
└── Custom training loops
```

### Core frameworks

| Category | Pick | Why / when |
|----------|------|------------|
| Deep learning | **PyTorch** | research standard; TensorFlow is declining |
| Alternative | **JAX** | research needing JIT compilation + GPU optimization (Google/DeepMind) |
| High-level training | **Lightning** | clean training loops, built-in logging, multi-GPU; less boilerplate |

### Data & preprocessing

| Category | Pick | Why |
|----------|------|-----|
| DataFrames | **Polars** | 10–100× faster than Pandas |
| Datasets | **Hugging Face datasets** | streaming, caching, standard format |
| Pretrained models | **Hugging Face transformers** | de facto standard |
| Analytics SQL | **DuckDB** | fast analytical queries over training data |

### Experiment tracking

| Category | Pick | Why |
|----------|------|-----|
| Primary | **Weights & Biases** | best UX, broad integrations |
| Self-hosted | **MLflow** | open-source, full control, more setup |
| Alternative | **Aim** | beautiful UI, handles large-scale runs |

### Model serving

| Category | Pick | Why |
|----------|------|-----|
| LLM serving | **vLLM** | fastest OSS LLM serving — PagedAttention, continuous batching |
| General inference | **ONNX Runtime** | optimized cross-platform inference |
| APIs | **FastAPI** | async, type-safe, auto-docs (see frameworks/fastapi.md) |

### Embeddings & RAG

| Category | Pick | When |
|----------|------|------|
| RAG framework | **LLMWare** | default — local/on-device, privacy-first, 300+ models |
| Alternative | **Cognita** | modular, API-driven, production-focused (TrueFoundry) |
| Embeddings API | **JinaAI** | multilingual, 8K context, task-specific adapters |
| Alternative | **Nomic** | when you also want data viz/exploration (Atlas platform) |

### GPU cloud

| Category | Pick | When |
|----------|------|------|
| Serverless GPU | **Modal** | Python-native, excellent DX, auto-scaling |
| Pre-trained models | **Replicate** | run models via API, no infra |
| Enterprise | **Baseten** | self-hosted option, more customization |

### Pipelines & orchestration

| Category | Pick | Why |
|----------|------|-----|
| ML pipelines | **Metaflow** | battle-tested at Netflix; seamless local-to-cloud scaling |
| Alternative | **Prefect** | general workflow orchestration, less ML-specific |

### Data versioning

| Category | Pick | Why |
|----------|------|-----|
| Data versioning | **DVC** | git for data; tracks large files, integrates with remote storage |

### Profiling & debugging

| Tool | Purpose | Usage |
|------|---------|-------|
| **Scalene** | CPU/memory/GPU profiler (recommended) | `scalene --web train.py` |
| **py-spy** | sampling profiler | `py-spy record -o profile.svg -- python train.py` |
| **hyperfine** | benchmarking | `hyperfine 'python v1.py' 'python v2.py'` |

### Notebooks

- **Marimo** — reactive, git-friendly (.py files); preferred for new projects.
- **Jupyter** — broad compatibility; reproducibility issues.

## Idioms

- **PyTorch is the primary framework; JAX only when you need JIT/GPU-optimized research.** Wrap training in **Lightning** to drop boilerplate (training loops, logging, multi-GPU).
- **Polars over Pandas** for any non-trivial data volume.
- **W&B for experiment tracking by default; MLflow when you need self-hosted control.**
- **vLLM for production LLM serving**; it's OpenAI-API-compatible, so clients are just the `openai` SDK pointed at your endpoint.
- **DVC for data versioning** — keep large files out of git, push to remote storage (S3/GCS/Azure).
- **Metaflow lets the same code run locally and on cloud** (`run` vs `run --with batch`).

### Hardware notes

- **Apple Silicon**: PyTorch auto-detects MPS (Metal Performance Shaders) — GPU acceleration works out of the box.
- **CUDA**: requires Linux + NVIDIA GPU; install PyTorch with CUDA support.
- **Memory**: large models need significant RAM — use quantization or smaller models for local dev.

### Local model experimentation

Run models locally via **LM Studio (MLX)** or **llama.cpp** for an OpenAI-compatible endpoint, then point the `openai` SDK or `httpx` at `http://localhost:<port>/v1`.

## Code patterns

### Hugging Face — load model + dataset

```python
from transformers import AutoModel, AutoTokenizer
from datasets import load_dataset

model = AutoModel.from_pretrained("meta-llama/Llama-3.2-3B-Instruct")
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.2-3B-Instruct")
dataset = load_dataset("imdb", split="train")
# huggingface-cli login first for gated models (Llama, etc.)
```

### Weights & Biases — track a run

```python
import wandb

wandb.init(project="my-project", config={"learning_rate": 0.001, "epochs": 10, "batch_size": 32})
for epoch in range(epochs):
    loss = train_epoch()
    wandb.log({"loss": loss, "epoch": epoch})
wandb.finish()
```

### vLLM — serve + client

```bash
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-3.2-3B-Instruct --port 8000
```

```python
from openai import OpenAI  # OpenAI-compatible

client = OpenAI(base_url="http://localhost:8000/v1", api_key="dummy")
response = client.chat.completions.create(
    model="meta-llama/Llama-3.2-3B-Instruct",
    messages=[{"role": "user", "content": "Hello!"}],
)
```

### Modal — serverless GPU function

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

### Metaflow — flow that runs local or on cloud

```python
from metaflow import FlowSpec, step, Parameter


class TrainingFlow(FlowSpec):
    lr = Parameter("lr", default=0.001)

    @step
    def start(self):
        self.data = load_data()
        self.next(self.train)

    @step
    def train(self):
        self.model = train_model(self.data, lr=self.lr)
        self.next(self.end)

    @step
    def end(self):
        save_model(self.model)


if __name__ == "__main__":
    TrainingFlow()
```

```bash
python train_flow.py run               # local
python train_flow.py run --with batch  # AWS Batch, same code
```

### DVC — version a dataset

```bash
uv pip install dvc dvc-s3   # or dvc-gcs, dvc-azure
dvc init
dvc remote add -d storage s3://my-bucket/dvc
dvc add data/train.parquet
git add data/train.parquet.dvc .gitignore
git commit -m "Add training data"
dvc push
```

### Lightning — minimal training module

```python
import lightning as L
import torch


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


trainer = L.Trainer(max_epochs=10, logger=L.loggers.WandbLogger())
trainer.fit(LitModel(), train_dataloader)
```

## See also

- [the base Python stack](README.md) — base Python stack, idioms, performance swaps
- [frameworks/fastapi.md](frameworks/fastapi.md) — serving ML behind an API
- [../../engineering-philosophy.md](../../engineering-philosophy.md) — universal code-health principles
