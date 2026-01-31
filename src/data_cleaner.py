import pandas as pd

def clean_data(df):
    """
    Performs basic data cleaning.
    1. Removes duplicates.
    2. Fills missing values.
    """
    print("\n--- Data Cleaning ---")
    
    # Check for duplicates
    initial_rows = df.shape[0]
    df = df.drop_duplicates()
    final_rows = df.shape[0]
    
    if initial_rows != final_rows:
        print(f"Removed {initial_rows - final_rows} duplicate rows.")
    else:
        print("No duplicate rows found.")

    # Check for missing values
    missing_values = df.isnull().sum().sum()
    if missing_values > 0:
        print(f"Found {missing_values} missing values. Filling with defaults...")
        # Fill numeric columns with the mean
        for col in df.select_dtypes(include=['number']).columns:
            df[col] = df[col].fillna(df[col].mean())
        # Fill text columns with 'Unknown'
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].fillna('Unknown')
        print("Missing values handled.")
    else:
        print("No missing values found.")
        
    return df
