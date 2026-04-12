🚀 Student Project Performance Analysis Dashboard

This is a Streamlit-based dashboard built to help instructors track and evaluate student GitHub projects efficiently.

It takes repository data from a CSV file, fetches live GitHub stats, calculates performance scores, and presents everything in a clean dashboard along with downloadable PDF reports.

🔑 Features
📄 Upload repos using CSV (team_id, repo_url)
⚡ Fast GitHub data fetching (async + cached)
📊 Automatic scoring system for performance
📈 Dashboard with KPIs and visual insights
🔍 Filterable data explorer + CSV export
📑 Auto-generated PDF report per team
📦 Bulk download reports as ZIP
🧠 Smart fallback if GitHub stats are delayed
📁 Project Structure
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
⚙️ Setup
1. Install dependencies
pip install -r requirements.txt
2. Create .env file

Add your GitHub token:

GITHUB_TOKEN=your_github_token_here
Public repos → no special permissions needed
Private repos → repo access required
3. Add repository data

Edit this file:

ProjectPerformanceAnalysis/data/input_repos.csv

Example:

team_id,repo_url
TR-01,https://github.com/freeCodeCamp/freeCodeCamp
TR-02,https://github.com/kamranahmedse/developer-roadmap
▶️ Run the App
streamlit run app.py
📊 Scoring Logic (Simple)
Commits → 30%
Code Contribution (LOC) → 70%
Consistency Bonus → +10% (if active ≥ 3 days)
📌 Status Categories
🟢 On Track → Score ≥ 70%
🟡 Lagging → Score ≥ 30%
🔴 Inactive → Score < 30%
⚠️ Smart Fallback System

If GitHub stats are not ready (common issue):

The system uses:

Contributor commit counts
Language-based code size
Recent activity trends
📑 PDF Reports Include
Team details + date
KPI summary
Score visualization
Weekly activity chart
Key metrics (efficiency, impact, etc.)
Auto-generated summary
🚧 Common Issues
Problem	Reason
Stats show 202	GitHub still processing
LOC is zero	Delay in GitHub stats
Rate limit hit	Too many API calls
📜 License

This project is intended for academic and educational use.

💡 (Optional Improvement)

If you want to upgrade this further later:

Add leaderboard ranking
Add student comparison view
Add real-time refresh button UI
Add instructor comments storage
