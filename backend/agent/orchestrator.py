import google.generativeai as genai
import json
import time
from tools.file_handler import detect_file_type
from tools.pdf_parser import parse_pdf_statement
from tools.data_parser import parse_statement
from tools.image_parser import parse_image_statement
from tools.analyzer import detect_anomalies
from tools.visualizer import generate_chart
from tools.task_generator import generate_financial_tasks


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


def _build_df_summary(df, anomalies):
    """
    Build a compact summary dict instead of sending raw DataFrame JSON.
    This dramatically reduces token count per Gemini request.
    """
    if df is None or df.empty:
        return {}

    summary = {
        'total_transactions': len(df),
        'total_spend': float(df['Amount'].sum()) if 'Amount' in df.columns else 0,
        'anomalies': anomalies or [],
    }

    if 'Category' in df.columns and 'Amount' in df.columns:
        summary['categories'] = {
            str(k): round(float(v), 2)
            for k, v in df.groupby('Category')['Amount'].sum().items()
        }

    if 'Date' in df.columns:
        try:
            summary['date_range'] = f"{df['Date'].min()} to {df['Date'].max()}"
        except Exception:
            pass

    return summary


class LedgerMindAgent:
    def __init__(self, api_key, vision_api_key=None, tasks_api_key=None):
        self.api_key = api_key
        self.vision_api_key = vision_api_key or api_key
        self.tasks_api_key = tasks_api_key or api_key

        # Cache: keyed by filepath → (df, anomalies, parsing_method)
        self._file_cache = {}

        if api_key:
            genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    def process_uploaded_file(self, filepath):
        """
        Autonomous workflow for when a file is uploaded.
        Uses a single Gemini API call per unique file (cached after first parse).
        """
        narrations = []

        # ── Cache hit: skip re-parsing & re-calling Gemini ──
        if filepath in self._file_cache:
            narrations.append("> [Cache] File already processed — skipping re-upload.")
            df, anomalies, parsing_method = self._file_cache[filepath]
            return {
                'dataframe': df,
                'anomalies': anomalies,
                'narration': narrations,
                'parsing_method': parsing_method,
            }

        # ── Detect file type ──
        filename_short = filepath.replace('\\', '/').split('/')[-1]
        narrations.append(f"> detect_file_type({filename_short})")
        file_type = detect_file_type(filepath)

        df = None
        parsing_method = 'standard'

        # ── Parse the file (NO Gemini call yet for structured formats) ──
        try:
            if file_type == 'pdf':
                narrations.append("> parse_pdf_statement() — extracting transaction table...")
                df = parse_pdf_statement(filepath)
            elif file_type in ['csv', 'excel']:
                narrations.append(f"> parse_statement() — normalizing {file_type.upper()} data...")
                df = parse_statement(filepath)
            elif file_type == 'image':
                narrations.append("> parse_image_statement() — using Gemini Vision AI...")
                result = parse_image_statement(
                    filepath,
                    self.vision_api_key,
                    restore_key=self.api_key
                )
                if isinstance(result, tuple):
                    df, parsing_method = result
                else:
                    df = result
                # Add 2s cooldown after vision call to avoid burst limits
                time.sleep(2)
            else:
                narrations.append("> Error: Unsupported file type.")
                return {'error': 'Unsupported file type', 'narration': narrations}
        except Exception as e:
            print(f"Agent Orchestrator Error during parsing: {e}")
            narrations.append(f"> Error parsing file: {e}")
            return {'error': str(e), 'narration': narrations, 'dataframe': None, 'anomalies': []}

        # ── Guard against empty parse ──
        if df is None or df.empty:
            narrations.append("> Warning: No transaction data could be extracted.")
            return {
                'error': 'No transaction data could be extracted from the file.',
                'narration': narrations,
                'dataframe': None,
                'anomalies': [],
            }

        narrations.append(f"> Successfully parsed {len(df)} transactions.")

        # ── Anomaly detection (local — no API call) ──
        narrations.append("> detect_anomalies() — running Z-score analysis...")
        anomalies = detect_anomalies(df)

        if anomalies:
            narrations.append(f"> Flagged {len(anomalies)} spending anomalies.")
        else:
            narrations.append("> No significant anomalies detected.")

        # ── Single combined Gemini call for summary narration ──
        # Only for non-image files (image already used one Gemini call via Vision).
        # For image files we skip this to stay within rate limits.
        if file_type != 'image' and self.api_key:
            try:
                narrations.append("> Generating AI summary (1 API call)...")
                summary = _build_df_summary(df, anomalies)
                combined_prompt = f"""You are a financial analyst. Here is the transaction summary: {json.dumps(summary)}

In ONE concise response, confirm:
1. How many transactions were parsed
2. Any anomalies detected (unusually large amounts)
3. Top spending category

Be concise, 2-3 sentences max."""
                resp = call_gemini_with_retry(self.model, combined_prompt)
                narrations.append(f"> AI: {resp.text.strip()[:200]}")
                # 2-second cooldown after this call
                time.sleep(2)
            except Exception as e:
                print(f"[Orchestrator] Summary Gemini call failed: {e}")
                narrations.append("> AI summary skipped (quota/error).")

        result = {
            'dataframe': df,
            'anomalies': anomalies,
            'narration': narrations,
            'parsing_method': parsing_method,
        }

        # ── Cache result ──
        self._file_cache[filepath] = (df, anomalies, parsing_method)

        return result

    def chat(self, user_message, state):
        """
        Handles user chat query with retry logic on rate-limit errors.
        Sends only a compact summary (not full raw DataFrame) to minimize tokens.
        """
        narrations = []
        df = state.get('dataframe')

        if df is None:
            return {'text_reply': "Please upload a bank statement first before querying.", 'narrations': narrations}

        # Build compact summary instead of full dataframe JSON
        anomalies = state.get('anomalies', [])
        df_summary = _build_df_summary(df, anomalies)

        prompt = f"""You are LedgerMind AI, a financial intelligence agent.
The user has uploaded a financial dataset. Here is the data summary:
{json.dumps(df_summary, indent=2)}

User question: "{user_message}"

If the user wants a chart or visualization, output JSON: {{"action": "generate_chart", "type": "trend_line" (or "category_pie", "bar")}}.
If the user wants a data answer, answer it directly based on the summary above. Output JSON: {{"action": "answer", "text": "your answer"}}"""

        try:
            narrations.append("> Querying financial data...")

            if self.api_key:
                genai.configure(api_key=self.api_key)

            response = call_gemini_with_retry(self.model, prompt)

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

    def generate_tasks(self, state):
        """
        Generates AI-powered financial tasks using the dedicated tasks API key.
        """
        df = state.get('dataframe')
        anomalies = state.get('anomalies', [])

        if df is None:
            return {
                'tasks': [{
                    'title': 'Upload a financial statement',
                    'description': 'Upload a bank statement to get AI-powered financial tasks.',
                    'priority': 'low',
                    'category': 'plan',
                    'completed': False,
                }],
                'error': None,
            }

        try:
            tasks = generate_financial_tasks(df, anomalies, self.tasks_api_key)

            if self.api_key:
                genai.configure(api_key=self.api_key)

            return {'tasks': tasks, 'error': None}
        except Exception as e:
            err_str = str(e)
            print(f"[Agent.generate_tasks] Exception: {err_str}")

            if self.api_key:
                genai.configure(api_key=self.api_key)

            return {
                'tasks': generate_financial_tasks(df, anomalies, None),
                'error': err_str,
            }
