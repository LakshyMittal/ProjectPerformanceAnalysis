# Student Project Performance Analysis Dashboard

<<<<<<< HEAD
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
=======
A Streamlit-based analytics platform designed to help instructors systematically evaluate and monitor student GitHub projects. The system aggregates repository-level metrics, computes performance scores, and presents actionable insights through an interactive dashboard and downloadable reports.

---

## Overview

This application ingests repository data via a structured CSV input, retrieves live GitHub metrics using asynchronous API calls, and transforms raw activity data into meaningful performance indicators.

It is designed for academic environments where instructors need a **scalable, objective, and data-driven evaluation system**.

---

## Key Features

* **Repository Ingestion**

  * CSV-based input (`team_id`, `repo_url`)
  * Supports batch processing of multiple teams

* **GitHub Data Integration**

  * Asynchronous API calls for improved performance
  * Fetches commits, contributors, language distribution, and activity trends
  * Built-in caching (1 hour) with refresh support

* **Performance Scoring Engine**

  * Weighted scoring model based on commits and code contribution
  * Consistency bonus for sustained activity
  * Automatic classification into performance categories

* **Interactive Dashboard**

  * KPI summaries for quick evaluation
  * Visual insights (activity trends, score distribution)
  * Clean and minimal UI for academic use

* **Data Exploration**

  * Filterable dataset view
  * Export results as CSV

* **Reporting System**

  * Auto-generated one-page PDF report per team
  * Bulk export as ZIP archive

* **Resilient Data Handling**

  * Intelligent fallback mechanisms when GitHub statistics are delayed or unavailable

---

## Project Structure

```id="projstruct"
.
├── app.py                    # Streamlit entry point
├── analytics.py              # Scoring and metric calculations
├── github_connector.py       # GitHub API integration
├── pdf_generator.py          # Report generation
├── utils.py                  # Helper utilities
├── requirements.txt
├── .streamlit/
│   └── config.toml
└── ProjectPerformanceAnalysis/
    └── data/
        └── input_repos.csv   # Input dataset
```

---

## Installation

### 1. Clone the repository

```bash id="clonecmd"
git clone <your-repository-url>
cd <project-folder>
```

### 2. Install dependencies

```bash id="installcmd"
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the root directory:

```id="envfile"
GITHUB_TOKEN=your_github_token_here
```

> Note:
>
> * Public repositories do not require additional scopes
> * Private repositories require `repo` access

---

## Input Format

File location:

```id="inputpath"
ProjectPerformanceAnalysis/data/input_repos.csv
```

Example:

```csv id="csvexample"
>>>>>>> 1ff8e4feb00d77cb94dc4adbab71db172e4ba18e
team_id,repo_url
TR-01,https://github.com/freeCodeCamp/freeCodeCamp
TR-02,https://github.com/kamranahmedse/developer-roadmap
```

<<<<<<< HEAD
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
=======
---

## Running the Application

```bash id="runapp"
streamlit run app.py
```

---

## Scoring Methodology

The performance score is computed using a weighted model:

* **Commit Activity** → 30%
* **Code Contribution (Lines of Code)** → 70%
* **Consistency Bonus** → +10% (if active on ≥ 3 days)

---

## Performance Classification

| Category | Score Range |
| -------- | ----------- |
| On Track | ≥ 70%       |
| Lagging  | 30% – 69%   |
| Inactive | < 30%       |

---

## Fallback Strategy

In cases where GitHub returns incomplete or delayed statistics (e.g., HTTP 202):

The system derives approximate metrics using:

* Contributor commit counts
* Language-based repository size
* Recent commit activity patterns

---

## Report Contents

Each generated PDF report includes:

* Team identification and timestamp
* KPI summary
* Score visualization
* Weekly activity trends
* Derived performance metrics (efficiency, contribution impact)
* Auto-generated evaluation summary

---

## Known Limitations

* GitHub repository statistics may be delayed due to background computation
* Large batch requests may encounter API rate limits
* LOC metrics depend on GitHub’s internal processing availability

---

## License

This project is intended for **academic and educational use only**.

---

## Future Enhancements

* Leaderboard and ranking system
* Comparative analytics across teams
* Real-time refresh controls
* Instructor feedback and annotation system
* Persistent data storage for historical tracking

---
>>>>>>> 1ff8e4feb00d77cb94dc4adbab71db172e4ba18e
