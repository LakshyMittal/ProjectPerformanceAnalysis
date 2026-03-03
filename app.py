import streamlit as st
import pandas as pd
import plotly.express as px
import asyncio
import httpx
import os
from datetime import datetime
from github_connector import fetch_repo_details
from analytics import calculate_scores

# Page Config
st.set_page_config(
    page_title="Dev Performance Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
    <style>
    div[data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.05); /* Glassmorphism */
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 15px;
        border-radius: 10px;
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Student Project Performance Analysis")
st.markdown("### Real-time Engineering Metrics & Team Health Monitoring")
st.divider()

# Load Repo List
def load_repos():
    if os.path.exists("data/input_repos.csv"):
        df = pd.read_csv("data/input_repos.csv")
        df.columns = df.columns.str.strip() # Remove whitespace from headers
        if 'repo_url' not in df.columns:
            return pd.DataFrame(columns=["repo_url"])
        return df
    return pd.DataFrame(columns=["repo_url"])

repos_df = load_repos()

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    st.info("Data is cached for 1 hour to optimize API usage.")
    st.caption(f"Last System Load: {datetime.now().strftime('%H:%M:%S')}")
    
if st.sidebar.button("Refresh Data"):
    st.cache_data.clear()

# Main Analysis Button
if st.button("🚀 Run Analysis"):
    if repos_df.empty:
        st.warning("No repositories found in data/input_repos.csv")
    else:
        # Define the caching function
        @st.cache_data(ttl=3600, show_spinner=False)
        def get_cached_data(repo_urls):
            async def _fetch_async():
                # Increase timeout for large repos/retries
                async with httpx.AsyncClient(timeout=30.0) as client:
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
                    st.warning(f"⚠️ Could not fetch {err.get('url')}: {err.get('error')}")
            
            if valid_data:
                # 1. Calculate Scores (Business Logic)
                scored_data = calculate_scores(valid_data)
                df_results = pd.DataFrame(scored_data)
                
                # --- STALE CACHE PROTECTION ---
                # Ensure new columns exist even if cache has old data
                if 'gini_coefficient' not in df_results.columns:
                    df_results['gini_coefficient'] = 0.0
                if 'primary_language' not in df_results.columns:
                    df_results['primary_language'] = "Unknown"
                if 'weekly_activity' not in df_results.columns:
                    df_results['weekly_activity'] = [[] for _ in range(len(df_results))]
                
                # 2. Merge with CSV to get Assigned Team IDs (Single Source of Truth)
                if 'team_id' in repos_df.columns:
                    # Normalize URLs for robust merging (strip whitespace/trailing slashes)
                    df_results['url_norm'] = df_results['url'].str.strip().str.rstrip('/')
                    repos_df['url_norm'] = repos_df['repo_url'].str.strip().str.rstrip('/')
                    
                    # Merge
                    final_df = df_results.merge(
                        repos_df[['url_norm', 'team_id']], 
                        on='url_norm', 
                        how='left',
                        suffixes=('_gen', '')
                    )
                    
                    # Fill missing team_ids with generated ones if CSV mapping fails
                    final_df['team_id'] = final_df['team_id'].fillna(final_df['team_id_gen'])
                else:
                    final_df = df_results

                # 3. Data Validation & Cleaning
                final_df.fillna(0, inplace=True) # Handle NaNs
                
                # 4. Deterministic Sorting (Crucial for Chart Stability)
                # Sort by Progress (Desc) then Team ID (Asc) to break ties consistently
                final_df = final_df.sort_values(by=['progress_pct', 'team_id'], ascending=[False, True])
                
                # --- Professional Dashboard Layout ---
                
                tab1, tab2, tab3 = st.tabs(["📈 Executive Dashboard", "🔍 Data Explorer", "⚖️ Methodology"])
                
                with tab1:
                    # 1. Top Metrics Row
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Total Teams", len(final_df))
                    col2.metric("Class Average", f"{final_df['progress_pct'].mean():.1f}%")
                    top_team = final_df.iloc[0]
                    col3.metric("Top Performer", top_team['team_id'], f"{top_team['progress_pct']:.1f}%")
                    col4.metric("Active Repos", len(final_df[final_df['active_days'] > 0]))
                    
                    st.markdown("---")
                    
                    # 2. Charts Row
                    col_chart1, col_chart2 = st.columns(2)
                    
                    with col_chart1:
                        st.subheader("🏆 Leaderboard (Progress %)")
                        # Horizontal bar chart is more professional for names/IDs
                        fig_bar = px.bar(
                            final_df.sort_values('progress_pct', ascending=True), 
                            x='progress_pct', 
                            y='team_id', 
                            orientation='h',
                            color='status',
                            color_discrete_map={"On Track": "#2ecc71", "Lagging": "#f1c40f", "Inactive": "#e74c3c"},
                            text_auto='.1f',
                            title="🏆 Team Performance Ranking"
                        )
                        fig_bar.update_layout(xaxis_title="Score (%)", yaxis_title="Team ID", showlegend=True)
                        st.plotly_chart(fig_bar, use_container_width=True)
                        
                    with col_chart2:
                        st.subheader("🧩 Code Contribution (LOC)")
                        fig_pie = px.pie(
                            final_df, 
                            values='lines_added', 
                            names='team_id', 
                            hole=0.5,
                            title="🧩 Code Contribution Share"
                        )
                        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                        st.plotly_chart(fig_pie, use_container_width=True)
                
                with tab2:
                    st.subheader("📋 Detailed Data View")
                    
                    # Filter by Status
                    status_filter = st.multiselect("Filter by Status", options=final_df['status'].unique(), default=final_df['status'].unique())
                    filtered_df = final_df[final_df['status'].isin(status_filter)]
                    
                    # Format Gini for display (Low Gini = Good Balance)
                    display_df = filtered_df.copy()
                    display_df['team_balance'] = display_df['gini_coefficient'].apply(lambda x: f"{1.0 - x:.2f}") # Invert so 1.0 is good
                    
                    # Process Weekly Activity for Sparkline
                    def get_trend(data):
                        if isinstance(data, list):
                            return [w.get('commits', 0) for w in data]
                        return []
                    display_df['weekly_trend'] = display_df['weekly_activity'].apply(get_trend)

                    st.dataframe(
                        display_df[['team_id', 'primary_language', 'team_balance', 'weekly_trend', 'total_commits', 'lines_added', 'active_days', 'progress_pct', 'status']],
                        column_config={
                            "team_balance": st.column_config.ProgressColumn("Collaboration Score", help="1.0 = Perfect Equality, 0.0 = One person did everything", min_value=0, max_value=1),
                            "weekly_trend": st.column_config.LineChartColumn("Weekly Activity (1 Year)", y_min=0, help="Commit trend over the last year"),
                            "progress_pct": st.column_config.ProgressColumn("Overall Score", format="%.1f%%", min_value=0, max_value=100),
                        },
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    csv = filtered_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Report as CSV",
                        data=csv,
                        file_name=f"project_analysis_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )

                with tab3:
                    st.subheader("⚖️ Grading Methodology")
                    st.markdown("""
                    **1. Base Score Calculation**
                    - **Commits (30%)**: Normalized against the class maximum.
                    - **Lines of Code (70%)**: Normalized against the class maximum.
                    
                    **2. Consistency Bonus**
                    - Teams active for **3+ days** receive a **1.1x multiplier**.
                    
                    **3. Status Thresholds**
                    - 🟢 **On Track**: Score ≥ 70%
                    - 🟡 **Lagging**: Score ≥ 30%
                    - 🔴 **Inactive**: Score < 30%
                    """)
                
            else:
                st.error("No valid data could be fetched.")

else:
    st.info("Click 'Run Analysis' to start.")
    if not repos_df.empty:
        st.write("Loaded Repositories:")
        st.dataframe(repos_df)