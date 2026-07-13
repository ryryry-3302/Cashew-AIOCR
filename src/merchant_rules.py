"""Merchant matching using configurable rules."""

import re
from typing import Optional, List, Tuple

from models import CanonicalTransaction, MerchantRule


class MerchantMatcher:
    """Match transactions to merchants using configurable rules."""
    
    def __init__(self, rules: List[MerchantRule]):
        self.rules = rules
    
    def match(self, tx: CanonicalTransaction) -> Optional[MerchantRule]:
        """Find the best matching rule for a transaction."""
        # Get the text to match against
        match_text = tx.description_normalized.lower()
        if tx.merchant:
            match_text = tx.merchant.lower()
        
        # Try all rules and find the best match
        best_match = None
        best_score = 0
        
        for rule in self.rules:
            score = self._calculate_match_score(rule, match_text)
            if score > best_score:
                best_score = score
                best_match = rule
        
        return best_match
    
    def _calculate_match_score(self, rule: MerchantRule, text: str) -> int:
        """Calculate how well a rule matches the text."""
        match_value = rule.match_value.lower()
        
        if rule.match_type == "exact":
            if text == match_value:
                return 100
        
        elif rule.match_type == "prefix":
            if text.startswith(match_value):
                return 90
        
        elif rule.match_type == "contains":
            if match_value in text:
                return 80
        
        elif rule.match_type == "regex":
            try:
                if re.search(match_value, text, re.IGNORECASE):
                    return 70
            except re.error:
                pass
        
        return 0
    
    def apply_rule(self, tx: CanonicalTransaction, rule: MerchantRule) -> CanonicalTransaction:
        """Apply a merchant rule to a transaction."""
        # Set merchant name
        if rule.output_merchant:
            tx.merchant = rule.output_merchant
        elif tx.merchant:
            tx.merchant = rule.name
        
        # Set category
        tx.category = rule.category
        
        # Set subcategory if provided
        if rule.subcategory:
            tx.subcategory = rule.subcategory
        
        return tx


def match_transactions(
    transactions: List[CanonicalTransaction],
    matcher: MerchantMatcher
) -> Tuple[List[CanonicalTransaction], int]:
    """Match all transactions and return the count of matched transactions."""
    matched_count = 0
    
    for tx in transactions:
        rule = matcher.match(tx)
        if rule:
            matcher.apply_rule(tx, rule)
            matched_count += 1
    
    return transactions, matched_count


if __name__ == "__main__":
    # Test merchant matching
    from config import load_config
    
    config = load_config()
    rules = config.get_merchant_rules()
    matcher = MerchantMatcher(rules)
    
    test_transactions = [
        CanonicalTransaction(
            date=None,  # Not needed for this test
            description_original="VISA DEBIT GRAB*FOOD",
            description_normalized="visa debit grab*food",
            amount=10.0,
            currency="SGD",
            direction=None,  # Not needed for this test
            merchant=None,
        ),
        CanonicalTransaction(
            date=None,
            description_original="SHOPEE*ORDER123",
            description_normalized="shopee*order123",
            amount=25.0,
            currency="SGD",
            direction=None,
            merchant=None,
        ),
        CanonicalTransaction(
            date=None,
            description_original="Unknown Merchant",
            description_normalized="unknown merchant",
            amount=5.0,
            currency="SGD",
            direction=None,
            merchant=None,
        ),
    ]
    
    for tx in test_transactions:
        rule = matcher.match(tx)
        if rule:
            matcher.apply_rule(tx, rule)
            print(f"Matched: {tx.description_original} -> {tx.category}")
        else:
            print(f"No match: {tx.description_original}")
