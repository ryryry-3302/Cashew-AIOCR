"""Canonical transaction models and Cashew-specific models."""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional, List, Tuple
from enum import Enum
import hashlib


class Direction(Enum):
    DEBIT = "debit"
    CREDIT = "credit"


class CashewType(Enum):
    DEFAULT = "default"
    TRANSFER = "transfer"
    BUDGET = "budget"


@dataclass
class CanonicalTransaction:
    """Canonical transaction model that every stage produces."""
    
    # Core fields (extracted from source)
    date: date
    description_original: str
    description_normalized: str
    amount: float
    currency: str
    direction: Direction
    
    # Enriched fields (added during processing)
    merchant: Optional[str] = None
    category: str = "Uncategorized"
    subcategory: Optional[str] = None
    account: Optional[str] = None
    institution: Optional[str] = None
    reference: Optional[str] = None
    notes: Optional[str] = None
    balance: Optional[float] = None
    
    # Computed fields
    income: bool = field(default=False)
    confidence: float = field(default=1.0)
    
    # Provenance
    source_file: Optional[str] = None
    statement_start: Optional[int] = None
    statement_end: Optional[int] = None
    
    # Stable ID for deduplication
    _id: Optional[str] = field(default=None, repr=False)
    
    def __post_init__(self):
        # Compute income flag
        self.income = self.direction == Direction.CREDIT
        
        # Compute stable ID if not already set
        if self._id is None:
            self._id = self.compute_id()
    
    def compute_id(self) -> str:
        """Generate a stable transaction ID based on key fields."""
        data = f"{self.date}|{self.amount}|{self.direction.value}|{self.description_normalized}|{self.institution or ''}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    @property
    def amount_signed(self) -> float:
        """Return signed amount (negative for debits, positive for credits)."""
        return -self.amount if self.direction == Direction.DEBIT else self.amount
    
    def to_cashew(self, config: dict) -> "CashewTransaction":
        """Convert canonical transaction to Cashew format."""
        cat_config = config.get("categories", {}).get(self.category, {})
        
        # Get account with default fallback
        accounts = config.get("accounts", {})
        account_name = accounts.get(self.account, accounts.get("_", "Unknown"))
        
        return CashewTransaction(
            account=account_name,
            amount=self.amount_signed,
            amount_unpaid=0.0,
            currency=self.currency,
            title=self.merchant or self.description_normalized,
            note=self.description_original,
            date=self.date,
            income=self.income,
            type=CashewType.DEFAULT,
            category_name=self.category,
            subcategory_name=self.subcategory,
            color=cat_config.get("color", "#808080"),
            icon=cat_config.get("icon", "default"),
            emoji=cat_config.get("emoji", ""),
            budget=config.get("defaults", {}).get("budget", ""),
            objective=config.get("defaults", {}).get("objective", ""),
            extra=config.get("defaults", {}).get("extra", ""),
        )


@dataclass
class CashewTransaction:
    """Cashew-specific transaction model for export."""
    
    # Cashew fields
    account: str
    amount: float
    amount_unpaid: float
    currency: str
    title: str
    note: str
    date: date
    income: bool
    type: CashewType
    category_name: str
    subcategory_name: Optional[str]
    color: str
    icon: str
    emoji: str
    budget: str
    objective: str
    extra: str
    
    # Optional fields
    category_id: Optional[str] = None
    subcategory_id: Optional[str] = None
    
    def to_csv_row(self) -> dict:
        """Convert to CSV row format."""
        return {
            "account": self.account,
            "amount": self.amount if self.amount != 0 else "",
            "amount unpaid": self.amount_unpaid if self.amount_unpaid != 0 else "",
            "currency": self.currency,
            "title": self.title,
            "note": self.note,
            "date": self.date.strftime("%Y-%m-%d %H:%M:%S.000") if isinstance(self.date, date) else str(self.date),
            "income": "false" if self.income else "false",
            "type": self.type.value,
            "category name": self.category_name,
            "subcategory name": self.subcategory_name or "",
            "color": self.color,
            "icon": self.icon,
            "emoji": self.emoji,
            "budget": self.budget,
            "objective": self.objective,
            "extra": self.extra,
        }
    
    @classmethod
    def from_canonical(cls, tx: CanonicalTransaction, config: dict) -> "CashewTransaction":
        """Create CashewTransaction from canonical transaction using config."""
        # Determine amount
        amount = tx.amount_signed
        
        # Determine title and note
        title = tx.merchant or tx.description_normalized
        note = tx.description_original
        
        # Get category config
        cat_config = config.get("categories", {}).get(tx.category, {})
        
        # Determine icon and color
        icon = cat_config.get("icon", "default")
        color = cat_config.get("color", "#808080")
        emoji = cat_config.get("emoji", "")
        
        # Determine type
        tx_type = CashewType.DEFAULT
        if tx.income:
            tx_type = CashewType.DEFAULT  # Could be "income" if supported
        
        return cls(
            account=config.get("accounts", {}).get(tx.account, "Unknown"),
            amount=amount,
            amount_unpaid=0.0,
            currency=tx.currency,
            title=title,
            note=note,
            date=tx.date,
            income=tx.income,
            type=tx_type,
            category_name=tx.category,
            subcategory_name=tx.subcategory,
            color=color,
            icon=icon,
            emoji=emoji,
            budget=config.get("defaults", {}).get("budget", ""),
            objective=config.get("defaults", {}).get("objective", ""),
            extra=config.get("defaults", {}).get("extra", ""),
        )


@dataclass
class ValidationResult:
    """Result of validating a transaction."""
    valid: bool
    errors: List[str]
    transaction: Optional[CanonicalTransaction] = None


@dataclass
class ProcessingResult:
    """Result of processing a single JSON file."""
    source_file: str
    transactions: List[CanonicalTransaction]
    validation_errors: List[Tuple[int, str]]  # (line_number, error_message)
    skipped_count: int


@dataclass
class PipelineResult:
    """Result of the entire pipeline."""
    total_transactions: int
    duplicates_removed: int
    uncategorized_count: int
    validation_errors: List[Tuple[str, int, str]]  # (file, line, error)
    files_processed: List[str]
    output_transactions: List[CanonicalTransaction]


@dataclass
class MerchantRule:
    """A single merchant matching rule."""
    name: str
    match_type: str  # exact, contains, prefix, regex
    match_value: str
    output_merchant: Optional[str] = None
    category: str = "Uncategorized"
    subcategory: Optional[str] = None
    icon: str = "default"
    color: str = "#808080"
    emoji: str = ""


@dataclass
class DuplicateInfo:
    """Information about a duplicate transaction."""
    primary: CanonicalTransaction
    duplicate: CanonicalTransaction
    match_fields: List[str]