# Distributed Agent Simulation

A simulation framework for evaluating LLM-based multi-agent orchestration architectures from a distributed systems perspective.

Instead of comparing reasoning quality, this project investigates how different orchestration strategies behave under identical workloads. The framework focuses on scalability, coordination overhead, bottlenecks, latency, and failure propagation while keeping the workload and execution environment consistent.

The project was developed for a distributed systems study comparing multiple orchestration architectures using reproducible experiments and structured execution logging.

---

## Features

- Compare four multi-agent orchestration architectures
- Evaluate both parallel and sequential workloads
- Config-driven experiment execution
- Structured JSONL event logging
- Automatic metric extraction and analysis
- Failure injection for crash and straggler experiments
- Reproducible experiments with metadata and Git commit tracking

---

## System Overview

The framework separates an experiment into four independent components.

```text
Configuration
        │
        ▼
Architecture
        │
        ▼
Workload
        │
        ▼
Analysis
```

This separation makes it possible to evaluate different orchestration strategies without changing workload logic or analysis code.

### Supported Architectures

| Architecture | Description |
|--------------|-------------|
| **Monolithic** | Sequential single-worker baseline |
| **Master–Worker** | Central coordinator distributes work to multiple workers |
| **Queue-Based** | Producer–consumer model using task and result queues |
| **Swarm** | Decentralized task handoff through predefined routing |

![Architecture Overview](docs/images/architecture_overview.png)

### Workloads

Two workloads are included to represent different execution characteristics.

| Workload | Characteristics | Primary Purpose |
|----------|-----------------|-----------------|
| **Task A** | Highly parallel document summarization | Scalability and throughput |
| **Task B** | Sequential multi-hop question answering | Coordination and dependency overhead |

### Evaluation Metrics

Experiments collect structured execution logs and derive metrics including:

- Throughput
- P50 / P99 latency
- Queue wait time
- Worker utilization
- Wall-clock execution time
- Failure statistics

---

## Experiment Pipeline

Every experiment follows the same execution flow.

```mermaid
flowchart LR

A[Configuration] --> B[Runner]

B --> C[Architecture]

C --> D[Workload]

D --> E[LLM]

E --> F[JSONL Logs]

F --> G[Parser]

G --> H[Analyzer]

H --> I[Figures & Reports]
```

The framework stores structured event logs instead of only aggregated metrics. As a result, experiments can be analyzed repeatedly without rerunning expensive LLM inference.

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

Copy the example environment file.

```bash
cp .env.example .env
```

At minimum, configure:

```text
GEMINI_API_KEY=YOUR_API_KEY
```

Multiple API keys are also supported.

```text
GEMINI_API_KEY1=...
GEMINI_API_KEY2=...
...
```

The client automatically performs API key rotation and exponential backoff when rate limits occur.

### 3. Configure an experiment

Edit one of the YAML configuration files under `configs/`.

Typical parameters include:

- architecture
- workload
- worker count
- failure mode
- logging options

### 4. Run an experiment

```bash
python runner/run_experiment.py \
    --config configs/example.yaml
```

### 5. Parse experiment logs

```bash
python parser/metrics_parser.py
```

### 6. Analyze results

Use the analysis scripts under `analyzer/` to generate figures and summary statistics from the parsed metrics.