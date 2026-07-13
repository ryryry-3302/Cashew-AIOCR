"""JSON validation and transaction parsing."""

import json
from datetime import datetime
from typing import Optional, List, Tuple
from pathlib import Path

from models import CanonicalTransaction, Direction, ValidationResult


# Required fields for a valid transaction
REQUIRED_FIELDS = ["date", "description", "amount", "currency", "direction"]

# Valid currency codes (common ones, can be extended)
VALID_CURRENCIES = {
    "SGD", "USD", "EUR", "GBP", "JPY", "CNY", "HKD", "AUD", "CAD",
    "MYR", "THB", "IDR", "PHP", "KRW", "TWD", "VND", "INR"
}


def validate_direction(value: str) -> Optional[Direction]:
    """Validate and convert direction string to Direction enum."""
    if value is None:
        return None
    value_lower = str(value).lower().strip()
    if value_lower == "debit":
        return Direction.DEBIT
    elif value_lower == "credit":
        return Direction.CREDIT
    return None


def parse_date(value: str) -> Optional[datetime.date]:
    """Parse date string to datetime.date object."""
    if value is None:
        return None
    
    formats = [
        "%Y-%m-%d",      # 2024-01-15
        "%d/%m/%Y",      # 15/01/2024
        "%m/%d/%Y",      # 01/15/2024
        "%Y/%m/%d",      # 2024/01/15
        "%d-%m-%Y",      # 15-01-2024
        "%m-%d-%Y",      # 01-15-2024
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(str(value), fmt).date()
        except ValueError:
            continue
    return None


def parse_amount(value) -> Optional[float]:
    """Parse amount to float."""
    if value is None:
        return None
    
    try:
        # Handle string amounts like "123.45" or "$123.45"
        amount_str = str(value).replace("$", "").replace("€", "").replace("£", "")
        return float(amount_str)
    except (ValueError, TypeError):
        return None


def validate_transaction(tx: dict, line_number: int = 0) -> ValidationResult:
    """Validate a single transaction dictionary."""
    errors: List[str] = []
    """Validate a single transaction dictionary."""
    errors = []
    
    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in tx or tx[field] is None:
            errors.append(f"Missing required field: {field}")
    
    if errors:
        return ValidationResult(valid=False, errors=errors)
    
    # Validate date
    parsed_date = parse_date(tx["date"])
    if parsed_date is None:
        errors.append(f"Invalid date format: {tx['date']}")
    
    # Validate amount
    amount = parse_amount(tx["amount"])
    if amount is None:
        errors.append(f"Invalid amount: {tx['amount']}")
    elif amount <= 0:
        errors.append(f"Amount must be positive: {tx['amount']}")
    
    # Validate currency
    currency = str(tx["currency"]).upper().strip()
    if currency not in VALID_CURRENCIES:
        errors.append(f"Invalid currency: {tx['currency']}")
    
    # Validate direction
    direction = validate_direction(tx["direction"])
    if direction is None:
        errors.append(f"Invalid direction: {tx['direction']}")
    
    if errors:
        return ValidationResult(valid=False, errors=errors)
    
    # Create canonical transaction
    canonical = CanonicalTransaction(
        date=parsed_date,
        description_original=str(tx["description"]),
        description_normalized=str(tx["description"]),  # Will be normalized later
        amount=amount,
        currency=currency,
        direction=direction,
        merchant=None,
        category="Uncategorized",
        subcategory=None,
        account=None,
        institution=None,
        reference=tx.get("reference"),
        notes=tx.get("notes"),
        balance=tx.get("balance"),
        confidence=tx.get("confidence", 1.0),
        source_file=None,  # Set by caller
        statement_start=line_number,
        statement_end=line_number,
    )
    
    return ValidationResult(valid=True, errors=[], transaction=canonical)


def validate_json_file(filepath: str) -> List[ValidationResult]:
    """Validate a JSON file containing transactions."""
    results = []
    
    try:
        with open(filepath) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return [ValidationResult(
            valid=False,
            errors=[f"Invalid JSON: {e}"]
        )]
    except FileNotFoundError:
        return [ValidationResult(
            valid=False,
            errors=[f"File not found: {filepath}"]
        )]
    
    # Handle both list and dict with transactions key
    if isinstance(data, list):
        transactions = data
    elif isinstance(data, dict):
        # Try common keys
        for key in ["transactions", "data", "items"]:
            if key in data:
                transactions = data[key]
                break
        else:
            # Check if this is the root-level transaction
            if "date" in data and "description" in data:
                transactions = [data]
            else:
                return [ValidationResult(
                    valid=False,
                    errors=["No transactions found in JSON"]
                )]
    else:
        return [ValidationResult(
            valid=False,
            errors=["JSON must be a list or object with transactions"]
        )]
    
    # Validate each transaction
    for i, tx in enumerate(transactions):
        result = validate_transaction(tx, line_number=i)
        results.append(result)
    
    return results


def load_and_validate(filepath: str) -> Tuple[List, List]:
    """Load and validate a JSON file, returning valid transactions and errors."""
    results = validate_json_file(filepath)
    
    valid_txs = []
    errors = []
    
    for result in results:
        if result.valid and result.transaction:
            valid_txs.append(result.transaction)
        else:
            errors.append((result.errors,))
    
    return valid_txs, errors


if __name__ == "__main__":
    # Test with sample data
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python validator.py <json_file>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    valid_txs, errors = load_and_validate(filepath)
    
    print(f"Valid transactions: {len(valid_txs)}")
    print(f"Errors: {len(errors)}")
    
    for error in errors:
        print(f"  - {error}")
