import streamlit as st
import pandas as pd
import plotly.express as px
import asyncio
import json
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
    "team_slug": "team",
    "repo_name": "Unknown",
    "last_pushed": "N/A",
    "primary_language": "Unknown",
    "url": "",
    "status": "Inactive",
    "score_loc_source": "LOC added",
}


def _as_list(value):
    return value if isinstance(value, list) else []


def sanitize_filename(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in str(value))
    return safe.strip("_") or "team"


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
        df_results[col] = pd.to_numeric(df_results[col], errors="coerce")

    for col, default in TEXT_DEFAULTS.items():
        if col not in df_results.columns:
            df_results[col] = default

    df_results = df_results.fillna({**NUMERIC_DEFAULTS, **TEXT_DEFAULTS})

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
if 0 < len(repos_df) < 3:
    st.sidebar.warning("Only a few repositories are loaded (<3). Scores may be statistically unstable.")
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
        concurrency = min(12, max(4, len(repo_urls) // 5 or 4))
        sem = asyncio.Semaphore(concurrency)
        async def _fetch_with_sem(url, client):
            async with sem:
                return await fetch_repo_details(client, url)
        async with httpx.AsyncClient(timeout=90.0) as client:
            tasks = [_fetch_with_sem(url, client) for url in repo_urls]
            return await asyncio.gather(*tasks)
    return asyncio.run(_fetch_async())


@st.cache_data(ttl=3600, show_spinner=False)
def get_pdf_bytes(team_payload_json: str) -> bytes:
    return generate_team_pdf(json.loads(team_payload_json))


@st.cache_data(ttl=3600, show_spinner=False)
def get_zip_bytes(rows_json: str) -> bytes:
    return generate_all_pdfs_zip(json.loads(rows_json))

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

            rate_values = [v for v in final_df.get("rate_limit_remaining", pd.Series(dtype=float)).tolist() if pd.notna(v)]
            if rate_values and min(rate_values) < 120:
                st.warning(
                    f"GitHub rate limit is getting low (minimum remaining: {int(min(rate_values))}). "
                    "Use fewer repositories or wait for reset."
                )

            warning_rows = final_df[final_df["stats_warnings"].apply(bool)]
            if not warning_rows.empty:
                with st.expander("GitHub stats warnings"):
                    for row in warning_rows.itertuples(index=False):
                        st.write(f"**{row.team_id}**")
                        for warning in row.stats_warnings:
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
                    rows_json = json.dumps(report_rows, sort_keys=True, default=str)
                    if st.button("Prepare ZIP Report", key="prepare_zip_report", width="stretch"):
                        st.session_state["zip_rows_json"] = rows_json
                    if st.session_state.get("zip_rows_json") == rows_json:
                        zip_bytes = get_zip_bytes(rows_json)
                        st.download_button(
                            label="Download All Reports as ZIP",
                            data=zip_bytes,
                            file_name=f"all_team_reports_{datetime.now().strftime('%Y%m%d')}.zip",
                            mime="application/zip",
                            width="stretch",
                        )
                    else:
                        st.caption("Click Prepare ZIP Report to generate the archive on demand.")
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
                        label="Download Report as CSV",
                        data=csv,
                        file_name=f"project_analysis_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )

                    st.markdown("---")
                    st.subheader("Team PDF Reports")
                    page_size = 10
                    total_rows = len(display_df)
                    total_pages = max(1, (total_rows + page_size - 1) // page_size)
                    selected_page = st.number_input(
                        "PDF Page",
                        min_value=1,
                        max_value=total_pages,
                        value=1,
                        step=1,
                        key="pdf_page",
                    )
                    start_idx = (selected_page - 1) * page_size
                    end_idx = min(start_idx + page_size, total_rows)
                    page_df = display_df.iloc[start_idx:end_idx]

                    header_cols = st.columns([2, 2, 2, 2])
                    header_cols[0].write("Team")
                    header_cols[1].write("Status")
                    header_cols[2].write("Score")
                    header_cols[3].write("PDF")

                    for index, row in enumerate(page_df.itertuples(index=False), start=start_idx):
                        row_cols = st.columns([2, 2, 2, 2])
                        row_cols[0].write(str(getattr(row, "team_id", "")))
                        row_cols[1].write(str(getattr(row, "status", "")))
                        row_cols[2].write(f"{float(getattr(row, 'progress_pct', 0)):.1f}%")
                        row_key = f"{index}_{getattr(row, 'team_id', 'team')}"
                        prepare_key = f"prepare_pdf_{row_key}"
                        state_key = f"ready_pdf_{row_key}"
                        if row_cols[3].button("Prepare", key=prepare_key):
                            st.session_state[state_key] = True
                        if st.session_state.get(state_key):
                            team_payload_json = json.dumps(row._asdict(), sort_keys=True, default=str)
                            pdf_bytes = get_pdf_bytes(team_payload_json)
                            row_cols[3].download_button(
                                label="Download",
                                data=pdf_bytes,
                                file_name=f"{sanitize_filename(getattr(row, 'team_id', 'team'))}_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                                mime="application/pdf",
                                key=f"pdf_{row_key}",
                            )

            # -- TAB 3: Methodology --
            with tab3:
                st.markdown("""
                **1. Base Score Calculation**
                - Commits (30%): Normalized against an absolute baseline target.
                - Lines of Code (50%): Normalized against an absolute baseline target.
                - Active Days (20%): Normalized against an absolute baseline target.

                **2. Consistency Bonus**
                - Teams active for 3+ days receive a 1.1x multiplier.

                **3. Status Thresholds**
                - 🟢 On Track: Score ≥ 70%
                - 🟡 Lagging: Score ≥ 30%
                - 🔴 Inactive: Score < 30%

                **Important note**
                - Scoring uses absolute baselines (not class-relative ranking) to keep grading stable between cohorts.
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
