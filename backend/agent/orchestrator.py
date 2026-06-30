import google.generativeai as genai
import json
from tools.file_handler import detect_file_type
from tools.pdf_parser import parse_pdf_statement
from tools.data_parser import parse_statement
from tools.analyzer import detect_anomalies
from tools.visualizer import generate_chart

class LedgerMindAgent:
    def __init__(self, api_key):
        if api_key:
            genai.configure(api_key=api_key)
        # Using a model that supports function calling
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        
    def process_uploaded_file(self, filepath):
        """
        Autonomous workflow for when a file is uploaded.
        """
        narrations = []
        
        narrations.append(f"Detecting file type for {filepath}...")
        file_type = detect_file_type(filepath)
        
        df = None
        if file_type == 'pdf':
            narrations.append(f"Detected PDF statement. Extracting transaction table (with OCR fallback if needed)...")
            df = parse_pdf_statement(filepath)
        elif file_type in ['csv', 'excel']:
            narrations.append(f"Detected {file_type.upper()} file. Normalizing data...")
            df = parse_statement(filepath)
        else:
            narrations.append("Error: Unsupported file type.")
            return {'error': 'Unsupported file type', 'narration': narrations}
            
        narrations.append(f"Successfully parsed {len(df)} transactions. Detecting anomalies...")
        anomalies = detect_anomalies(df)
        
        if anomalies:
            narrations.append(f"Detected {len(anomalies)} spending anomalies/spikes.")
        else:
            narrations.append("No significant anomalies detected in this dataset.")
            
        return {
            'dataframe': df,
            'anomalies': anomalies,
            'narration': narrations
        }
        
    def chat(self, user_message, state):
        """
        Handles user chat query. We simulate the agentic tool call loop.
        In a full implementation, we pass the tools to genai.GenerativeModel 
        and let it call them. For this MVP, we use a structured prompt to 
        extract intent if true function calling setup is too complex for this snippet,
        but we'll implement a basic router logic or prompt to simulate it.
        """
        narrations = []
        df = state.get('dataframe')
        
        if df is None:
            return {'text_reply': "Please upload a bank statement first before querying.", 'narrations': narrations}
            
        # Very basic LLM prompt to determine action: 
        # (1) Answer question (2) Generate chart
        prompt = f"""
        You are LedgerMind AI, a financial intelligence agent.
        The user has uploaded a financial dataset with columns: {df.columns.tolist()}.
        Total rows: {len(df)}.
        Top 5 rows:
        {df.head().to_string()}
        
        User question: "{user_message}"
        
        If the user wants a chart or visualization, output JSON: {{"action": "generate_chart", "type": "trend_line" (or "category_pie", "bar")}}.
        If the user wants a data answer, answer it directly based on the data provided above. Output JSON: {{"action": "answer", "text": "your answer"}}
        """
        
        response = self.model.generate_content(prompt)
        try:
            # Clean response
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:-3]
            elif text.startswith("```"):
                text = text[3:-3]
                
            result = json.loads(text)
            
            if result.get('action') == 'generate_chart':
                chart_type = result.get('type', 'bar')
                narrations.append(f"Analyzing request... Determined user wants a chart. Calling generate_chart(type='{chart_type}')...")
                chart_base64 = generate_chart(df, chart_type)
                return {
                    'text_reply': f"Here is the {chart_type.replace('_', ' ')} you requested.",
                    'narrations': narrations,
                    'new_chart': chart_base64
                }
            else:
                narrations.append("Analyzing data to answer the query...")
                return {
                    'text_reply': result.get('text', "I analyzed the data but couldn't form a conclusive answer."),
                    'narrations': narrations
                }
        except Exception as e:
             # Fallback
             return {
                 'text_reply': f"I processed your query: {response.text}",
                 'narrations': ["Used LLM to answer query."]
             }
