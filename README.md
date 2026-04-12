# Student Project Performance Analysis Dashboard

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
team_id,repo_url
TR-01,https://github.com/freeCodeCamp/freeCodeCamp
TR-02,https://github.com/kamranahmedse/developer-roadmap
```

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
