from groq import Groq
import base64
import pandas as pd
import json
import re
import os
from PIL import Image

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env
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
    OCR fallback using pytesseract when Groq quota is exceeded.
    Only called at upload time, never on page load.
    """
    if not TESSERACT_AVAILABLE:
        raise Exception(
            "Image OCR unavailable (Tesseract not installed). "
            "Please use CSV or Excel format instead, or try again "
            "when Groq AI quota resets."
        )

    img = Image.open(filepath)
    try:
        text = pytesseract.image_to_string(img)
    except Exception as e:
        if "tesseract is not installed" in str(e).lower() or "not in your path" in str(e).lower():
            raise Exception("⏳ AI quota reached. (OCR fallback is also unavailable because Tesseract is not installed). Please wait 60 seconds and try again.")
        raise e

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
                            'Category': auto_categorize(desc),
                            'Amount': amount
                        })
            except ValueError:
                continue

    if not transactions:
        return pd.DataFrame(columns=['Date', 'Description', 'Category', 'Amount'])

    df = pd.DataFrame(transactions)
    df['Category'] = df['Description'].apply(auto_categorize)
    return df


def parse_image_statement(filepath, api_key=None):
    """
    Uses Groq Vision to parse an image of a receipt or bank statement.
    Falls back to pytesseract OCR if quota is exceeded.

    Args:
        filepath:  path to the image file
        api_key:   the GROQ_API_KEY

    Returns: (pd.DataFrame, parsing_method_str)
    """
    try:
        if not api_key:
            api_key = os.environ.get('GROQ_API_KEY')
            if not api_key:
                raise RuntimeError("No API key provided for image parsing.")

        # Create a new Groq client
        client = Groq(api_key=api_key)

        with open(filepath, 'rb') as f:
            image_data = f.read()

        ext = filepath.split('.')[-1].lower()
        mime = 'image/jpeg' if ext in ['jpg', 'jpeg'] else 'image/png'
        base64_image = base64.b64encode(image_data).decode('utf-8')

        prompt = """Extract ALL financial transactions from this image.
Return ONLY a JSON array with no markdown, no explanation, no thinking:
[{"Date":"2024-01-15","Description":"Office Rent","Category":"Rent","Amount":1500.00}]
If there are no financial transactions, return: []
Return ONLY valid JSON, no other text."""

        response = client.chat.completions.create(
            model='qwen/qwen3.6-27b',
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime};base64,{base64_image}",
                            },
                        },
                    ],
                }
            ]
        )

        text = response.choices[0].message.content.strip()
        print(f"[image_parser] Raw Groq response: {text[:500]}")

        # Strip markdown fences
        text = re.sub(r'```json|```', '', text).strip()
        # Strip <think>...</think> or <thought>...</thought> blocks (even if unclosed)
        text = re.sub(r'<(think|thought)>.*?(?:</\1>|$)', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'</?(think|thought)>', '', text, flags=re.IGNORECASE).strip()

        # Try to extract JSON array from the response
        json_match = re.search(r'\[.*\]', text, re.DOTALL)
        if json_match:
            text = json_match.group(0)

        if not text:
            print("[image_parser] Model returned empty response, falling back to OCR...")
            return parse_image_with_ocr(filepath), 'ocr_fallback'

        # ── Robust JSON parsing with multiple fix attempts ──
        transactions = None

        # Attempt 1: Direct parse
        try:
            transactions = json.loads(text)
        except json.JSONDecodeError:
            pass

        # Attempt 2: Fix common JSON issues
        if transactions is None:
            try:
                fixed = text
                # Fix trailing commas before ] or }
                fixed = re.sub(r',\s*([}\]])', r'\1', fixed)
                # Fix unescaped double quotes inside strings by replacing with single quotes
                # Remove any control characters
                fixed = re.sub(r'[\x00-\x1f\x7f]', ' ', fixed)
                transactions = json.loads(fixed)
            except json.JSONDecodeError:
                pass

        # Attempt 3: Try to extract individual JSON objects
        if transactions is None:
            try:
                objects = re.findall(r'\{[^{}]*\}', text)
                if objects:
                    transactions = []
                    for obj_str in objects:
                        try:
                            obj_str = re.sub(r',\s*}', '}', obj_str)
                            obj = json.loads(obj_str)
                            transactions.append(obj)
                        except json.JSONDecodeError:
                            continue
            except Exception:
                pass

        # Attempt 4: If all JSON parsing fails, fall back to OCR
        if not transactions:
            print("[image_parser] Could not parse JSON from model response, falling back to OCR...")
            return parse_image_with_ocr(filepath), 'ocr_fallback'

        df = pd.DataFrame(transactions)

        # Ensure standard columns exist
        for col in ['Date', 'Description', 'Amount']:
            if col not in df.columns:
                df[col] = 'N/A' if col != 'Amount' else 0.0

        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0.0)
        if 'Category' not in df.columns:
            df['Category'] = 'Uncategorized'

        return df, 'groq_vision'

    except Exception as e:
        err_str = str(e)
        print(f"[image_parser] Groq error: {err_str}")

        # ── Auth / invalid key errors ──
        if any(k in err_str for k in ['401', '403', 'API_KEY_INVALID', 'invalid api key',
                                       'PERMISSION_DENIED', 'API key not valid']):
            raise RuntimeError(
                "Invalid or missing Groq API key. "
                "Please update GROQ_API_KEY in your .env file with a valid key and restart the server."
            )

        # ── Quota / rate-limit errors — try OCR fallback ──
        if '429' in err_str or 'quota' in err_str.lower() or 'rate' in err_str.lower():
            print("[image_parser] Quota exceeded — falling back to OCR...")
            return parse_image_with_ocr(filepath), 'ocr_fallback'

        raise RuntimeError(f"Image parsing failed: {err_str}")
