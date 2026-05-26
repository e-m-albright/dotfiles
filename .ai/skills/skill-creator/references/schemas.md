# JSON Schemas

Data contract for skill evaluation. We don't currently run an eval runner; these schemas are the contract for any future eval system we add. They also document the format if you want to write eval files manually.

Sourced from [anthropics/skills/skill-creator/references/schemas.md@d211d43](https://github.com/anthropics/skills/blob/d211d43/skills/skill-creator/references/schemas.md). Verbatim except for this header.

---

## evals.json

Defines the evals for a skill. Located at `evals/evals.json` within the skill directory.

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "User's example prompt",
      "expected_output": "Description of expected result",
      "files": ["evals/files/sample1.pdf"],
      "expectations": [
        "The output includes X",
        "The skill used script Y"
      ]
    }
  ]
}
```

**Fields:**
- `skill_name`: Name matching the skill's frontmatter
- `evals[].id`: Unique integer identifier
- `evals[].prompt`: The task to execute
- `evals[].expected_output`: Human-readable description of success
- `evals[].files`: Optional list of input file paths (relative to skill root)
- `evals[].expectations`: List of verifiable statements

---

## grading.json

Output from the grader agent. Located at `<run-dir>/grading.json`.

```json
{
  "expectations": [
    {
      "text": "The output includes the name 'John Smith'",
      "passed": true,
      "evidence": "Found in transcript Step 3: 'Extracted names: John Smith, Sarah Johnson'"
    }
  ],
  "summary": {
    "passed": 2,
    "failed": 1,
    "total": 3,
    "pass_rate": 0.67
  },
  "execution_metrics": {
    "tool_calls": {"Read": 5, "Write": 2, "Bash": 8},
    "total_tool_calls": 15,
    "total_steps": 6,
    "errors_encountered": 0,
    "output_chars": 12450,
    "transcript_chars": 3200
  },
  "timing": {
    "executor_duration_seconds": 165.0,
    "grader_duration_seconds": 26.0,
    "total_duration_seconds": 191.0
  }
}
```

**Important:** The viewer (when used) reads field names exactly. The `expectations[]` entries must use `text`, `passed`, `evidence` — not `name`/`met`/`details` variants.

---

## benchmark.json

Output from a benchmark run. Located at `benchmarks/<timestamp>/benchmark.json`.

```json
{
  "metadata": {
    "skill_name": "pdf",
    "skill_path": "/path/to/pdf",
    "timestamp": "2026-01-15T10:30:00Z",
    "evals_run": [1, 2, 3],
    "runs_per_configuration": 3
  },
  "runs": [
    {
      "eval_id": 1,
      "eval_name": "Ocean",
      "configuration": "with_skill",
      "run_number": 1,
      "result": {
        "pass_rate": 0.85,
        "passed": 6,
        "failed": 1,
        "total": 7,
        "time_seconds": 42.5,
        "tokens": 3800,
        "tool_calls": 18,
        "errors": 0
      },
      "expectations": [
        {"text": "...", "passed": true, "evidence": "..."}
      ]
    }
  ],
  "run_summary": {
    "with_skill": {
      "pass_rate": {"mean": 0.85, "stddev": 0.05, "min": 0.80, "max": 0.90}
    },
    "without_skill": {
      "pass_rate": {"mean": 0.35, "stddev": 0.08, "min": 0.28, "max": 0.45}
    },
    "delta": {"pass_rate": "+0.50"}
  }
}
```

**Important:** `configuration` must be exactly `"with_skill"` or `"without_skill"` — viewers/aggregators key off these strings.

---

## history.json (Improve mode)

Tracks version progression when iterating on a skill.

```json
{
  "started_at": "2026-01-15T10:30:00Z",
  "skill_name": "pdf",
  "current_best": "v2",
  "iterations": [
    {"version": "v0", "parent": null, "expectation_pass_rate": 0.65, "is_current_best": false},
    {"version": "v1", "parent": "v0", "expectation_pass_rate": 0.75, "is_current_best": false},
    {"version": "v2", "parent": "v1", "expectation_pass_rate": 0.85, "is_current_best": true}
  ]
}
```

---

## Use of these schemas

Today these schemas only document the format. If/when we add an eval runner:
- A `bin/dotfiles eval-skill <name>` subcommand could read `evals/evals.json` and run each prompt twice (with/without skill) via subagent.
- A grader subagent would produce `grading.json` per run.
- An aggregator would produce `benchmark.json` from multiple runs.

The full Anthropic implementation lives at [anthropics/skills/skill-creator](https://github.com/anthropics/skills/tree/d211d43/skills/skill-creator) — `scripts/run_loop.py`, `scripts/aggregate_benchmark.py`, `agents/grader.md`, `eval-viewer/generate_review.py`. Pull in if/when we want this infrastructure.
