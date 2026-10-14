import os
os.environ.setdefault('MPLCONFIGDIR', '/tmp/matplotlib')

from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Determine static folder (only exists locally / monorepo, not in standalone backend deployment)
docs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'docs'))
if os.path.isdir(docs_path):
    app = Flask(__name__, static_folder=docs_path, static_url_path='/')
else:
    app = Flask(__name__, static_folder=None)

# Configure CORS to allow all origins and methods
CORS(app, resources={r"/*": {"origins": "*"}})

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response

# Use /tmp for serverless environments (Vercel, AWS Lambda)
is_serverless = bool(os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'))
if is_serverless:
    UPLOAD_FOLDER = os.path.join('/tmp', 'uploads')
else:
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')

try:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
except Exception:
    UPLOAD_FOLDER = os.path.join('/tmp', 'uploads')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# Global state (MVP — use sessions/DB in production)
global_app_state = {
    'dataframe': None,
    'anomalies': [],
    'charts': []
}

from agent.orchestrator import LedgerMindAgent

# Initialize the Groq Agent
groq_api_key = os.environ.get('GROQ_API_KEY')
agent = LedgerMindAgent(api_key=groq_api_key)


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
    print(f"GROQ_API_KEY loaded: {'YES' if groq_api_key else 'NO'}")
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
                'reply': '⏳ AI is busy right now. Please wait a few seconds and try again.',
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


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint — shows backend status and AI provider info."""
    return jsonify({
        'status': 'ok',
        'provider': 'groq',
        'model': 'qwen/qwen3.8-27b',
        'has_api_key': bool(groq_api_key),
    }), 200


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if app.static_folder and os.path.isdir(app.static_folder):
        if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        elif os.path.exists(os.path.join(app.static_folder, 'index.html')):
            return send_from_directory(app.static_folder, 'index.html')
    return jsonify({
        'status': 'ok',
        'message': 'LedgerMind AI Backend API is active',
        'health_check': '/api/health'
    }), 200



if __name__ == '__main__':
    app.run(debug=True, port=5000)
