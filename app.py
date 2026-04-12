import streamlit as st
import pandas as pd
import plotly.express as px
import asyncio
import httpx
from datetime import datetime
from pathlib import Path

from github_connector import fetch_repo_details
from analytics import calculate_scores
from pdf_generator import generate_team_pdf, generate_all_pdfs_zip
from utils import normalize_repo_url

st.set_page_config(
    page_title="Student Project Performance Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for glassmorphism
st.markdown("""
<style>
div[data-testid="stMetric"] {
    background-color: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    padding: 15px;
    border-radius: 8px;
    backdrop-filter: blur(10px);
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}
</style>
""", unsafe_allow_html=True)

PROJECT_ROOT = Path(__file__).resolve().parent
INPUT_CSV_CANDIDATES = [
    PROJECT_ROOT / "data" / "input_repos.csv",
    PROJECT_ROOT / "ProjectPerformanceAnalysis" / "data" / "input_repos.csv",
]

NUMERIC_DEFAULTS = {
    "total_commits": 0,
    "lines_added": 0,
    "lines_deleted": 0,
    "active_days": 0,
    "gini_coefficient": 0.0,
    "normalized_commits": 0.0,
    "normalized_loc": 0.0,
    "final_score": 0.0,
    "progress_pct": 0.0,
    "code_bytes": 0,
    "score_loc_value": 0,
}
TEXT_DEFAULTS = {
    "team_id": "Unknown",
    "repo_name": "Unknown",
    "last_pushed": "N/A",
    "primary_language": "Unknown",
    "url": "",
    "status": "Inactive",
    "score_loc_source": "LOC added",
}


def _as_list(value):
    return value if isinstance(value, list) else []


def load_repos() -> tuple[pd.DataFrame, Path | None]:
    csv_path = next((path for path in INPUT_CSV_CANDIDATES if path.exists()), None)
    if csv_path is None:
        return pd.DataFrame(columns=["team_id", "repo_url"]), None

    try:
        df = pd.read_csv(csv_path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=["team_id", "repo_url"]), csv_path

    df.columns = df.columns.str.strip()
    if "repo_url" not in df.columns:
        return pd.DataFrame(columns=["team_id", "repo_url"]), csv_path

    df["repo_url"] = df["repo_url"].astype(str).map(normalize_repo_url)
    df = df[df["repo_url"].ne("")].copy()

    if "team_id" in df.columns:
        df["team_id"] = df["team_id"].astype(str).str.strip()

    df["url_norm"] = df["repo_url"].map(normalize_repo_url)
    return df, csv_path


def prepare_results_frame(scored_data: list[dict], repos_df: pd.DataFrame) -> pd.DataFrame:
    df_results = pd.DataFrame(scored_data)

    for col, default in NUMERIC_DEFAULTS.items():
        if col not in df_results.columns:
            df_results[col] = default
        df_results[col] = pd.to_numeric(df_results[col], errors="coerce").fillna(default)

    for col, default in TEXT_DEFAULTS.items():
        if col not in df_results.columns:
            df_results[col] = default
        df_results[col] = df_results[col].fillna(default)

    for col in ["weekly_activity", "stats_warnings"]:
        if col not in df_results.columns:
            df_results[col] = [[] for _ in range(len(df_results))]
        df_results[col] = df_results[col].apply(_as_list)

    if "language_bytes" not in df_results.columns:
        df_results["language_bytes"] = [{} for _ in range(len(df_results))]

    df_results["url_norm"] = df_results["url"].map(normalize_repo_url)

    if "team_id" in repos_df.columns and not repos_df.empty:
        repo_lookup = repos_df[["url_norm", "team_id"]].drop_duplicates("url_norm")
        final_df = df_results.merge(
            repo_lookup,
            on="url_norm",
            how="left",
            suffixes=("_generated", ""),
        )
        if "team_id_generated" in final_df.columns:
            final_df["team_id"] = final_df["team_id"].fillna(final_df["team_id_generated"])
            final_df.drop(columns=["team_id_generated"], inplace=True)
    else:
        final_df = df_results

    final_df["team_id"] = final_df["team_id"].replace("", "Unknown").fillna("Unknown")
    final_df = final_df.sort_values(
        by=["progress_pct", "team_id"],
        ascending=[False, True],
        kind="mergesort",
    )
    return final_df.reset_index(drop=True)


def build_weekly_trend(data):
    if isinstance(data, list):
        return [int(w.get("commits", 0)) for w in data if isinstance(w, dict)]
    return []


def render_contribution_chart(final_df: pd.DataFrame) -> None:
    chart_options = [
        ("lines_added", "🧩 Code Contribution Share", "LOC added"),
        ("code_bytes", "🧩 Repository Code Size Share", "language bytes"),
        ("total_commits", "🧩 Commit Contribution Share", "commits"),
    ]

    for column, title, label in chart_options:
        if column in final_df.columns and final_df[column].sum() > 0:
            fig_pie = px.pie(final_df, values=column, names="team_id", hole=0.5, title=title)
            fig_pie.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig_pie, width="stretch")
            if column != "lines_added":
                st.caption(
                    f"GitHub LOC additions were unavailable, so this chart is using {label} as a fallback."
                )
            return

    st.info("No contribution data available for the pie chart yet.")

