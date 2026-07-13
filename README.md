# Cashew Import Pipeline

Convert AI-extracted bank statement JSON files into a single CSV that can be directly imported into Cashew.

## Overview

This pipeline processes JSON files extracted from bank statements (via OCR + LLM) and produces a CSV file compatible with Cashew's import format.

## Architecture

```
Bank Statement (PDF/Image)
        │
        ▼
LLM extracts transactions
        │
        ▼
statement.json
        │
        ▼
Python pipeline
        │
        ├── validate JSON
        ├── normalize transactions
        ├── deduplicate
        ├── categorize
        ├── enrich Cashew fields
        ├── merge all statements
        └── export Cashew CSV
```

## Folder Structure

```
project/
│
├── input/                    # Place JSON files here
│   ├── dbs_june.json
│   └── uob_june.json
│
├── config/                   # Configuration files
│   ├── merchant_rules.yaml   # Merchant → category mappings
│   ├── category_defaults.yaml # Category icons/colors
│   ├── accounts.yaml         # Institution → account mapping
│   └── cashew_defaults.yaml  # Default Cashew fields
│
├── output/                   # Generated output
│   ├── cashew_import.csv     # Final CSV for import
│   └── report.txt            # Processing report
│
├── src/                      # Source code
│   ├── models.py             # Data models
│   ├── validator.py          # JSON validation
│   ├── normalizer.py         # Description normalization
│   ├── merchant_rules.py     # Merchant matching
│   ├── deduplicator.py       # Duplicate detection
│   ├── cashew_mapper.py      # Cashew format mapping
│   ├── exporter.py           # CSV export
│   ├── pipeline.py           # Main pipeline
│   └── cli.py                # Command-line interface
│
└── README.md
```

## Quick Start

### 1. Create default configuration files

```bash
   python /home/jovyan/Workspace/Cashew-AIOCR/src/cli.py -i input -c config -o output -e existing_data.csv           
```

### 2. Place your JSON files in the input directory

Your JSON files should follow this schema:

```json
[
  {
    "date": "2024-01-15",
    "description": "VISA DEBIT GRAB*FOOD",
    "amount": 10.50,
    "currency": "SGD",
    "direction": "debit"
  },
  {
    "date": "2024-01-16",
    "description": "PAYMENT RECEIVED",
    "amount": 2000.00,
    "currency": "SGD",
    "direction": "credit"
  }
]
```

### 3. Run the pipeline

**To create a new CSV from scratch:**

```bash
python -m src.cli
```

**To merge new transactions into existing Cashew data:**

```bash
python -m src.cli -e path/to/existing_cashew.csv
```

Or with custom directories:

```bash
python -m src.cli -i my_statements -c my_config -o my_output
```

## Configuration

### merchant_rules.yaml

Define how to categorize transactions based on merchant names:

```yaml
# Simple format
McDonald's: Dining
Starbucks: Dining

# Full format with match criteria
Grab Food:
  match:
    type: contains
    value: grab
  output:
    category: Dining
    icon: cutlery
    color: "#FF607D8B"
    emoji: "🍔"

Shopee:
  match:
    type: prefix
    value: shopee
  output:
    category: Shopping
    icon: shopping_cart
    color: "#FF9900"
    emoji: "🛒"
```

Supported match types:
- `exact`: Exact match
- `prefix`: Match at start of string
- `contains`: Match anywhere in string
- `regex`: Regular expression

### accounts.yaml

Map institutions to Cashew account names:

```yaml
DBS: Bank
UOB: Bank
OCBC: Bank
GrabPay: Wallet
ShopeePay: Wallet
```

### category_defaults.yaml

Define default icons and colors for categories:

```yaml
Dining:
  icon: cutlery
  color: "#FF607D8B"
  emoji: "🍔"

Shopping:
  icon: shopping_cart
  color: "#FF9900"
  emoji: "🛒"
```

### cashew_defaults.yaml

Default values for Cashew fields:

```yaml
budget: ""
objective: ""
extra: ""
```

## Output

### cashew_import.csv

A CSV file with the following columns:

| Column | Description |
|--------|-------------|
| account | Cashew account name |
| amount | Signed amount (negative for debits) |
| amount unpaid | Always 0 for this import |
| currency | Currency code (e.g., SGD) |
| title | Merchant or normalized description |
| note | Original description |
| date | Transaction date (ISO format) |
| income | true/false |
| type | Transaction type |
| category name | Category from merchant rules |
| subcategory name | Optional subcategory |
| color | Category color |
| icon | Category icon |
| emoji | Category emoji |
| budget | Budget association |
| objective | Objective association |
| extra | Extra data |

### report.txt

A text report containing:
- Files processed
- Transaction counts
- Duplicates removed
- Uncategorized transactions
- Validation errors

## Transaction Model

### CanonicalTransaction

The internal representation used throughout the pipeline:

```python
@dataclass
class CanonicalTransaction:
    date: date
    description_original: str
    description_normalized: str
    amount: float
    currency: str
    direction: Direction  # DEBIT or CREDIT
    merchant: Optional[str]
    category: str
    subcategory: Optional[str]
    account: Optional[str]
    institution: Optional[str]
    reference: Optional[str]
    notes: Optional[str]
    balance: Optional[float]
    income: bool
    confidence: float
    source_file: Optional[str]
    statement_start: Optional[int]
    statement_end: Optional[int]
    _id: Optional[str]  # Stable ID for deduplication
```

## Validation

The pipeline validates each transaction:
- Required fields exist
- Valid ISO dates
- Amount > 0
- Valid currency code
- Valid direction (debit/credit)

Invalid transactions are logged but don't stop processing.

## Duplicate Detection

Duplicates are detected using a stable ID based on:
- Date
- Amount
- Direction
- Normalized merchant
- Institution

This ensures the same transaction never creates duplicates, even across multiple runs.

## Extending the Pipeline

### Adding a new bank format

1. Add the new format to `validator.py` in the `validate_json_file` function
2. Test with sample data

### Adding new merchant rules

Edit `config/merchant_rules.yaml` and add your rules.

### Adding new categories

1. Add to `config/category_defaults.yaml`
2. Add rules in `config/merchant_rules.yaml`

### Adding support for another finance app

1. Create a new mapper in `src/<app>_mapper.py`
2. Create a new exporter in `src/<app>_exporter.py`
3. Update `pipeline.py` to use the new components

## License

MIT License
