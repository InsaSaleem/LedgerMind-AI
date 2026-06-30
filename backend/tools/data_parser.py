import pandas as pd
import numpy as np

def parse_statement(filepath):
    """
    Parses a CSV or Excel file into a standardized DataFrame.
    Normalizes columns to: ['Date', 'Description', 'Amount', 'Category']
    """
    if filepath.endswith('.csv'):
        df = pd.read_csv(filepath)
    elif filepath.endswith(('.xls', '.xlsx')):
        df = pd.read_excel(filepath)
    else:
        raise ValueError("Unsupported file format for parse_statement")
        
    # Standardize column names (heuristic matching)
    col_mapping = {}
    for col in df.columns:
        c_lower = str(col).lower()
        if 'date' in c_lower:
            col_mapping[col] = 'Date'
        elif 'desc' in c_lower or 'name' in c_lower or 'payee' in c_lower:
            col_mapping[col] = 'Description'
        elif 'amount' in c_lower or 'cost' in c_lower or 'price' in c_lower:
            col_mapping[col] = 'Amount'
        elif 'category' in c_lower or 'type' in c_lower:
            col_mapping[col] = 'Category'
            
    df = df.rename(columns=col_mapping)
    
    # Ensure required columns exist
    required_cols = ['Date', 'Description', 'Amount']
    for c in required_cols:
        if c not in df.columns:
            # If we couldn't map it, raise an error or try to guess by index
            if len(df.columns) >= 3:
                 df = df.iloc[:, :3]
                 df.columns = required_cols
            else:
                 raise ValueError(f"Missing required column: {c}")

    if 'Category' not in df.columns:
        df['Category'] = 'Uncategorized'
        
    # Clean data
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
    
    # Clean Amount (remove currency symbols, commas)
    if df['Amount'].dtype == 'O':
        df['Amount'] = df['Amount'].astype(str).str.replace(r'[\$,]', '', regex=True)
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
    
    # Drop rows with entirely missing crucial data
    df = df.dropna(subset=['Date', 'Amount'])
    
    return df
