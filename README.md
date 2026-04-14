# Student Project Performance Analysis Dashboard

Streamlit application for faculty to evaluate student GitHub repositories using consistent metrics, visual dashboards, and downloadable PDF reports.

## Highlights

- Asynchronous GitHub data collection with retry and fallback handling
- Absolute-baseline scoring (not class-relative ranking)
- Executive dashboard with leaderboard and contribution charts
- Data Explorer with filters, sparklines, CSV export, and per-team PDF
- Bulk ZIP report generation on demand
- Built-in safeguards for rate limits and tiny datasets

## Tech Stack

- Python
- Streamlit
- Pandas
- Plotly
- httpx
- ReportLab

## Project Layout

- `app.py` - Streamlit UI and orchestration
- `github_connector.py` - GitHub API integration and fallbacks
- `analytics.py` - Scoring logic
- `pdf_generator.py` - Team PDF and ZIP report generation
- `utils.py` - URL parsing and normalization
- `ProjectPerformanceAnalysis/data/input_repos.csv` - Input repositories

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create `.env` from `.env.example`:
   - `GITHUB_TOKEN` is required
4. Run:
   ```bash
   streamlit run app.py
   ```

## Input CSV Format

`ProjectPerformanceAnalysis/data/input_repos.csv` must contain:

```csv
team_id,repo_url
TR-01,https://github.com/freeCodeCamp/freeCodeCamp
TR-02,https://github.com/kamranahmedse/developer-roadmap
```

## Scoring Methodology

Absolute targets:

- Commits target: `100`
- LOC added target: `5000`
- Active days target: `20`
- Fallback code-bytes target: `250000` (when LOC stats are unavailable)

Weights:

- Commits: `30%`
- LOC/Code bytes: `50%`
- Active days: `20%`

Consistency bonus:

- `1.1x` multiplier when active days >= `3`

Status thresholds:

- On Track: `>= 70%`
- Lagging: `>= 30%`
- Inactive: `< 30%`

## Reliability Notes

- GitHub stats endpoints can return `202 Accepted` while still computing.
- The app applies bounded retries and falls back to contributor/commit endpoints.
- Sidebar warns when loaded repository count is below 3.
- UI warns when API rate limit remaining is low.

## Testing

Run:

```bash
pytest
```

Current tests cover:

- URL parsing and normalization (`utils.py`)
- Absolute scoring behavior and thresholds (`analytics.py`)
