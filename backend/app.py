import os
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
# Purani line: CORS(app) ko is se replace karein
CORS(app, resources={r"/*": {"origins": "*"}})

# Use /tmp for serverless environments like Vercel
if os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'):
    UPLOAD_FOLDER = os.path.join('/tmp', 'uploads')
else:
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Global state (MVP — use sessions/DB in production)
global_app_state = {
    'dataframe': None,
    'anomalies': [],
    'charts': []
}

from agent.orchestrator import LedgerMindAgent

# Initialize the Gemini Agent with all three keys
gemini_api_key    = os.environ.get('GEMINI_API_KEY')
gemini_vision_key = os.environ.get('GEMINI_VISION_KEY', gemini_api_key)
gemini_tasks_key  = os.environ.get('GEMINI_TASKS_KEY', gemini_api_key)
agent = LedgerMindAgent(
    gemini_api_key,
    vision_api_key=gemini_vision_key,
    tasks_api_key=gemini_tasks_key,
)


def _is_rate_limit(err_str):
    return '429' in err_str or 'quota' in err_str.lower() or 'rate limit' in err_str.lower()


def _safe_total_spend(df):
    """Safely compute total spend, returning 0 if the Amount column is missing."""
    if df is not None and not df.empty and 'Amount' in df.columns:
        try:
            return float(df['Amount'].sum())
        except Exception:
            return 0.0
    return 0.0


@app.route('/api/upload', methods=['POST'])
def upload_file():
    print(f"GEMINI_API_KEY loaded: {'YES' if gemini_api_key else 'NO'}")
    print(f"GEMINI_VISION_KEY loaded: {'YES' if gemini_vision_key else 'NO'}")
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            response = agent.process_uploaded_file(filepath)

            # Store state for subsequent queries
            if response.get('dataframe') is not None:
                global_app_state['dataframe'] = response['dataframe']
                global_app_state['anomalies'] = response.get('anomalies', [])

            if 'error' in response:
                err = response['error']
                print(f"Upload error: {err}")
                if _is_rate_limit(err):
                    return jsonify({
                        'error': '⏳ AI quota reached. Please wait 60 seconds and try again, or use a CSV/Excel file instead.',
                        'agent_narration': response.get('narration', [])
                    }), 429
                return jsonify({'error': err, 'agent_narration': response.get('narration', [])}), 400

            total_spend = _safe_total_spend(global_app_state['dataframe'])

            return jsonify({
                'message': 'File uploaded and processed successfully',
                'filename': filename,
                'parsing_method': response.get('parsing_method', 'standard'),
                'agent_narration': response.get('narration', []),
                'anomalies': global_app_state['anomalies'],
                'stats': {
                    'total_spend': total_spend,
                    'anomaly_count': len(global_app_state['anomalies'])
                }
            }), 200

        except Exception as e:
            err_str = str(e)
            print(f"Flask upload exception: {err_str}")
            if _is_rate_limit(err_str):
                return jsonify({
                    'error': '⏳ AI quota reached. Please wait 60 seconds and try again, or use a CSV/Excel file instead.'
                }), 429
            return jsonify({'error': err_str}), 500


@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')

    if not user_message:
        return jsonify({'error': 'Empty message'}), 400

    try:
        state_for_agent = {
            'dataframe': global_app_state['dataframe'],
            'anomalies': global_app_state['anomalies'],
        }
        response = agent.chat(user_message, state_for_agent)

        if 'new_chart' in response:
            global_app_state['charts'].append(response['new_chart'])

        return jsonify({
            'reply': response.get('text_reply', ''),
            'narrations': response.get('narrations', []),
            'chart': response.get('new_chart', None)
        }), 200

    except Exception as e:
        err_str = str(e)
        if _is_rate_limit(err_str):
            return jsonify({
                'reply': '⏳ AI rate limit reached. Free tier allows 15 requests/minute. Please wait 30–60 seconds and try again.',
                'narrations': [],
                'chart': None
            }), 200
        return jsonify({'reply': f'Server error: {err_str}', 'narrations': []}), 200


@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    df = global_app_state['dataframe']
    if df is None:
        return jsonify({'stats': None})

    total_spend = _safe_total_spend(df)

    if 'Category' in df.columns:
        cat_summary = df.groupby('Category')['Amount'].sum().sort_values(ascending=False)
        top_cat_name = cat_summary.index[0] if len(cat_summary) > 0 else 'N/A'
        top_cat_amount = float(cat_summary.iloc[0]) if len(cat_summary) > 0 else 0
        top_categories = cat_summary.head(5).to_dict()
    else:
        top_cat_name = 'N/A'
        top_cat_amount = 0
        top_categories = {}

    return jsonify({
        'stats': {
            'total_spend': total_spend,
            'anomaly_count': len(global_app_state['anomalies']),
            'top_categories': top_categories,
            'top_cat_name': top_cat_name,
            'top_cat_amount': top_cat_amount,
        },
        'anomalies': global_app_state['anomalies']
    }), 200


@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """Generate AI-powered financial tasks using the dedicated tasks API key."""
    try:
        state_for_agent = {
            'dataframe': global_app_state['dataframe'],
            'anomalies': global_app_state['anomalies'],
        }
        result = agent.generate_tasks(state_for_agent)
        return jsonify({
            'tasks': result.get('tasks', []),
            'error': result.get('error'),
        }), 200
    except Exception as e:
        err_str = str(e)
        print(f"Tasks endpoint error: {err_str}")
        return jsonify({
            'tasks': [],
            'error': err_str,
        }), 500


@app.route('/api/export', methods=['POST'])
def export_report():
    if global_app_state['dataframe'] is None:
        return jsonify({'error': 'No data available to export'}), 400

    from tools.report_generator import generate_pdf_report
    report_path = generate_pdf_report(
        global_app_state['dataframe'],
        global_app_state['anomalies'],
        global_app_state['charts'],
        app.config['UPLOAD_FOLDER']
    )
    return jsonify({'report_url': report_path}), 200


@app.route('/api/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename), as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
