import matplotlib.pyplot as plt
import seaborn as sns
import os

def plot_data(df):
    """
    Generates and saves visualizations based on the student data.
    """
    print("\n--- Generating Visualizations ---")
    
    # Ensure output folder exists
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # Set the visual style
    sns.set_theme(style="whitegrid")
    
    # 1. Scatter Plot: Hours Studied vs Exam Score
    # This shows if studying more actually helps.
    plt.figure(figsize=(10, 6))
    sns.scatterplot(data=df, x='Hours_Studied', y='Exam_Score', hue='Gender', alpha=0.6)
    plt.title('Impact of Study Hours on Exam Score')
    plt.xlabel('Hours Studied')
    plt.ylabel('Exam Score')
    plt.savefig(f"{output_dir}/hours_vs_score.png")
    print(f"Saved: {output_dir}/hours_vs_score.png")
    plt.close()
    
    # 2. Bar Chart: Parental Involvement vs Average Score
    # This shows which category of parents has students with higher scores.
    if 'Parental_Involvement' in df.columns:
        plt.figure(figsize=(8, 5))
        # Calculate order based on mean score so the chart looks organized
        order = df.groupby('Parental_Involvement')['Exam_Score'].mean().sort_values(ascending=False).index
        sns.barplot(data=df, x='Parental_Involvement', y='Exam_Score', order=order, palette='viridis', hue='Parental_Involvement')
        plt.title('Average Exam Score by Parental Involvement')
        plt.ylim(0, 100) # Fix y-axis to 0-100 for grades
        plt.savefig(f"{output_dir}/parental_involvement.png")
        print(f"Saved: {output_dir}/parental_involvement.png")
        plt.close()

    # 3. Histogram: Distribution of Exam Scores
    # This shows if most students get high, low, or average scores.
    plt.figure(figsize=(10, 6))
    sns.histplot(df['Exam_Score'], bins=20, kde=True, color='skyblue')
    plt.title('Distribution of Exam Scores')
    plt.xlabel('Score')
    plt.savefig(f"{output_dir}/score_distribution.png")
    print(f"Saved: {output_dir}/score_distribution.png")
    plt.close()
