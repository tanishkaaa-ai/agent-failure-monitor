# Lightweight Real-Time Agent Failure Prediction and Intervention System

A lightweight, real-time framework designed to monitor AI agent execution step-by-step, predict impending failures early using runtime signals and a fast ML classifier, cross-verify critical uncertainty with an LLM Judge, and trigger targeted interventions to recover or gracefully halt execution.

## Project Structure

```text
├── configs/            # Configuration files (hyperparameters, signal thresholds, API settings)
├── data/
│   ├── raw/            # Raw agent execution trajectories, traces, and logs
│   └── processed/      # Extracted features, token stats, and labeled datasets
├── notebooks/          # Jupyter notebooks for exploratory data analysis (EDA) & prototyping
├── src/                # Core modular source code
│   ├── signals/        # Signal extraction (token drift, repetitive loops, tool error rates, latency)
│   ├── models/         # Lightweight ML classifiers (e.g., Logistic Regression, Random Forest, XGBoost)
│   ├── judge/          # LLM-as-a-Judge validation logic and prompt templates
│   ├── interventions/  # Intervention strategies (re-prompting, tool retry, fallback, human-in-the-loop)
│   └── utils/          # Logging, metrics, and helper functions
├── tests/              # Unit and integration tests
├── .gitignore          # Files and folders to exclude from git tracking
├── requirements.txt    # Project dependencies
└── verify_env.py       # Environment verification script
```

## Quickstart

1. **Activate the virtual environment**:
   ```bash
   source venv/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify installation**:
   ```bash
   python verify_env.py
   ```

