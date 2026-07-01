import google.generativeai as genai
import pandas as pd
import json
import os
from PIL import Image

def parse_image_statement(filepath):
    """
    Uses Gemini Vision to parse an image of a receipt or bank statement
    and extract transaction data into a standard Pandas DataFrame.
    Returns: pd.DataFrame with columns ['Date', 'Description', 'Amount', 'Category']
    """
    try:
        # We assume genai is already configured in orchestrator.py
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        img = Image.open(filepath)
        
        prompt = """
        You are a highly accurate financial data extraction assistant.
        Analyze this image (which is a receipt or bank statement) and extract all line-item transactions.
        For each transaction, extract the Date, Description (payee or item name), and Amount.
        Return the result strictly as a JSON array of objects. Do not include markdown formatting like ```json.
        Example output format:
        [
            {"Date": "2023-10-15", "Description": "Coffee Shop", "Amount": 4.50},
            {"Date": "2023-10-16", "Description": "Office Supplies", "Amount": 12.99}
        ]
        If a date is missing for a specific line but present at the top of a receipt, apply that date to all lines.
        Make sure Amount is a float (no currency symbols).
        """
        
        response = model.generate_content([prompt, img])
        
        # Clean response string
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:-3]
        elif text.startswith("```"):
            text = text[3:-3]
            
        data = json.loads(text)
        
        if not data:
             raise ValueError("Extracted JSON array is empty.")
             
        df = pd.DataFrame(data)
        
        # Ensure correct columns exist
        for col in ['Date', 'Description', 'Amount']:
            if col not in df.columns:
                df[col] = "N/A" if col != 'Amount' else 0.0
                
        # Ensure Amount is numeric
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0.0)
        
        # Add default category
        df['Category'] = 'Uncategorized'
        
        return df
        
    except Exception as e:
        print(f"Error parsing image with Gemini: {e}")
        raise RuntimeError(f"Image parsing failed: {e}")
