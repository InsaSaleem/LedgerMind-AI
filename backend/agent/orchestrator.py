from groq import Groq
import json
import time
import re


def _strip_think_tags(text):
    """Remove <think>...</think> or <thought>...</thought> blocks, even if unclosed."""
    if not text:
        return ""
    # Remove closed or unclosed <think> or <thought> blocks
    text = re.sub(r'<(think|thought)>.*?(?:</\1>|$)', '', text, flags=re.DOTALL | re.IGNORECASE)
    # Double check for any residual tags
    text = re.sub(r'</?(think|thought)>', '', text, flags=re.IGNORECASE)
    return text.strip()
from tools.file_handler import detect_file_type
from tools.pdf_parser import parse_pdf_statement
from tools.data_parser import parse_statement
from tools.image_parser import parse_image_statement
from tools.analyzer import detect_anomalies
from tools.visualizer import generate_chart
from tools.task_generator import generate_financial_tasks

class GroqResponse:
    def __init__(self, text):
        self.text = text

def call_groq_with_retry(client, model_name, prompt, max_retries=3):
    """Wrap Groq calls with exponential-backoff retry on 429 quota errors."""
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = response.choices[0].message.content
            return GroqResponse(_strip_think_tags(raw))
        except Exception as e:
            err_str = str(e)
            if '429' in err_str or 'quota' in err_str.lower() or 'rate' in err_str.lower():
                wait_time = (2 ** attempt) * 10  # 10s, 20s, 40s
                print(f"[Groq] 429 rate-limit hit. Waiting {wait_time}s (attempt {attempt+1}/{max_retries})...")
                time.sleep(wait_time)
                if attempt == max_retries - 1:
                    raise Exception(
                        "Groq API rate limit reached. "
                        "Please wait 30–60 seconds and try again."
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
    def __init__(self, api_key):
        self.api_key = api_key
        self.model_name = 'qwen/qwen3.6-27b'

        # Cache: keyed by filepath → (df, anomalies, parsing_method)
        self._file_cache = {}

        # Create the new SDK client
        if api_key:
            self.client = Groq(api_key=api_key)
        else:
            self.client = None

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
                narrations.append("> parse_image_statement() — using Groq Vision AI...")
                result = parse_image_statement(
                    filepath,
                    self.api_key,
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

        # ── Single combined Groq call for summary narration ──
        # Only for non-image files (image already used one Groq call via Vision).
        if file_type != 'image' and self.client:
            try:
                narrations.append("> Generating AI summary (1 API call)...")
                summary = _build_df_summary(df, anomalies)
                combined_prompt = f"""You are a financial analyst. Here is the transaction summary: {json.dumps(summary)}

In ONE concise response, confirm:
1. How many transactions were parsed
2. Any anomalies detected (unusually large amounts)
3. Top spending category

Be concise, 2-3 sentences max."""
                resp = call_groq_with_retry(self.client, self.model_name, combined_prompt)
                narrations.append(f"> AI: {resp.text.strip()[:200]}")
                time.sleep(2)
            except Exception as e:
                print(f"[Orchestrator] Summary Groq call failed: {e}")
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

        # Build compact summary instead of full dataframe JSON
        anomalies = state.get('anomalies', [])
        df_summary = _build_df_summary(df, anomalies) if df is not None else None

        if df_summary:
            data_context = f"Here is the data summary:\n{json.dumps(df_summary, indent=2)}"
        else:
            data_context = "No file has been uploaded yet. Please ask the user to upload a bank statement or financial file."

        prompt = f"""You are LedgerMind AI, an intelligent, friendly financial intelligence agent.
{data_context}

User message: "{user_message}"

Guidelines:
1. You MUST match the user's language. If the user speaks in English, reply in English. If the user speaks in Urdu/Hindi (including Roman Urdu/Hindi, e.g. "hi, kaise ho?"), reply in the same language/script (e.g. Roman Urdu/Hindi or Urdu script as appropriate).
2. If the user greets you (e.g. "hi", "hello", "salam", "kaise ho"), greet them back warmly and explain what you can do (e.g. analyze bank statements, check anomalies, generate graphs).
3. If no file is uploaded yet, remind the user politely (in their language) to upload a bank statement/file using the drag-and-drop area so you can analyze it, but still respond to their greeting or general queries.
4. If the user wants a chart or visualization, output JSON: {{"action": "generate_chart", "type": "trend_line" (or "category_pie", "bar")}}. Note: Charts can only be generated if a file is already uploaded. If no file is uploaded, inform the user they must upload a file first.
5. If the user wants a text answer, answer it directly in the user's language based on the guidelines. Do NOT include <think> tags. Output JSON: {{"action": "answer", "text": "your response here"}}"""

        try:
            narrations.append("> Querying financial data...")

            if not self.client:
                raise Exception("No API client initialized.")

            response = call_groq_with_retry(self.client, self.model_name, prompt)

            text = _strip_think_tags(response.text)

            # Try to extract JSON using regex if standard stripping fails
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                text = match.group(0)

            try:
                result = json.loads(text)
            except json.JSONDecodeError:
                # Fallback if it's not valid JSON at all
                narrations.append("> Analyzing data to answer the query...")
                return {
                    'text_reply': _strip_think_tags(response.text),
                    'narrations': narrations
                }

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
                    'text_reply': result.get('text', response.text.strip()),
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
        Generates AI-powered financial tasks using the Groq API key.
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
            tasks = generate_financial_tasks(df, anomalies, self.api_key)
            return {'tasks': tasks, 'error': None}
        except Exception as e:
            err_str = str(e)
            print(f"[Agent.generate_tasks] Exception: {err_str}")
            return {
                'tasks': generate_financial_tasks(df, anomalies, None),
                'error': err_str,
            }