repos_df, loaded_csv_path = load_repos()

# --- Sidebar ---
st.sidebar.header("⚙️ Configuration")
st.sidebar.info("Data is cached for 1 hour to optimize API usage.")
st.sidebar.caption(f"Last System Load: {datetime.now().strftime('%H:%M:%S')}")
if loaded_csv_path:
    st.sidebar.caption(f"Input CSV: {loaded_csv_path.relative_to(PROJECT_ROOT)}")
if st.sidebar.button("Refresh Data", width="stretch"):
    st.cache_data.clear()
    st.sidebar.success("Cache cleared. Run the analysis again.")

# --- Main App Body ---
st.title("📊 Student Project Performance Analysis")
st.markdown("### Real-time Engineering Metrics & Team Health Monitoring")
st.divider()

@st.cache_data(ttl=3600, show_spinner=False)
def get_cached_data(repo_urls: tuple[str, ...]) -> list[dict]:
    async def _fetch_async():
        sem = asyncio.Semaphore(2)  # Prevent hitting GitHub secondary rate limits
        async def _fetch_with_sem(url, client):
            async with sem:
                return await fetch_repo_details(client, url)
        async with httpx.AsyncClient(timeout=90.0) as client:
            tasks = [_fetch_with_sem(url, client) for url in repo_urls]
            return await asyncio.gather(*tasks)
    return asyncio.run(_fetch_async())

