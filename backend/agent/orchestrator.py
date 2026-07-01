import google.generativeai as genai
import json
import time
from tools.file_handler import detect_file_type
from tools.pdf_parser import parse_pdf_statement
from tools.data_parser import parse_statement
from tools.image_parser import parse_image_statement
from tools.analyzer import detect_anomalies
from tools.visualizer import generate_chart


def call_gemini_with_retry(model, prompt, max_retries=3):
    """Wrap Gemini calls with exponential-backoff retry on 429 quota errors."""
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            return response
        except Exception as e:
            err_str = str(e)
            if '429' in err_str or 'quota' in err_str.lower() or 'rate' in err_str.lower():
                wait_time = (2 ** attempt) * 10  # 10s, 20s, 40s
                print(f"[Gemini] 429 rate-limit hit. Waiting {wait_time}s (attempt {attempt+1}/{max_retries})...")
                time.sleep(wait_time)
                if attempt == max_retries - 1:
                    raise Exception(
                        "Gemini API rate limit reached. "
                        "Please wait 30–60 seconds and try again. "
                        "(Free tier: 15 requests/minute)"
                    )
            else:
                raise e


class LedgerMindAgent:
    def __init__(self, api_key):
        self.api_key = api_key
        if api_key:
            genai.configure(api_key=api_key)
        # Using a model that supports function calling
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    def process_uploaded_file(self, filepath):
        """
        Autonomous workflow for when a file is uploaded.
        """
        narrations = []

        narrations.append(f"> detect_file_type({filepath.split('/')[-1].split(chr(92))[-1]})")
        file_type = detect_file_type(filepath)

        df = None
        parsing_method = 'standard'
        try:
            if file_type == 'pdf':
                narrations.append("> parse_pdf_statement() — extracting transaction table...")
                df = parse_pdf_statement(filepath)
            elif file_type in ['csv', 'excel']:
                narrations.append(f"> parse_statement() — normalizing {file_type.upper()} data...")
                df = parse_statement(filepath)
            elif file_type == 'image':
                narrations.append("> parse_image_statement() — using Gemini Vision AI...")
                result = parse_image_statement(filepath, self.api_key)
                # image_parser now returns (df, method) tuple
                if isinstance(result, tuple):
                    df, parsing_method = result
                else:
                    df = result
            else:
                narrations.append("> Error: Unsupported file type.")
                return {'error': 'Unsupported file type', 'narration': narrations}
        except Exception as e:
            print(f"Agent Orchestrator Error during parsing: {e}")
            narrations.append(f"> Error parsing file: {e}")
            return {'error': str(e), 'narration': narrations, 'dataframe': None, 'anomalies': []}

        narrations.append(f"> Successfully parsed {len(df)} transactions.")
        narrations.append("> detect_anomalies() — running Z-score analysis...")
        anomalies = detect_anomalies(df)

        if anomalies:
            narrations.append(f"> Flagged {len(anomalies)} spending anomalies.")
        else:
            narrations.append("> No significant anomalies detected.")

        return {
            'dataframe': df,
            'anomalies': anomalies,
            'narration': narrations,
            'parsing_method': parsing_method,
        }

    def chat(self, user_message, state):
        """
        Handles user chat query with retry logic on rate-limit errors.
        """
        narrations = []
        df = state.get('dataframe')

        if df is None:
            return {'text_reply': "Please upload a bank statement first before querying.", 'narrations': narrations}

        # Build a safe text summary of the dataframe (no serialization issues)
        try:
            df_info = f"Columns: {df.columns.tolist()}. Total rows: {len(df)}.\nTop 5 rows:\n{df.head().to_string()}"
        except Exception:
            df_info = "(DataFrame summary unavailable)"

        prompt = f"""
        You are LedgerMind AI, a financial intelligence agent.
        The user has uploaded a financial dataset. {df_info}
        
        User question: "{user_message}"
        
        If the user wants a chart or visualization, output JSON: {{"action": "generate_chart", "type": "trend_line" (or "category_pie", "bar")}}.
        If the user wants a data answer, answer it directly based on the data provided above. Output JSON: {{"action": "answer", "text": "your answer"}}
        """

        try:
            narrations.append("> Querying financial data...")
            response = call_gemini_with_retry(self.model, prompt)

            # Clean response
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:-3].strip()
            elif text.startswith("```"):
                text = text[3:-3].strip()

            result = json.loads(text)

            if result.get('action') == 'generate_chart':
                chart_type = result.get('type', 'bar')
                narrations.append(f"> generate_chart(type='{chart_type}')...")
                chart_base64 = generate_chart(df, chart_type)
                return {
                    'text_reply': f"Here is the {chart_type.replace('_', ' ')} you requested.",
                    'narrations': narrations,
                    'new_chart': chart_base64
                }
            else:
                narrations.append("> Analyzing data to answer the query...")
                return {
                    'text_reply': result.get('text', "I analyzed the data but couldn't form a conclusive answer."),
                    'narrations': narrations
                }
        except Exception as e:
            err_str = str(e)
            print(f"[Agent.chat] Exception: {err_str}")
            if '429' in err_str or 'quota' in err_str.lower() or 'rate limit' in err_str.lower():
                return {
                    'text_reply': "⏳ AI rate limit reached. Free tier allows 15 requests/minute. Please wait 30–60 seconds and try again.",
                    'narrations': ["> Rate limit hit — please retry shortly."]
                }
            return {
                'text_reply': f"Agent error: {err_str}",
                'narrations': ["> Failed to process query due to an error."]
            }
