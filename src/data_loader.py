import pandas as pd
import os

def load_data(filepath):
    """
    Loads the CSV data into a Pandas DataFrame.
    
    Args:
        filepath (str): Path to the CSV file.
        
    Returns:
        pd.DataFrame: The loaded data, or None if an error occurs.
    """
    # Check if file exists first
    if not os.path.exists(filepath):
        print(f"Error: File not found at {filepath}")
        return None
        
    try:
        # Read the CSV file
        df = pd.read_csv(filepath)
        
        # Print success message and stats
        print(f"SUCCESS: Data loaded from {filepath}")
        print(f" - Total Rows: {df.shape[0]}")
        print(f" - Total Columns: {df.shape[1]}")
        return df
        
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return None
