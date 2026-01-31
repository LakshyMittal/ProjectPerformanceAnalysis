
from src.data_loader import load_data
from src.data_cleaner import clean_data
from src.analyzer import perform_analysis
from src.visualizer import plot_data

def main():
    print("--------------------------------------------------")
    print("   Project Performance Analysis System Started")
    print("--------------------------------------------------")

    # Step 1: Load Data
    # We use the relative path to the data folder
    csv_path = "data/student_performance.csv"
    
    df = load_data(csv_path)

    # Step 2: Basic Check
    if df is not None:
        print("\nData Preview (First 6000 rows):")
        print(df.head(6000))
        
        # Step 3: Clean Data
        df = clean_data(df)
        
        # Step 4: Analyze Data
        perform_analysis(df)
        
        # Step 5: Visualize Data
        plot_data(df)
        
        print("\nSystem finished successfully. Check 'output' folder for graphs.")
    else:
        print("System stopped due to data loading error.")

if __name__ == "__main__":
    main()
