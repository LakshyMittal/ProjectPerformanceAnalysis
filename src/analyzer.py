import pandas as pd

def perform_analysis(df):
    """
    Calculates key metrics from the student data.
    """
    print("\n--- Project Analysis ---")
    
    # 1. Basic Statistics
    avg_score = df['Exam_Score'].mean()
    avg_hours = df['Hours_Studied'].mean()
    avg_attendance = df['Attendance'].mean()
    
    print(f"Average Exam Score: {avg_score:.2f}")
    print(f"Average Hours Studied: {avg_hours:.2f} hours/week")
    print(f"Average Attendance: {avg_attendance:.2f}%")
    
    # 2. Correlation Analysis
    # Does studying more actually help?
    if 'Hours_Studied' in df.columns and 'Exam_Score' in df.columns:
        correlation = df['Hours_Studied'].corr(df['Exam_Score'])
        print(f"Correlation (Hours vs Score): {correlation:.2f}")
        if correlation > 0.5:
            print("-> Strong positive relationship: More study = Higher score!")
        elif correlation > 0:
            print("-> Weak positive relationship.")
            
    # 3. Categorical Analysis (e.g., Parental Involvement)
    if 'Parental_Involvement' in df.columns:
        print("\nAverage Score by Parental Involvement:")
        print(df.groupby('Parental_Involvement')['Exam_Score'].mean().sort_values(ascending=False))

    return df
