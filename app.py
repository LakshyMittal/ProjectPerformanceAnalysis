import streamlit as st
import pandas as pd
import plotly.express as px
import asyncio
import httpx
import os
from github_connector import fetch_repo_details
from analytics import calculate_scores

# Page Config
st.set_page_config(page_title="Dev Performance Dashboard", layout="wide")

st.title("📊 Project Performance Analysis Dashboard")

# Load Repo List
def load_repos():
    if os.path.exists("data/input_repos.csv"):
        return pd.read_csv("data/input_repos.csv")
    return pd.DataFrame(columns=["repo_url"])

repos_df = load_repos()

# Sidebar
st.sidebar.header("Configuration")
if st.sidebar.button("Refresh Data"):
    st.cache_data.clear()

# Main Analysis Button
if st.button("🚀 Run Analysis"):
    if repos_df.empty:
        st.warning("No repositories found in data/input_repos.csv")
    else:
        # Define the caching function
        @st.cache_data(ttl=3600)
        def get_cached_data(repo_urls):
            async def _fetch_async():
                async with httpx.AsyncClient() as client:
                    tasks = [fetch_repo_details(client, url) for url in repo_urls]
                    return await asyncio.gather(*tasks)
            return asyncio.run(_fetch_async())

        with st.spinner("Fetching data from GitHub..."):
            # Fetch data (Cached)
            raw_data = get_cached_data(repos_df['repo_url'].tolist())
            
            # Filter out errors
            valid_data = [d for d in raw_data if "error" not in d]
            errors = [d for d in raw_data if "error" in d]
            
            if errors:
                for err in errors:
                    st.error(f"Error fetching {err.get('url')}: {err.get('error')}")
            
            if valid_data:
                # Calculate Scores
                scored_data = calculate_scores(valid_data)
                df_results = pd.DataFrame(scored_data)
                
                # --- Merge with CSV to get Assigned Team IDs ---
                # This replaces the auto-generated ID with the one from input_repos.csv
                if 'team_id' in repos_df.columns:
                    df_results = df_results.merge(repos_df[['repo_url', 'team_id']], left_on='url', right_on='repo_url', suffixes=('_gen', ''))
                    # The merge keeps the CSV 'team_id' and renames the generated one to 'team_id_gen'
                
                # --- Dashboard Layout ---
                
                # 1. Top Metrics
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Teams", len(df_results))
                col2.metric("Class Average", f"{df_results['progress_pct'].mean():.1f}%")
                top_team = df_results.iloc[0]
                col3.metric("Top Performer", top_team['team_id'], f"{top_team['progress_pct']:.1f}%")
                
                # 2. Charts
                col_chart1, col_chart2 = st.columns(2)
                
                with col_chart1:
                    st.subheader("Progress by Team")
                    fig_bar = px.bar(df_results, x='team_id', y='progress_pct', 
                                     color='team_id', title="Team Progress %")
                    fig_bar.add_hline(y=df_results['progress_pct'].mean(), line_dash="dot", annotation_text="Avg")

                    st.plotly_chart(fig_bar, use_container_width=True)
                    
                with col_chart2:
                    st.subheader("Code Volume Share (LOC)")
                    fig_pie = px.pie(df_results, values='lines_added', names='team_id', 
                                     color='team_id', hole=0.4,
                                     title="Lines of Code Contribution")
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                # 3. Detailed Table
                st.subheader("Detailed Leaderboard")
                # HIDDEN: repo_name (Privacy Requirement)
                st.dataframe(df_results[['team_id', 'total_commits', 'lines_added', 'active_days', 'progress_pct', 'status', 'last_pushed']])
                
                # Export Data
                csv = df_results.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Report as CSV",
                    data=csv,
                    file_name="project_analysis_report.csv",
                    mime="text/csv"
                )
                
            else:
                st.error("No valid data could be fetched.")

else:
    st.info("Click 'Run Analysis' to start.")
    if not repos_df.empty:
        st.write("Loaded Repositories:")
        st.dataframe(repos_df)