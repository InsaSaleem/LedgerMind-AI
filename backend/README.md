# ⚙️ LedgerMind AI — Backend Services

The backend for **LedgerMind AI** is an enterprise-grade REST API server built with **Python**, **Flask**, and **Groq LPU Hardware Acceleration** (`qwen/qwen3.8-27b`). It handles financial document parsing, statistical anomaly detection, agentic reasoning, dynamic chart generation, and executive PDF reporting.

---

## ⚡ Quick Start

```bash
# 1. Create and activate virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env from template
copy .env.example .env
# Edit .env and insert your GROQ_API_KEY

# 4. Run the Flask application
python app.py
```
*Backend server runs at:* `http://127.0.0.1:5000`

---

## 🏗️ Core Architecture & Modules

- **`agent/orchestrator.py`**: Coordinates the agentic workflow, prompt token formatting, Groq API integration, and cache management.
- **`tools/file_handler.py`**: Safe MIME and extension validation.
- **`tools/data_parser.py`**: Normalizes non-uniform CSV and Excel columns into standardized schemas.
- **`tools/pdf_parser.py`**: Extracts transaction tables from digital PDF statements using `pdfplumber`.
- **`tools/image_parser.py`**: Groq Vision & OCR engine for receipts and scanned images.
- **`tools/analyzer.py`**: Z-Score statistical model identifying financial outliers.
- **`tools/visualizer.py`**: Converts Pandas aggregations into dark-theme Matplotlib base64 charts.
- **`tools/task_generator.py`**: AI recommendation engine prioritizing operational action items.
- **`tools/report_generator.py`**: Compiles session data into downloadable ReportLab PDF reports.
- **`api/index.py`**: Vercel Serverless Function entry point.

For full project documentation, see the main [Root README](../README.md).
