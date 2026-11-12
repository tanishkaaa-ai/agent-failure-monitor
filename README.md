# Lightweight Real-Time Agent Failure Prediction and Intervention System

A production-grade, real-time framework designed to monitor AI agent execution step-by-step, predict impending failures early using runtime signals and a fast ML classifier, cross-verify critical uncertainty with an LLM Judge, and trigger targeted interventions to recover or gracefully halt execution.

## End-to-End Execution Flow

At every execution turn of the agent:
1. **Agent Action**: The agent emits a reasoning thought, action, or tool invocation.
2. **Monitoring Layer**: Records the action and environment observation in the trajectory history.
3. **Signals Engine**: Computes runtime metrics (retries, fail rates, loops, stagnation, task drift) with zero future data leakage.
4. **ML Model**: Evaluates calibrated probability ($p \in [0.0, 1.0]$) of future failure using a trained lightweight classifier.
5. **LLM Judge**: Prompted reasoning component evaluates semantic validity, categorizing anomalies (`TOOL_FAILURE`, `TEMPORARY_TIMEOUT`, `LOOP`, `PLAN_MISMATCH`, `STAGNATION`, `UNKNOWN`).
6. **Decision System**: Rule-based fusion engine combines signals, ML risk, and Judge verdict using configurable priority thresholds.
7. **CONTINUE Decision**: If the decision is `CONTINUE`, the agent proceeds uninterrupted.
8. **ALARM Decision**: If the decision is `ALARM`, the Intervention Layer activates.
9. **Intervention Execution**: Selects and applies a single corrective action (`RETRY_WITH_BACKOFF`, `SWITCH_TOOL`, `BREAK_LOOP_AND_REPLAN`, `REPLAN`, `ESCALATE_TO_HUMAN`, or `TERMINATE`).
10. **Resumption**: Injects corrective feedback into agent context and seamlessly resumes monitoring on the next turn.

---

## Directory Structure

```text
├── configs/
│   └── decision_config.yaml    # Configurable decision fusion thresholds and overrides
├── data/
│   ├── raw/                    # Raw AFTraj-2K parquet datasets and benchmark splits
│   └── processed/              # Step-level features and train/val/test CSV splits
├── examples/                   # Standalone phase demonstration scripts
│   ├── demo_signals_engine.py
│   ├── demo_ml_prediction.py
│   ├── demo_llm_judge.py
│   ├── demo_decision_system.py
│   └── demo_intervention_layer.py
├── models_saved/               # Serialized ML models and metadata
│   ├── logistic_regression.joblib
│   ├── decision_tree.joblib
│   └── model_metadata.json
├── notebooks/                  # Inspection scripts and Jupyter notebooks
├── src/                        # Modular source code
│   ├── signals/                # Runtime Signals Engine & feature extraction
│   ├── models/                 # ML training pipelines & real-time risk predictor
│   ├── judge/                  # Prompted LLM Judge & Pydantic output schemas
│   ├── decision/               # Rule-based decision fusion system
│   ├── interventions/          # Intervention engine, tool registry & recovery actions
│   └── pipeline.py             # AgentFailureGuardSystem unified orchestrator
├── tests/                      # Pytest suite (47 tests across all subsystems)
├── main.py                     # Main CLI entry point
├── requirements.txt            # Python dependencies
└── verify_env.py               # Environment verification script
```

---

## Quickstart & CLI Commands

### 1. Activate Environment
```bash
source venv/bin/activate
```

### 2. Run Demonstrations
- **Live Trajectory Auditing Demo**:
  ```bash
  python main.py --demo
  ```
- **Auditing a Safe Trajectory**:
  ```bash
  python main.py --safe
  ```
- **Batch Evaluation over Test Split**:
  ```bash
  python main.py --eval
  ```
- **Interactive Step-by-Step Simulation**:
  ```bash
  python main.py --interactive
  ```

### 3. Run Test Suite
```bash
pytest tests/
```
*(47 passing unit and integration tests)*
