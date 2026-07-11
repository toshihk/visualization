---
title: The Guide For Job Seekers
emoji: 💼
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
---

# The Guide for Job Seekers

A two-page Plotly Dash application for exploring covered tech markets and comparing AI disruption, hiring momentum, workplace signals, and company opportunities.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.preprocess
python -m app.main
```

Open `http://127.0.0.1:8888/explore`.

## Decision journey

- **Explore** (`/explore`): choose a period, country, industry, and role using the covered-market map and demand/disruption charts.
- **Decide** (`/decide`): inherit that exploration state, filter by workplace preferences, inspect the AI Disruption Index, and compare layoff counts across all matching companies.

The session store preserves the journey while moving between pages. “Reset Page 2 filters” preserves the exploration choices; “Clear entire journey” returns to defaults.

## Data contract

- `ai_workforce_transformation.csv` supplies industry/region salary, satisfaction, work-model, and workforce benchmarks.
- `tech_layoffs_hiring_trends_elite_v2.csv` supplies country, company, role, hiring, layoffs, and workplace signals.
- The datasets connect only through aggregates at `year + quarter + normalized industry + region`.
- Company salary and written employee reviews are not inferred. The signal cloud is explicitly a proxy based on categorical workplace indicators.

## Quality checks

```bash
source .venv/bin/activate
pytest -q
```
