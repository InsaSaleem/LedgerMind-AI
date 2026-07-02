import google.generativeai as genai
import pandas as pd
import json
import re
import os
from PIL import Image

# ── OCR availability check (lazy — never fails on import) ──
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except Exception:
    TESSERACT_AVAILABLE = False


def auto_categorize(description):
    """Keyword-based categorizer for OCR-extracted transactions."""
    desc = description.lower()
    if any(w in desc for w in ['rent', 'office', 'warehouse', 'storage']):
        return 'Rent'
    elif any(w in desc for w in ['salary', 'wage', 'payroll', 'staff']):
        return 'Salaries'
    elif any(w in desc for w in ['google', 'facebook', 'instagram', 'ads', 'marketing', 'campaign']):
        return 'Marketing'
    elif any(w in desc for w in ['electric', 'water', 'internet', 'phone', 'utility', 'bill']):
        return 'Utilities'
    elif any(w in desc for w in ['supplier', 'fabric', 'textile', 'wholesale', 'vendor']):
        return 'Suppliers'
    elif any(w in desc for w in ['shopify', 'zoom', 'canva', 'software', 'subscription', 'saas']):
        return 'Software & SaaS'
    elif any(w in desc for w in ['fuel', 'transport', 'courier', 'delivery', 'shipping']):
        return 'Transport'
    elif any(w in desc for w in ['packaging', 'supplies', 'stationery', 'office supply']):
        return 'Supplies'
    elif any(w in desc for w in ['repair', 'maintenance', 'equipment', 'emergency']):
        return 'Maintenance'
    elif any(w in desc for w in ['grocery', 'food', 'lunch', 'meal', 'metro']):
        return 'Food & Groceries'
    else:
        return 'General'


def parse_image_with_ocr(filepath):
    """
    OCR fallback using pytesseract when Gemini quota is exceeded.
    Only called at upload time, never on page load.
    """
    if not TESSERACT_AVAILABLE:
        raise Exception(
            "Image OCR unavailable (Tesseract not installed). "
            "Please use CSV or Excel format instead, or try again "
            "when Gemini AI quota resets."
        )

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
                            'Category': 'General',
                            'Amount': amount
                        })
            except ValueError:
                continue

    if not transactions:
        return pd.DataFrame(columns=['Date', 'Description', 'Category', 'Amount'])

    df = pd.DataFrame(transactions)
    # Apply keyword-based auto-categorization so data looks meaningful
    df['Category'] = df['Description'].apply(auto_categorize)
    return df


def _create_vision_model(api_key):
    """
    Create a dedicated Gemini model instance for vision tasks.
    Uses a separate configure call scoped to this function to avoid
    polluting the global genai configuration used by the orchestrator.
    """
    # Configure genai with the vision-specific key
    genai.configure(api_key=api_key)

    # Try model names in priority order (free-tier compatible)
    _model_names = [
        'gemini-2.0-flash',
        'gemini-1.5-flash-latest',
        'gemini-1.5-flash',
    ]
    for _name in _model_names:
        try:
            model = genai.GenerativeModel(_name)
            return model
        except Exception:
            continue

    raise RuntimeError("No supported Gemini vision model found.")


def parse_image_statement(filepath, api_key=None, restore_key=None):
    """
    Uses Gemini Vision to parse an image of a receipt or bank statement.
    Falls back to pytesseract OCR if quota is exceeded.

    Args:
        filepath:    path to the image file
        api_key:     the GEMINI_VISION_KEY (dedicated image key, or falls back to main key)
        restore_key: the main GEMINI_API_KEY to restore after vision call

    Returns: (pd.DataFrame, parsing_method_str)
    """
    try:
        if not api_key:
            raise RuntimeError("No API key provided for image parsing.")

        model = _create_vision_model(api_key)

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

    finally:
        # Restore the main API key so subsequent orchestrator calls work correctly
        if restore_key:
            genai.configure(api_key=restore_key)