if st.button("🚀 Run Analysis", type="primary", width="stretch"):
    if repos_df.empty or "repo_url" not in repos_df.columns:
        st.error("No valid repository data found in `data/input_repos.csv`.")
    else:
        repo_urls = tuple(repos_df["repo_url"].map(normalize_repo_url).tolist())
        with st.spinner("Fetching data from GitHub..."):
            raw_data = get_cached_data(repo_urls)

        # Error Handling
        valid_data = [d for d in raw_data if "error" not in d]
        errors = [d for d in raw_data if "error" in d]
        for err in errors:
            st.warning(f"⚠️ Could not fetch {err.get('url')}: {err.get('error')}")

        if not valid_data:
            st.error("No repositories could be analyzed. Check your GitHub token, CSV URLs, and rate limits.")
            st.stop()

        if valid_data:
            # Analytics and Data Assembly
            scored_data = calculate_scores(valid_data)
            final_df = prepare_results_frame(scored_data, repos_df)
            report_rows = final_df.drop(columns=["url_norm"], errors="ignore").to_dict("records")

            warning_rows = final_df[final_df["stats_warnings"].apply(bool)]
            if not warning_rows.empty:
                with st.expander("GitHub stats warnings"):
                    for _, row in warning_rows.iterrows():
                        st.write(f"**{row['team_id']}**")
                        for warning in row["stats_warnings"]:
                            st.caption(warning)

            # --- TABS LAYOUT ---
            tab1, tab2, tab3 = st.tabs(["📈 Executive Dashboard", "🔍 Data Explorer", "⚖️ Methodology"])

            # -- TAB 1: Dashboard --
            with tab1:
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total Teams", len(final_df))
                m2.metric("Class Average", f"{final_df['progress_pct'].mean():.1f}%")
                
                top_team = final_df.iloc[0] if not final_df.empty else None
                m3.metric("Top Performer", top_team['team_id'] if top_team is not None else "N/A", f"{top_team['progress_pct']:.1f}%" if top_team is not None else "")
                m4.metric("Active Repos", len(final_df[final_df['active_days'] > 0]))

                # Bulk PDF Download
                st.markdown("---")
                col_dl1, col_dl2, col_dl3 = st.columns([1, 2, 1])
                with col_dl2:
                    zip_bytes = generate_all_pdfs_zip(report_rows)
                    st.download_button(
                        label="📦 Download All Reports as ZIP",
                        data=zip_bytes,
                        file_name=f"all_team_reports_{datetime.now().strftime('%Y%m%d')}.zip",
                        mime="application/zip",
                        width="stretch",
                    )
                st.markdown("---")

                c1, c2 = st.columns(2)
                with c1:
                    fig_bar = px.bar(
                        final_df.sort_values(by=['progress_pct', 'team_id'], ascending=[True, False]), 
                        x='progress_pct', y='team_id', orientation='h',
                        color='status', text_auto='.1f',
                        color_discrete_map={"On Track": "#2ecc71", "Lagging": "#f1c40f", "Inactive": "#e74c3c"},
                        title="🏆 Team Performance Ranking"
                    )
                    fig_bar.update_layout(xaxis_title="Score (%)", yaxis_title="Team")
                    st.plotly_chart(fig_bar, width="stretch")

                with c2:
                    render_contribution_chart(final_df)

            # -- TAB 2: Data Explorer --
            with tab2:
                selected_statuses = st.multiselect(
                    "Filter by Status:",
                    options=["On Track", "Lagging", "Inactive"],
                    default=["On Track", "Lagging", "Inactive"]
                )
                display_df = final_df[final_df['status'].isin(selected_statuses)].copy()

                if display_df.empty:
                    st.info("No teams match the selected filters.")
                else:
                    display_df['team_balance'] = display_df['gini_coefficient'].apply(
                        lambda x: max(0.0, min(1.0, 1.0 - float(x)))
                    )
                    display_df['weekly_trend'] = display_df['weekly_activity'].apply(build_weekly_trend)

                    display_cols = [
                        'team_id', 'repo_name', 'primary_language', 'team_balance', 'weekly_trend',
                        'total_commits', 'lines_added', 'lines_deleted', 'code_bytes', 'score_loc_source',
                        'active_days', 'last_pushed',
                        'progress_pct', 'status'
                    ]

                    st.dataframe(
                        display_df[display_cols],
                        column_config={
                            "team_balance": st.column_config.ProgressColumn(
                                "Collaboration Score",
                                help="1.0 = perfect equality",
                                min_value=0.0,
                                max_value=1.0,
                                format="%.2f",
                            ),
                            "weekly_trend": st.column_config.LineChartColumn(
                                "Weekly Activity (1 Year)", y_min=0, help="Commit trend over the last year"
                            ),
                            "progress_pct": st.column_config.ProgressColumn(
                                "Overall Score", format="%.1f%%", min_value=0, max_value=100
                            ),
                            "lines_added": st.column_config.NumberColumn("LOC Added", format="%d"),
                            "lines_deleted": st.column_config.NumberColumn("LOC Deleted", format="%d"),
                            "code_bytes": st.column_config.NumberColumn("Code Bytes", format="%d"),
                            "total_commits": st.column_config.NumberColumn("Commits", format="%d"),
                            "active_days": st.column_config.NumberColumn("Active Days", format="%d"),
                        },
                        width="stretch",
                        hide_index=True
                    )

                    csv = display_df.drop(columns=["url_norm"], errors="ignore").to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Report as CSV",
                        data=csv,
                        file_name=f"project_analysis_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )

                    # Individual Team PDF Generator
                    st.markdown("---")
                    st.subheader("📄 Download Individual Team Report")
                    selected_team_id = st.selectbox("Select a team to generate their PDF report:", options=final_df['team_id'].tolist(), index=0)
                    selected_row = final_df[final_df['team_id'] == selected_team_id].iloc[0]
                    team_dict = selected_row.to_dict()
                    pdf_bytes = generate_team_pdf(team_dict)
                    st.download_button(
                        label=f"⬇️ Download {selected_team_id} Report PDF",
                        data=pdf_bytes,
                        file_name=f"{selected_team_id}_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                    )

            # -- TAB 3: Methodology --
            with tab3:
                st.markdown("""
                **1. Base Score Calculation**
                - Commits (30%): Normalized against the class maximum.
                - Lines of Code (70%): Normalized against the class maximum.

                **2. Consistency Bonus**
                - Teams active for 3+ days receive a 1.1x multiplier.

                **3. Status Thresholds**
                - 🟢 On Track: Score ≥ 70%
                - 🟡 Lagging: Score ≥ 30%
                - 🔴 Inactive: Score < 30%

                **Important note**
                - Commit and LOC metrics come from GitHub statistics endpoints. GitHub can return `202 Accepted`
                  while it computes those statistics, so the connector retries and then shows a warning if the
                  data is still unavailable.
                - If every repository returns zero LOC additions because GitHub stats are unavailable, the dashboard
                  uses GitHub language bytes as a code-size fallback for the normalized LOC portion of the score.
                """)
else:
    st.info("Click 'Run Analysis' to start.")
    if loaded_csv_path:
        st.caption(f"Loaded repository file: `{loaded_csv_path.relative_to(PROJECT_ROOT)}`")
    if not repos_df.empty:
        st.write("Loaded Repositories:")
        st.dataframe(repos_df.drop(columns=["url_norm"], errors="ignore"), width="stretch")
