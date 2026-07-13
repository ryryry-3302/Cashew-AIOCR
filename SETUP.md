# Setup Instructions

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

## Quick Setup

### 1. Create a Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate the virtual environment
# On Linux/Mac:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Create Default Configuration Files

```bash
python -m src.cli --create-config
```

### 4. Run the Web UI

```bash
python src/webui.py
```

The web UI will be available at: http://localhost:5001

## Alternative: Using Conda (if you have Anaconda/Miniconda)

```bash
# Create conda environment
conda create -n cashew-env python=3.8 -y
conda activate cashew-env

# Install dependencies
pip install -r requirements.txt

# Create config
python -m src.cli --create-config

# Run web UI
python src/webui.py
```

## Directory Structure

```
Cashew-AIOCR/
├── src/
│   ├── webui.py          # Flask web application
│   ├── pipeline.py       # Main processing pipeline
│   ├── models.py         # Data models
│   ├── validator.py      # JSON validation
│   ├── normalizer.py     # Description normalization
│   ├── merchant_rules.py # Merchant matching
│   ├── deduplicator.py   # Duplicate detection
│   ├── cashew_mapper.py  # Cashew format mapping
│   ├── exporter.py       # CSV export
│   ├── config.py         # Configuration loader
│   └── cli.py            # Command-line interface
├── templates/
│   └── index.html        # Web UI frontend
├── config/
│   ├── merchant_rules.yaml
│   ├── category_defaults.yaml
│   ├── accounts.yaml
│   └── cashew_defaults.yaml
├── input/                # Place JSON files here
├── output/               # Generated output
├── uploads/              # Uploaded files (created automatically)
├── requirements.txt
├── SETUP.md
├── README.md
└── SYSTEMPROMPT.md
```

## Usage

1. **Upload Cashew Data** - Upload your existing Cashew CSV file
2. **Upload Bank JSONs** - Upload JSON files extracted from bank statements
3. **Process & Merge** - Click the "Process & Merge Transactions" button
4. **Review** - Preview all merged transactions with filtering and search
5. **Export** - Download the final merged CSV for import into Cashew

## Troubleshooting

### "Could not find the route" error

Make sure you're accessing the correct URL. The web UI runs on port 5001 by default.

### Port already in use

If you get "Address already in use" error, either:
- Kill the existing process on port 5001
- Or change the port in `src/webui.py` (line 235)

### Missing modules

Run `pip install -r requirements.txt` to install all dependencies.
