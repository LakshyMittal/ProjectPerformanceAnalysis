<div align="center">

<img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/Streamlit-1.56.0-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white"/>
<img src="https://img.shields.io/badge/GitHub_API-v3-181717?style=for-the-badge&logo=github&logoColor=white"/>
<img src="https://img.shields.io/badge/Tests-pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white"/>
<img src="https://img.shields.io/badge/License-Academic-green?style=for-the-badge"/>

# Student Project Performance Analysis Dashboard

**A real-time GitHub analytics platform for evaluating, monitoring, and reporting student project performance at scale.**

[Features](#-features) · [Setup](#️-setup) · [Scoring](#-scoring-methodology) · [Tech Stack](#-tech-stack)

</div>

---

## Overview

This system provides a **data-driven alternative to subjective project evaluation**. It integrates with the GitHub API to extract repository activity, transforms it into structured metrics, and computes performance scores using a standardized model.

Designed specifically for **academic environments**, it enables instructors to assess multiple teams consistently, efficiently, and objectively.

---

## Features

### GitHub Data Integration

* Asynchronous API requests for parallel data fetching
* Handles `202 Accepted` responses with retry + backoff
* Multi-level fallback system (stats → contributors → commits)
* Built-in caching to reduce API load

### Scoring Engine

* Absolute baseline scoring (independent of class size)
* Weighted evaluation:

  * Commits → 30%
  * LOC → 50%
  * Active Days → 20%
* Consistency multiplier for sustained activity
* Gini coefficient for contribution fairness

### Dashboard & Analytics

* KPI overview (class average, top performer, active teams)
* Team ranking with performance classification
* Activity trend visualization
* Contribution distribution charts

### Reporting

* One-click PDF report generation per team
* Bulk export (ZIP)
* Automated evaluation summaries

---

## Project Structure

```id="projstruct2"
ProjectPerformanceAnalysis/
│
├── app.py
├── analytics.py
├── github_connector.py
├── pdf_generator.py
├── utils.py
│
├── requirements.txt
├── .env.example
│
├── tests/
│   ├── test_analytics.py
│   └── test_utils.py
│
├── .streamlit/
│   └── config.toml
│
└── ProjectPerformanceAnalysis/
    └── data/
        └── input_repos.csv
```

---

## Setup

### 1. Clone repository

```bash id="clone2"
git clone https://github.com/your-username/ProjectPerformanceAnalysis.git
cd ProjectPerformanceAnalysis
```

### 2. Install dependencies

```bash id="install2"
pip install -r requirements.txt
```

### 3. Configure environment

```env id="env2"
GITHUB_TOKEN=your_token_here
```

> Public repos → no scope required
> Private repos → `repo` scope required

### 4. Run application

```bash id="run2"
streamlit run app.py
```

---

## Input Format

```csv id="csv2"
team_id,repo_url
TR-01,https://github.com/org/project-alpha
TR-02,https://github.com/org/project-beta
```

---

## Scoring Methodology

```
Final Score = (Commits × 0.30) + (LOC × 0.50) + (Active Days × 0.20)
            × Consistency Multiplier
```

### Performance Categories

| Category | Score  |
| -------- | ------ |
| On Track | ≥ 70%  |
| Lagging  | 30–69% |
| Inactive | < 30%  |

---

## Tech Stack

| Technology | Purpose         |
| ---------- | --------------- |
| Streamlit  | UI & dashboard  |
| Pandas     | Data processing |
| Plotly     | Visualization   |
| httpx      | Async API calls |
| ReportLab  | PDF generation  |
| pytest     | Testing         |

---

## Limitations

* GitHub stats endpoints may be delayed
* Large datasets may approach rate limits
* LOC depends on GitHub internal computation

---

## Roadmap

* Persistent storage (history tracking)
* Comparative analytics
* Instructor feedback system
* Configurable scoring weights
* Email report delivery

---

## Author

**Lakshy Mittal**
BCA (AI/ML) — Manav Rachna International Institute of Research and Studies

---

## License

Academic and educational use only

---

<div align="center">

Built with Python, Streamlit, and GitHub API

</div>
