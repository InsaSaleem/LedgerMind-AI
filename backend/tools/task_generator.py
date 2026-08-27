from groq import Groq
import json
import time


def call_tasks_model_with_retry(client, model_name, prompt, max_retries=3):
    """Wrap Groq calls with exponential-backoff retry on 429 quota errors."""
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}]
            )
            return response
        except Exception as e:
            err_str = str(e)
            if '429' in err_str or 'quota' in err_str.lower() or 'rate' in err_str.lower():
                wait_time = (2 ** attempt) * 10
                print(f"[Tasks] 429 rate-limit hit. Waiting {wait_time}s (attempt {attempt+1}/{max_retries})...")
                time.sleep(wait_time)
                if attempt == max_retries - 1:
                    raise Exception(
                        "Groq Tasks API rate limit reached. "
                        "Please wait 30–60 seconds and try again."
                    )
            else:
                raise e


def generate_financial_tasks(df, anomalies, tasks_api_key):
    """
    Uses a dedicated Groq API key to analyze the financial data
    and generate a prioritized list of actionable financial tasks.

    Args:
        df: pandas DataFrame with financial transactions
        anomalies: list of detected anomaly dicts
        tasks_api_key: dedicated GROQ_API_KEY

    Returns: list of task dicts with keys: title, description, priority, category
    """
    if not tasks_api_key:
        return _generate_fallback_tasks(df, anomalies)

    try:
        client = Groq(api_key=tasks_api_key)
        model_name = 'llama-3.3-70b-versatile'

        # Build context
        total_spend = float(df['Amount'].sum()) if 'Amount' in df.columns else 0
        num_transactions = len(df)

        category_summary = "No categories available."
        if 'Category' in df.columns:
            cat_sums = df.groupby('Category')['Amount'].sum().sort_values(ascending=False)
            category_summary = ", ".join(
                [f"{cat}: ${amt:.2f}" for cat, amt in cat_sums.head(5).items()]
            )

        anomaly_summary = "No anomalies detected."
        if anomalies:
            anomaly_lines = []
            for a in anomalies[:5]:
                anomaly_lines.append(
                    f"- {a.get('description', 'Unknown')} (${a.get('amount', 0):.2f}): {a.get('reason', '')}"
                )
            anomaly_summary = "\n".join(anomaly_lines)

        prompt = f"""You are LedgerMind AI, a financial intelligence agent.
Analyze this financial data and generate 5-8 specific, actionable financial tasks.

DATA SUMMARY:
- Total transactions: {num_transactions}
- Total spend: ${total_spend:.2f}
- Top categories: {category_summary}
- Detected anomalies:
{anomaly_summary}

Generate tasks as a JSON array. Each task should have:
- "title": short action item (max 60 chars)
- "description": 1-2 sentence explanation of why this matters
- "priority": "high", "medium", or "low"
- "category": one of "review", "budget", "investigate", "optimize", "plan"

Return ONLY valid JSON array, no other text or markdown."""

        response = call_tasks_model_with_retry(client, model_name, prompt)
        text = response.choices[0].message.content.strip()

        # Strip <think>...</think> or <thought>...</thought> blocks (even if unclosed)
        import re
        text = re.sub(r'<(think|thought)>.*?(?:</\1>|$)', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'</?(think|thought)>', '', text, flags=re.IGNORECASE).strip()

        # Clean markdown fences
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        tasks = json.loads(text)

        # Validate structure
        validated_tasks = []
        for task in tasks:
            validated_tasks.append({
                'title': str(task.get('title', 'Untitled Task'))[:80],
                'description': str(task.get('description', ''))[:200],
                'priority': task.get('priority', 'medium') if task.get('priority') in ['high', 'medium', 'low'] else 'medium',
                'category': task.get('category', 'review'),
                'completed': False,
            })

        return validated_tasks

    except Exception as e:
        print(f"[task_generator] Groq error: {e}")
        return _generate_fallback_tasks(df, anomalies)


def _generate_fallback_tasks(df, anomalies):
    """
    Generate basic tasks without AI when the API key is missing or quota exceeded.
    """
    tasks = []

    if df is not None and not df.empty:
        total = float(df['Amount'].sum()) if 'Amount' in df.columns else 0
        tasks.append({
            'title': f'Review total spending: ${total:,.2f}',
            'description': f'You have {len(df)} transactions totaling ${total:,.2f}. Review for accuracy.',
            'priority': 'medium',
            'category': 'review',
            'completed': False,
        })

    for i, anom in enumerate(anomalies[:3]):
        tasks.append({
            'title': f"Investigate: {anom.get('description', 'Unknown')[:40]}",
            'description': anom.get('reason', 'Flagged as anomalous spending.'),
            'priority': 'high',
            'category': 'investigate',
            'completed': False,
        })

    if df is not None and 'Category' in df.columns:
        top_cat = df.groupby('Category')['Amount'].sum().sort_values(ascending=False)
        if not top_cat.empty:
            cat_name = top_cat.index[0]
            cat_amt = float(top_cat.iloc[0])
            tasks.append({
                'title': f'Set budget for {cat_name}',
                'description': f'Your highest spending category is {cat_name} at ${cat_amt:,.2f}. Consider setting a monthly budget.',
                'priority': 'medium',
                'category': 'budget',
                'completed': False,
            })

    if not tasks:
        tasks.append({
            'title': 'Upload a financial statement',
            'description': 'Upload a bank statement to get AI-powered financial tasks and action items.',
            'priority': 'low',
            'category': 'plan',
            'completed': False,
        })

    return tasks
