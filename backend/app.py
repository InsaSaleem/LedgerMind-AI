import os
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app) # Enable CORS for frontend

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# We will store the latest dataframe globally for MVP purposes.
# In a real app, use sessions or a database.
global_app_state = {
    'dataframe': None,
    'anomalies': [],
    'charts': []
}

from agent.orchestrator import LedgerMindAgent

# Initialize the Gemini Agent
gemini_api_key = os.environ.get('GEMINI_API_KEY')
agent = LedgerMindAgent(gemini_api_key)

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # We can simulate the agentic workflow triggering upon upload
        try:
            # Let the agent handle the newly uploaded file autonomously
            response = agent.process_uploaded_file(filepath)
            
            # Store the state for subsequent queries
            if response.get('dataframe') is not None:
                global_app_state['dataframe'] = response['dataframe']
                global_app_state['anomalies'] = response.get('anomalies', [])
            
            # If the response explicitly returned an error (e.g. from orchestrator exception)
            if 'error' in response:
                print(f"Upload flow generated an error response: {response['error']}")
                return jsonify({'error': response['error'], 'agent_narration': response.get('narration', [])}), 400
                
            total_spend = 0
            if global_app_state['dataframe'] is not None and not global_app_state['dataframe'].empty:
                total_spend = float(global_app_state['dataframe']['Amount'].sum())

            return jsonify({
                'message': 'File uploaded and processed successfully',
                'filename': filename,
                'agent_narration': response.get('narration', []),
                'anomalies': global_app_state['anomalies'],
                'stats': {
                    'total_spend': total_spend,
                    'anomaly_count': len(global_app_state['anomalies'])
                }
            }), 200
        except Exception as e:
            print(f"Flask App Route Exception: {e}")
            return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    
    if not user_message:
        return jsonify({'error': 'Empty message'}), 400
        
    try:
        # Pass the message and the current state to the agent
        response = agent.chat(user_message, global_app_state)
        
        if 'new_chart' in response:
            global_app_state['charts'].append(response['new_chart'])
            
        return jsonify({
            'reply': response.get('text_reply', ''),
            'narrations': response.get('narrations', []),
            'chart': response.get('new_chart', None)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    df = global_app_state['dataframe']
    if df is None:
        return jsonify({'stats': None})
        
    total_spend = float(df['Amount'].sum())
    top_categories = df.groupby('Category')['Amount'].sum().sort_values(ascending=False).head(3).to_dict() if 'Category' in df.columns else {}
    
    return jsonify({
        'stats': {
            'total_spend': total_spend,
            'anomaly_count': len(global_app_state['anomalies']),
            'top_categories': top_categories
        },
        'anomalies': global_app_state['anomalies']
    }), 200

@app.route('/api/export', methods=['POST'])
def export_report():
    if global_app_state['dataframe'] is None:
        return jsonify({'error': 'No data available to export'}), 400
        
    from tools.report_generator import generate_pdf_report
    report_path = generate_pdf_report(global_app_state['dataframe'], global_app_state['anomalies'], global_app_state['charts'], app.config['UPLOAD_FOLDER'])
    
    # In a real app we'd use send_file, but for the MVP, sending the URL/Path is fine, 
    # or returning a base64 encoded PDF.
    return jsonify({'report_url': report_path}), 200

@app.route('/api/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename), as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
