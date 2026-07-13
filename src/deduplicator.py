"""Duplicate detection and removal."""

from typing import Dict, List, Set, Tuple

from models import CanonicalTransaction, DuplicateInfo


class DuplicateDetector:
    """Detect and remove duplicate transactions."""
    
    def __init__(self):
        self._seen: Dict[str, CanonicalTransaction] = {}
        self._duplicates: List[DuplicateInfo] = []
    
    def add(self, tx: CanonicalTransaction) -> bool:
        """
        Add a transaction. Returns True if it's a new transaction,
        False if it's a duplicate.
        """
        tx_id = tx._id
        
        if tx_id in self._seen:
            # This is a duplicate
            self._duplicates.append(DuplicateInfo(
                primary=self._seen[tx_id],
                duplicate=tx,
                match_fields=["date", "amount", "merchant", "direction"],
            ))
            return False
        
        self._seen[tx_id] = tx
        return True
    
    def add_all(self, transactions: List[CanonicalTransaction]) -> List[CanonicalTransaction]:
        """Add all transactions and return only unique ones."""
        unique = []
        for tx in transactions:
            if self.add(tx):
                unique.append(tx)
        return unique
    
    @property
    def duplicate_count(self) -> int:
        """Return the number of duplicates found."""
        return len(self._duplicates)
    
    def get_duplicates(self) -> List[DuplicateInfo]:
        """Return all detected duplicates."""
        return self._duplicates


def deduplicate(transactions: List[CanonicalTransaction]) -> Tuple[List[CanonicalTransaction], int]:
    """Remove duplicates from a list of transactions."""
    detector = DuplicateDetector()
    unique = detector.add_all(transactions)
    return unique, detector.duplicate_count


if __name__ == "__main__":
    # Test duplicate detection
    from datetime import date
    from models import Direction
    
    tx1 = CanonicalTransaction(
        date=date(2024, 1, 15),
        description_original="GRAB FOOD",
        description_normalized="grab food",
        amount=10.0,
        currency="SGD",
        direction=Direction.DEBIT,
        merchant="Grab Food",
    )
    
    tx2 = CanonicalTransaction(
        date=date(2024, 1, 15),
        description_original="GRAB FOOD",
        description_normalized="grab food",
        amount=10.0,
        currency="SGD",
        direction=Direction.DEBIT,
        merchant="Grab Food",
    )
    
    tx3 = CanonicalTransaction(
        date=date(2024, 1, 16),
        description_original="GRAB FOOD",
        description_normalized="grab food",
        amount=10.0,
        currency="SGD",
        direction=Direction.DEBIT,
        merchant="Grab Food",
    )
    
    transactions = [tx1, tx2, tx3]
    unique, count = deduplicate(transactions)
    
    print(f"Original: {len(transactions)}")
    print(f"Unique: {len(unique)}")
    print(f"Duplicates removed: {count}")
