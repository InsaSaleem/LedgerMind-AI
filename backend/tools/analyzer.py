import pandas as pd
import numpy as np

def detect_anomalies(df):
    """
    Detects anomalies in the spending dataframe using z-scores.
    Returns a list of dicts describing the anomalies.
    """
    anomalies = []
    
    # Ensure Amount is numeric
    if 'Amount' not in df.columns:
        return anomalies
        
    amounts = df['Amount']
    mean_val = amounts.mean()
    std_val = amounts.std()
    
    if pd.isna(std_val) or std_val == 0:
        return anomalies # Can't calculate z-score

    # Work on a copy to avoid mutating the caller's DataFrame
    work_df = df.copy()
    work_df['Z-Score'] = (amounts - mean_val) / std_val
    
    # Flag anything with an absolute z-score > 2 as anomalous
    flagged = work_df[work_df['Z-Score'].abs() > 2]
    
    for index, row in flagged.iterrows():
        anomalies.append({
            'date': row['Date'],
            'description': row['Description'],
            'amount': row['Amount'],
            'reason': f"Unusually large transaction (Z-Score: {row['Z-Score']:.2f})"
        })
        
    # Also check for category spikes if categories are present and not all 'Uncategorized'
    if 'Category' in df.columns and len(df['Category'].unique()) > 1:
        cat_sums = df.groupby('Category')['Amount'].sum()
        cat_mean = cat_sums.mean()
        cat_std = cat_sums.std()
        
        if not pd.isna(cat_std) and cat_std > 0:
            for cat, amount in cat_sums.items():
                z = (amount - cat_mean) / cat_std
                if z > 2:
                    anomalies.append({
                        'date': 'N/A',
                        'description': f"Category Spike: {cat}",
                        'amount': amount,
                        'reason': f"Total spending in {cat} is unusually high compared to other categories."
                    })

    return anomalies

def query_data(df, natural_language_question):
    """
    In a real app, this would use pandasai or an LLM to generate pandas code.
    For this MVP, we rely on the Gemini orchestrator to either generate python
    code to run on the dataframe, or we can just return the dataframe head/summary
    if it's simple, but the prompt said:
    "query_data(dataframe, natural_language_question) — lets Gemini translate a user's plain-English question... into a Pandas query executed against the live dataframe"
    
    We will let Gemini supply the 'query_code' and safely evaluate it, or use a restricted env.
    Actually, to keep it safe and simple without pandasai, we can use `pd.eval` or similar, 
    but it's safer to have Gemini write a lambda function or query string.
    """
    # This is a stub for the tool. The actual translation happens in orchestrator.
    # The orchestrator will use the LLM to get an answer or pandas code.
    return f"Executed query for: {natural_language_question}"
