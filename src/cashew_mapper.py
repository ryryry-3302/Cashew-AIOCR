"""Map canonical transactions to Cashew format."""

from typing import List, Optional

from .models import CanonicalTransaction, CashewTransaction, CashewType


class CashewMapper:
    """Map canonical transactions to Cashew format."""
    
    def __init__(self, config: dict, account: Optional[str] = None):
        self.config = config
        self.account = account  # Override account if provided
    
    def map(self, tx: CanonicalTransaction) -> CashewTransaction:
        """Map a single canonical transaction to Cashew format."""
        # Determine amount
        amount = tx.amount_signed
        
        # Determine title and note
        title = tx.merchant or tx.description_normalized
        note = tx.description_original
        
        # Get category config
        cat_config = self.config.get("categories", {}).get(tx.category, {})
        
        # Determine icon and color
        icon = cat_config.get("icon", "default")
        color = cat_config.get("color", "#808080")
        emoji = cat_config.get("emoji", "")
        
        # Determine type
        tx_type = CashewType.DEFAULT
        
        # Use overridden account if provided, otherwise use config lookup
        if self.account:
            account_name = self.account
        else:
            accounts = self.config.get("accounts", {})
            account_name = accounts.get(tx.account, accounts.get("_", "Unknown"))
        
        return CashewTransaction(
            account=account_name,
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
            budget=self.config.get("defaults", {}).get("budget", ""),
            objective=self.config.get("defaults", {}).get("objective", ""),
            extra=self.config.get("defaults", {}).get("extra", ""),
        )
    
    def map_all(self, transactions: List[CanonicalTransaction]) -> List[CashewTransaction]:
        """Map all transactions."""
        return [self.map(tx) for tx in transactions]


if __name__ == "__main__":
    # Test mapping
    from datetime import date
    from models import Direction
    
    tx = CanonicalTransaction(
        date=date(2024, 1, 15),
        description_original="VISA DEBIT GRAB*FOOD",
        description_normalized="visa debit grab*food",
        amount=10.0,
        currency="SGD",
        direction=Direction.DEBIT,
        merchant="Grab Food",
        category="Dining",
        account="DBS",
    )
    
    config = {
        "accounts": {"DBS": "Bank"},
        "categories": {
            "Dining": {"icon": "cutlery", "color": "#FF607D8B", "emoji": "🍔"}
        },
        "defaults": {"budget": "", "objective": "", "extra": ""},
    }
    
    mapper = CashewMapper(config)
    cashew_tx = mapper.map(tx)
    
    print(f"Title: {cashew_tx.title}")
    print(f"Amount: {cashew_tx.amount}")
    print(f"Category: {cashew_tx.category_name}")
    print(f"Icon: {cashew_tx.icon}")
    print(f"Emoji: {cashew_tx.emoji}")
