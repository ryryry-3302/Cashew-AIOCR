"""Web UI for Cashew import pipeline."""

import json
import os
import sys
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename

# Add conda site-packages for pyyaml
sys.path.insert(0, '/opt/conda/lib/python3.8/site-packages')

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline import run_pipeline, CashewPipeline
from validator import validate_json_file
from exporter import CashewExporter
from config import load_config

PROJECT_ROOT = Path(__file__).parent.parent
app = Flask(__name__, template_folder=str(PROJECT_ROOT.resolve() / 'templates'))
app.config['UPLOAD_FOLDER'] = str(PROJECT_ROOT.resolve() / 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
app.config['JSON_SORT_KEYS'] = False

ALLOWED_EXTENSIONS = {'csv', 'json'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/upload-cashew', methods=['POST'])
def upload_cashew():
    """Upload existing Cashew CSV file."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Only CSV allowed.'}), 400
    
    filename = secure_filename(file.filename)
    filepath = Path(app.config['UPLOAD_FOLDER']) / 'cashew' / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)
    file.save(filepath)
    
    # Read and parse the CSV
    try:
        transactions = CashewExporter.read(str(filepath))
        return jsonify({
            'success': True,
            'filename': filename,
            'filepath': str(filepath),
            'transaction_count': len(transactions),
            'transactions': [tx.to_csv_row() for tx in transactions]
        })
    except Exception as e:
        return jsonify({'error': f'Failed to parse CSV: {str(e)}'}), 500


@app.route('/api/upload-jsons', methods=['POST'])
def upload_jsons():
    """Upload multiple bank statement JSON files."""
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400
    
    files = request.files.getlist('files')
    uploaded_files = []
    
    for file in files:
        if file.filename == '':
            continue
        if not allowed_file(file.filename):
            return jsonify({'error': f'Invalid file type for {file.filename}. Only JSON allowed.'}), 400
        
        filename = secure_filename(file.filename)
        filepath = Path(app.config['UPLOAD_FOLDER']) / 'jsons' / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        file.save(filepath)
        
        # Validate and load transactions
        results = validate_json_file(str(filepath))
        valid_txs = []
        errors = []
        
        for result in results:
            if result.valid and result.transaction:
                result.transaction.source_file = filename
                valid_txs.append(result.transaction)
            else:
                errors.append((result.errors,))
        
        uploaded_files.append({
            'filename': filename,
            'filepath': str(filepath),
            'transaction_count': len(valid_txs),
            'errors': errors,
            'transactions': [
                {
                    'date': tx.date.isoformat(),
                    'description': tx.description_original,
                    'amount': tx.amount,
                    'currency': tx.currency,
                    'direction': tx.direction.value,
                    'merchant': tx.merchant,
                    'category': tx.category,
                } for tx in valid_txs
            ]
        })
    
    return jsonify({
        'success': True,
        'uploaded_files': uploaded_files,
        'total_transactions': sum(f['transaction_count'] for f in uploaded_files)
    })


@app.route('/api/process', methods=['POST'])
def process_files():
    """Process uploaded files and generate combined preview."""
    import time
    start_time = time.time()
    
    data = request.get_json()
    cashew_filename = data.get('cashew_filepath')
    json_files = data.get('json_files', [])
    
    print(f"[DEBUG] Processing request: cashew={cashew_filename}, json_files={json_files}")
    
    # If only Cashew file is uploaded, just return the existing transactions
    if not json_files and cashew_filename:
        # Construct full path
        cashew_full_path = Path(app.config['UPLOAD_FOLDER']) / 'cashew' / cashew_filename
        try:
            transactions = CashewExporter.read(str(cashew_full_path))
            print(f"[DEBUG] Read {len(transactions)} transactions from Cashew file")
            return jsonify({
                'success': True,
                'transactions': [tx.to_csv_row() for tx in transactions],
                'total_count': len(transactions),
                'duplicates_removed': 0,
                'uncategorized_count': 0,
            })
        except Exception as e:
            print(f"[DEBUG] Error reading Cashew file: {e}")
            return jsonify({'error': f'Failed to read CSV: {str(e)}'}), 500
    
    if not json_files:
        return jsonify({'error': 'No JSON files to process'}), 400
    
    # Check if JSON files exist
    jsons_dir = Path(app.config['UPLOAD_FOLDER']) / 'jsons'
    missing_files = []
    for filename in json_files:
        filepath = jsons_dir / filename
        if not filepath.exists():
            missing_files.append(filename)
    
    if missing_files:
        print(f"[DEBUG] Missing files: {missing_files}")
        return jsonify({'error': f'Files not found: {missing_files}'}), 400
    
    print(f"[DEBUG] Found {len(json_files)} JSON files")
    
    # Create temporary output directory
    output_dir = Path(app.config['UPLOAD_FOLDER']) / 'output'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Construct full path for Cashew file if provided
    cashew_full_path = None
    if cashew_filename:
        cashew_full_path = Path(app.config['UPLOAD_FOLDER']) / 'cashew' / cashew_filename
    
    # Run pipeline
    try:
        print(f"[DEBUG] Starting pipeline with input_dir={jsons_dir}")
        result = run_pipeline(
            input_dir=str(jsons_dir),
            config_dir='config',
            output_dir=str(output_dir),
            existing_data_path=str(cashew_full_path) if cashew_full_path else None,
        )
        print(f"[DEBUG] Pipeline completed in {time.time() - start_time:.2f}s")
        
        # Read the generated CSV
        csv_path = output_dir / 'cashew_import.csv'
        if csv_path.exists():
            print(f"[DEBUG] Reading CSV from {csv_path}")
            transactions = CashewExporter.read(str(csv_path))
            print(f"[DEBUG] Read {len(transactions)} transactions from CSV")
            return jsonify({
                'success': True,
                'transactions': [tx.to_csv_row() for tx in transactions],
                'total_count': len(transactions),
                'duplicates_removed': result.duplicates_removed,
                'uncategorized_count': result.uncategorized_count,
            })
        else:
            print(f"[DEBUG] CSV file not found at {csv_path}")
            return jsonify({'error': 'Failed to generate output CSV'}), 500
    except Exception as e:
        print(f"[DEBUG] Processing error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500


@app.route('/api/export', methods=['POST'])
def export_csv():
    """Export the final CSV file."""
    data = request.get_json()
    output_dir = Path(app.config['UPLOAD_FOLDER']) / 'output'
    csv_path = output_dir / 'cashew_import.csv'
    
    if not csv_path.exists():
        return jsonify({'error': 'No CSV file to export'}), 404
    
    return send_file(
        csv_path,
        as_attachment=True,
        download_name='cashew_import.csv',
        mimetype='text/csv'
    )


@app.route('/api/download-template', methods=['GET'])
def download_template():
    """Download a sample JSON template."""
    template = {
        "institution": "",
        "account_name": "",
        "statement_period": {
            "start": "YYYY-MM-DD",
            "end": "YYYY-MM-DD"
        },
        "currency": "SGD",
        "transactions": [
            {
                "date": "YYYY-MM-DD",
                "description": "",
                "amount": 0.00,
                "currency": "SGD",
                "direction": "debit",
                "balance_after": None,
                "reference": "",
                "notes": ""
            }
        ]
    }
    
    return jsonify(template)


if __name__ == '__main__':
    # Create upload folders
    upload_folder = Path(app.config['UPLOAD_FOLDER'])
    upload_folder.mkdir(parents=True, exist_ok=True)
    (upload_folder / 'cashew').mkdir(parents=True, exist_ok=True)
    (upload_folder / 'jsons').mkdir(parents=True, exist_ok=True)
    (upload_folder / 'output').mkdir(parents=True, exist_ok=True)
    
    app.run(debug=False, host='0.0.0.0', port=5001)
