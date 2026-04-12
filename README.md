Hey, totally—here’s a complete README you can copy‑paste as‑is.

```markdown
# Student Project Performance Analysis Dashboard

A Streamlit dashboard for instructors to monitor and grade student GitHub projects. It reads team repositories from a CSV, pulls live GitHub metrics, calculates performance scores, and generates visual dashboards and PDF reports.

---

## Features
- CSV‑driven repo input (`team_id`, `repo_url`)
- Async GitHub API fetch (repo info, contributors, commit activity, languages)
- Caching for 1 hour with manual refresh
- Scoring + status classification (On Track / Lagging / Inactive)
- Executive dashboard with KPI cards + charts
- Data explorer with filters + CSV export
- One‑page PDF report per team + bulk ZIP download
- Smart fallbacks when GitHub stats are still computing

---

## Project Structure
```
.
├── app.py
├── analytics.py
├── github_connector.py
├── pdf_generator.py
├── utils.py
├── requirements.txt
├── .streamlit/
│   └── config.toml
└── ProjectPerformanceAnalysis/
    └── data/
        └── input_repos.csv
```

---

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Create `.env`
Create a `.env` file in the project root:
```
GITHUB_TOKEN=your_github_token_here
```

> For public repos, no special scopes are required.  
> For private repos, you need `repo` scope.

### 3. Add repo list
Edit the CSV file:
`ProjectPerformanceAnalysis/data/input_repos.csv`

Example:
```
team_id,repo_url
TR-01,https://github.com/freeCodeCamp/freeCodeCamp
TR-02,https://github.com/kamranahmedse/developer-roadmap
```

---

## Run the App
```bash
streamlit run app.py
```

---

## How Scoring Works (Summary)

- **Commits (30%)**: normalized against class max  
- **LOC Added (70%)**: normalized against class max  
- **Consistency Bonus**: +10% if active days ≥ 3  
- **Status**
  - On Track: score ≥ 70%
  - Lagging: score ≥ 30%
  - Inactive: score < 30%

If GitHub’s stats are still computing, the system falls back to:
- commit counts from contributors
- code size from language bytes
- recent commits for activity trend

---

## PDF Reports
Each PDF includes:
- Title + Team + Date
- KPI summary row
- Donut score + weekly activity chart
- Metrics table (net impact, efficiency ratio, gini, bus factor)
- Summary paragraph + instructor notes

---

## Common Issues
- **Stats returning 202**: GitHub still computing; retry or use fallback data.
- **Zeros for LOC**: usually GitHub stats delay, not a bug.
- **Rate limits**: reduce repo count or wait before retry.

---

## License
For academic and educational use.
```

If you want the README customized (branding, screenshots, badges), tell me and I’ll refine it.
