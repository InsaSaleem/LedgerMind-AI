import google.generativeai as genai
import pandas as pd
import json
import re
import os
from PIL import Image


def parse_image_with_ocr(filepath):
    """
    OCR fallback using pytesseract when Gemini quota is exceeded.
    """
    try:
        import pytesseract
    except ImportError:
        raise RuntimeError("pytesseract not installed. Run: pip install pytesseract")

    img = Image.open(filepath)
    text = pytesseract.image_to_string(img)
    transactions = []
    lines = text.split('\n')
    amount_pat = re.compile(r'\$?([\d,]+\.?\d{0,2})')
    date_pat = re.compile(
        r'\d{1,2}[\s/-]\w+[\s/-]\d{2,4}|'
        r'\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}'
    )

    for line in lines:
        line = line.strip()
        if not line or len(line) < 10:
            continue
        amounts = amount_pat.findall(line)
        dates = date_pat.findall(line)
        if amounts and len(line) > 15:
            try:
                amount = float(amounts[-1].replace(',', ''))
                if amount > 0:
                    date = dates[0] if dates else 'Unknown'
                    desc = line
                    for d in dates:
                        desc = desc.replace(d, '')
                    for a in amounts:
                        desc = desc.replace(f'${a}', '').replace(a, '')
                    desc = re.sub(r'\s+', ' ', desc).strip()
                    if desc and len(desc) > 3:
                        transactions.append({
                            'Date': date,
                            'Description': desc[:50],
                            'Category': 'Uncategorized',
                            'Amount': amount
                        })
            except ValueError:
                continue

    if not transactions:
        return pd.DataFrame(columns=['Date', 'Description', 'Category', 'Amount'])
    return pd.DataFrame(transactions)


def parse_image_statement(filepath, api_key=None):
    """
    Uses Gemini Vision to parse an image of a receipt or bank statement.
    Falls back to pytesseract OCR if quota is exceeded.
    Returns: (pd.DataFrame, parsing_method_str)
    """
    try:
        if api_key:
            genai.configure(api_key=api_key)

        # Try model names in priority order (free-tier compatible)
        _model_names = [
            'gemini-2.0-flash',
            'gemini-1.5-flash-latest',
            'gemini-1.5-flash',
        ]
        model = None
        for _name in _model_names:
            try:
                model = genai.GenerativeModel(_name)
                break
            except Exception:
                continue

        if model is None:
            raise RuntimeError("No supported Gemini vision model found.")

        with open(filepath, 'rb') as f:
            image_data = f.read()

        import base64
        encoded = base64.b64encode(image_data).decode()
        ext = filepath.split('.')[-1].lower()
        mime = 'image/jpeg' if ext in ['jpg', 'jpeg'] else 'image/png'

        prompt = """Extract ALL financial transactions from this image.
Return ONLY a JSON array with no markdown:
[{"Date":"2024-01-15","Description":"Office Rent","Category":"Rent","Amount":1500.00}]
Return ONLY valid JSON, no other text."""

        response = model.generate_content([
            {"inline_data": {"mime_type": mime, "data": encoded}},
            prompt
        ])

        text = response.text.strip()
        text = re.sub(r'```json|```', '', text).strip()
        transactions = json.loads(text)
        df = pd.DataFrame(transactions)

        # Ensure standard columns exist
        for col in ['Date', 'Description', 'Amount']:
            if col not in df.columns:
                df[col] = 'N/A' if col != 'Amount' else 0.0

        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0.0)
        if 'Category' not in df.columns:
            df['Category'] = 'Uncategorized'

        return df, 'gemini_vision'

    except Exception as e:
        err_str = str(e)
        print(f"[image_parser] Gemini error: {err_str}")
        if '429' in err_str or 'quota' in err_str.lower() or 'rate' in err_str.lower():
            print("[image_parser] Quota exceeded — falling back to OCR...")
            return parse_image_with_ocr(filepath), 'ocr_fallback'
        raise RuntimeError(f"Image parsing failed: {err_str}")
