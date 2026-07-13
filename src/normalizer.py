"""Transaction description normalization."""

import re
from typing import Optional, List

from models import CanonicalTransaction


class DescriptionNormalizer:
    """Normalize transaction descriptions for better merchant matching."""
    
    def __init__(self):
        # Patterns to remove
        self.patterns = [
            # Remove transaction IDs (e.g., TXN123456, REF789)
            (r'\b(?:TXN|TX|REF|REF#|ID|ID#)\d{6,}\b', ''),
            # Remove terminal numbers (e.g., TELLER123, POS456)
            (r'\b(?:TELLER|POS|TERMINAL)\d+\b', ''),
            # Remove authorization codes (e.g., AUTH123456)
            (r'\bAUTH\d{6,}\b', ''),
            # Remove batch numbers
            (r'\bBATCH\d+\b', ''),
            # Remove sequence numbers
            (r'\bSEQ\d+\b', ''),
            # Remove multiple asterisks
            (r'\*+', '*'),
            # Remove multiple spaces
            (r'\s+', ' '),
            # Remove leading/trailing whitespace
            (r'^\s+|\s+$', ''),
        ]
    
    def normalize(self, description: str) -> str:
        """Normalize a transaction description."""
        if not description:
            return ""
        
        normalized = str(description)
        
        # Apply all patterns
        for pattern, replacement in self.patterns:
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        
        # Normalize capitalization - title case for better matching
        # But preserve known patterns like "VISA", "MC", etc.
        normalized = self._preserve_acronyms(normalized)
        
        return normalized.strip()
    
    def _preserve_acronyms(self, text: str) -> str:
        """Preserve common acronyms while normalizing the rest."""
        acronyms = [
            'VISA', 'MC', 'AMEX', 'DISCOVER', 'DINERS', 'JCB',
            'POS', 'ATM', 'EFT', 'ACH', 'DEBIT', 'CREDIT',
            'PAYPAL', 'PAYTM', 'UPI', 'QR', 'NFC', 'RFID'
        ]
        
        result = text
        for acronym in acronyms:
            # Replace lowercase version with uppercase
            result = re.sub(r'\b' + acronym.lower() + r'\b', acronym, result)
        
        return result
    
    def extract_merchant(self, description: str, normalized: str) -> Optional[str]:
        """Extract merchant name from description."""
        # Common prefixes to strip
        prefixes = [
            'VISA DEBIT', 'VISA CREDIT', 'MC DEBIT', 'MC CREDIT',
            'AMEX DEBIT', 'AMEX CREDIT', 'PAYPAL', 'PAYTM',
            'GRABPAY', 'SHOPEEPAY', 'APPLE PAY', 'GOOGLE PAY',
            'SAMSUNG PAY', 'NETFLIX', 'SPOTIFY', 'UBER',
            'LYFT', 'AIRBNB', 'AMAZON', 'EBAY', 'ALIBABA'
        ]
        
        result = normalized
        
        for prefix in prefixes:
            if result.upper().startswith(prefix):
                result = result[len(prefix):].strip()
                break
        
        # Remove trailing asterisks and extra text
        result = result.split('*')[0].strip()
        
        return result if result else None


def normalize_transaction(tx: CanonicalTransaction, normalizer: DescriptionNormalizer) -> CanonicalTransaction:
    """Normalize a transaction's description and extract merchant."""
    original = tx.description_original
    normalized = normalizer.normalize(original)
    merchant = normalizer.extract_merchant(original, normalized)
    
    tx.description_normalized = normalized
    tx.merchant = merchant
    
    return tx


def normalize_transactions(transactions: List[CanonicalTransaction], normalizer: DescriptionNormalizer) -> List[CanonicalTransaction]:
    """Normalize a transaction's description and extract merchant."""
    original = tx.description_original
    normalized = normalizer.normalize(original)
    merchant = normalizer.extract_merchant(original, normalized)
    
    tx.description_normalized = normalized
    tx.merchant = merchant
    
    return tx


if __name__ == "__main__":
    # Test normalization
    normalizer = DescriptionNormalizer()
    
    test_cases = [
        "VISA DEBIT 1234 GRAB*FOOD SG",
        "Grab Food",
        "GrabFood",
        "SHOPEE*ORDER123456",
        "McDonald's Restaurant",
        "UBER*TRIP789",
        "NETFLIX.COM",
        "SPOTIFY PREMIUM",
    ]
    
    for desc in test_cases:
        normalized = normalizer.normalize(desc)
        merchant = normalizer.extract_merchant(desc, normalized)
        print(f"Original: {desc}")
        print(f"  Normalized: {normalized}")
        print(f"  Merchant: {merchant}")
        print()
