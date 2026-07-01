import pandas as pd
import pdfplumber
import pytesseract
from pdf2image import convert_from_path
import re
import datetime

def parse_pdf_statement(filepath):
    """
    Parses a PDF bank statement into a structured Pandas DataFrame.
    Returns: pd.DataFrame with columns ['Date', 'Description', 'Amount', 'Category']
    """
    df_list = []
    text_extracted = False
    
    try:
        # First attempt: Try extracting text/tables with pdfplumber (for native PDFs)
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text and len(text.strip()) > 50:
                    text_extracted = True
                    df_list.extend(_parse_text_to_rows(text))
                
                # Also try explicit table extraction
                tables = page.extract_tables()
                if tables:
                    text_extracted = True
                    for table in tables:
                        df_list.extend(_parse_table_to_rows(table))
    except Exception as e:
        print(f"Error with pdfplumber: {e}")
        # We don't raise here yet because we want to try the OCR fallback

    # Fallback to OCR if no meaningful text was extracted (scanned PDF)
    if not text_extracted:
        print("No text found. Falling back to OCR...")
        try:
            images = convert_from_path(filepath)
            for image in images:
                text = pytesseract.image_to_string(image)
                df_list.extend(_parse_text_to_rows(text))
        except Exception as e:
            print(f"OCR failed. Please ensure Tesseract is installed. {e}")
            raise RuntimeError(f"PDF parsing failed: no text could be extracted natively, and OCR failed: {e}")

    if not df_list:
        raise ValueError("Failed to extract any meaningful transaction rows from the PDF.")

    # Deduplicate and clean
    df = pd.DataFrame(df_list, columns=['Date', 'Description', 'Amount'])
    df.drop_duplicates(inplace=True)
    
    # Assign a default category if none exists (a real app would use an LLM or rules engine here)
    df['Category'] = 'Uncategorized'
    
    return df

def _parse_text_to_rows(text):
    """Simple regex based parser for statement lines: Date, Description, Amount"""
    rows = []
    # Basic regex for a line starting with a date, followed by text, ending with a number (possibly negative)
    # E.g. "12/04/2023 Amazon AWS $45.00"
    pattern = re.compile(r'^(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+(.+?)\s+\$?(-?[\d,]+\.\d{2})$', re.MULTILINE)
    
    for match in pattern.finditer(text):
        date_str = match.group(1)
        desc = match.group(2).strip()
        amt_str = match.group(3).replace(',', '')
        
        try:
            # Convert to appropriate types
            date = pd.to_datetime(date_str).strftime('%Y-%m-%d')
            amount = float(amt_str)
            rows.append([date, desc, amount])
        except Exception:
            continue
            
    return rows

def _parse_table_to_rows(table):
    """Parses a structured table from pdfplumber"""
    rows = []
    for row in table:
        if len(row) >= 3:
            # Very heuristic: assume first col is date, second is desc, last is amount
            date_str, desc, amt_str = row[0], row[1], row[-1]
            if date_str and amt_str:
                try:
                    date = pd.to_datetime(date_str).strftime('%Y-%m-%d')
                    amount = float(str(amt_str).replace('$', '').replace(',', '').strip())
                    rows.append([date, str(desc).strip(), amount])
                except Exception:
                    continue
    return rows
