"""Export Cashew transactions to CSV."""

import csv
from datetime import date, datetime
from pathlib import Path
from typing import List

from .models import CashewTransaction, CashewType, Direction


class CashewExporter:
    """Export Cashew transactions to CSV format."""
    
    # CSV column order matching Cashew import format
    CSV_COLUMNS = [
        "account",
        "amount",
        "amount unpaid",
        "currency",
        "title",
        "note",
        "date",
        "income",
        "type",
        "category name",
        "subcategory name",
        "color",
        "icon",
        "emoji",
        "budget",
        "objective",
        "extra",
    ]
    
    @staticmethod
    def read(filepath: str) -> List[CashewTransaction]:
        """Read existing Cashew transactions from CSV."""
        transactions = []
        
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                # Parse date - handle both formats
                date_str = row.get("date", "")
                try:
                    # Try parsing the Cashew format first
                    if " " in date_str:
                        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S.%f")
                    else:
                        dt = datetime.strptime(date_str, "%Y-%m-%d")
                    tx_date = dt.date()
                except ValueError:
                    # Fallback to ISO format
                    tx_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                
                # Parse amount
                amount_str = row.get("amount", "")
                amount = float(amount_str) if amount_str else 0.0
                
                # Parse amount_unpaid
                amount_unpaid_str = row.get("amount unpaid", "")
                amount_unpaid = float(amount_unpaid_str) if amount_unpaid_str else 0.0
                
                # Parse income
                income_str = row.get("income", "false")
                income = income_str.lower() == "true"
                
                # Parse type
                tx_type_str = row.get("type", "default")
                try:
                    tx_type = CashewType(tx_type_str)
                except ValueError:
                    tx_type = CashewType.DEFAULT
                
                transaction = CashewTransaction(
                    account=row.get("account", "Unknown"),
                    amount=amount,
                    amount_unpaid=amount_unpaid,
                    currency=row.get("currency", "SGD"),
                    title=row.get("title", ""),
                    note=row.get("note", ""),
                    date=tx_date,
                    income=income,
                    type=tx_type,
                    category_name=row.get("category name", "Uncategorized"),
                    subcategory_name=row.get("subcategory name", "") or None,
                    color=row.get("color", "#808080"),
                    icon=row.get("icon", "default"),
                    emoji=row.get("emoji", ""),
                    budget=row.get("budget", ""),
                    objective=row.get("objective", ""),
                    extra=row.get("extra", ""),
                )
                transactions.append(transaction)
        
        return transactions
    
    def __init__(self, output_path: str):
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
    
    def export(self, transactions: List[CashewTransaction]):
        """Export transactions to CSV."""
        # Sort transactions by date, amount, title for deterministic output
        sorted_txs = sorted(
            transactions,
            key=lambda tx: (tx.date, tx.amount, tx.title)
        )
        
        with open(self.output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.CSV_COLUMNS)
            writer.writeheader()
            
            for tx in sorted_txs:
                row = tx.to_csv_row()
                writer.writerow(row)
    
    def export_merged(
        self,
        existing_transactions: List[CashewTransaction],
        new_transactions: List[CashewTransaction],
    ):
        """Merge existing and new transactions, removing duplicates."""
        # Create a set of existing transaction keys (date + amount + title)
        existing_keys = set()
        for tx in existing_transactions:
            key = (tx.date, tx.amount, tx.title)
            existing_keys.add(key)
        
        # Filter out duplicates from new transactions
        unique_new = []
        for tx in new_transactions:
            key = (tx.date, tx.amount, tx.title)
            if key not in existing_keys:
                unique_new.append(tx)
        
        # Combine all transactions
        all_transactions = existing_transactions + unique_new
        
        # Sort by date
        sorted_txs = sorted(all_transactions, key=lambda tx: tx.date)
        
        with open(self.output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.CSV_COLUMNS)
            writer.writeheader()
            
            for tx in sorted_txs:
                row = tx.to_csv_row()
                writer.writerow(row)
        
        return len(unique_new)
    
    def export_report(
        self,
        transactions: List[CashewTransaction],
        duplicates_removed: int,
        uncategorized_count: int,
        validation_errors: List[tuple],
        files_processed: List[str],
    ):
        """Export a processing report."""
        report_path = self.output_path.parent / "report.txt"
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("CASHEW IMPORT PIPELINE REPORT\n")
            f.write("=" * 60 + "\n\n")
            
            f.write("FILES PROCESSED\n")
            f.write("-" * 40 + "\n")
            for filepath in files_processed:
                f.write(f"  - {filepath}\n")
            f.write("\n")
            
            f.write("TRANSACTIONS\n")
            f.write("-" * 40 + "\n")
            f.write(f"  Total imported: {len(transactions)}\n")
            f.write(f"  Duplicates removed: {duplicates_removed}\n")
            f.write(f"  Uncategorized: {uncategorized_count}\n")
            f.write("\n")
            
            if validation_errors:
                f.write("VALIDATION ERRORS\n")
                f.write("-" * 40 + "\n")
                for file, line, error in validation_errors:
                    f.write(f"  {file}:{line} - {error}\n")
                f.write("\n")
            
            f.write("OUTPUT\n")
            f.write("-" * 40 + "\n")
            f.write(f"  CSV file: {self.output_path}\n")
            f.write(f"  Report file: {report_path}\n")


if __name__ == "__main__":
    # Test export
    from datetime import date
    from models import CashewType
    
    tx = CashewTransaction(
        account="Bank",
        amount=-10.0,
        amount_unpaid=0.0,
        currency="SGD",
        title="Grab Food",
        note="VISA DEBIT GRAB*FOOD",
        date=date(2024, 1, 15),
        income=False,
        type=CashewType.DEFAULT,
        category_name="Dining",
        subcategory_name=None,
        color="#FF607D8B",
        icon="cutlery",
        emoji="🍔",
        budget="",
        objective="",
        extra="",
    )
    
    exporter = CashewExporter("output/test.csv")
    exporter.export([tx])
    print("Exported to output/test.csv")
