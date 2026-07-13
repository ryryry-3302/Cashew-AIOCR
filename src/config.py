"""Configuration loader for merchant rules, categories, and Cashew settings."""

import yaml
from pathlib import Path
from typing import Any, List

from models import MerchantRule


class Config:
    """Configuration manager that loads all YAML files."""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self._config: dict[str, Any] = {}
        self._merchant_rules: list = []
        self._load_all()
    
    def _load_all(self):
        """Load all configuration files."""
        # Load accounts
        accounts_path = self.config_dir / "accounts.yaml"
        if accounts_path.exists():
            with open(accounts_path) as f:
                self._config["accounts"] = yaml.safe_load(f) or {}
        else:
            self._config["accounts"] = {}
        
        # Load merchant rules
        rules_path = self.config_dir / "merchant_rules.yaml"
        if rules_path.exists():
            with open(rules_path) as f:
                raw_rules = yaml.safe_load(f) or {}
                self._merchant_rules = self._parse_merchant_rules(raw_rules)
        else:
            self._merchant_rules = []
        
        # Load category defaults
        cats_path = self.config_dir / "category_defaults.yaml"
        if cats_path.exists():
            with open(cats_path) as f:
                self._config["categories"] = yaml.safe_load(f) or {}
        else:
            self._config["categories"] = {}
        
        # Load accounts config
        acc_config_path = self.config_dir / "accounts.yaml"
        if acc_config_path.exists():
            with open(acc_config_path) as f:
                self._config["accounts"] = yaml.safe_load(f) or {}
        else:
            self._config["accounts"] = {}
        
        # Load Cashew defaults
        defaults_path = self.config_dir / "cashew_defaults.yaml"
        if defaults_path.exists():
            with open(defaults_path) as f:
                self._config["defaults"] = yaml.safe_load(f) or {}
        else:
            self._config["defaults"] = {
                "budget": "",
                "objective": "",
                "extra": "",
            }
    
    def _parse_merchant_rules(self, raw_rules: dict) -> List[MerchantRule]:
        """Parse merchant rules from YAML format."""
        rules = []
        for merchant_name, rule_data in raw_rules.items():
            if isinstance(rule_data, dict):
                # New format with match and output
                match_config = rule_data.get("match", {})
                output_config = rule_data.get("output", {})
                
                rule = MerchantRule(
                    name=merchant_name,
                    match_type=match_config.get("type", "contains"),
                    match_value=match_config.get("value", merchant_name.lower()),
                    output_merchant=output_config.get("merchant"),
                    category=output_config.get("category", "Uncategorized"),
                    subcategory=output_config.get("subcategory"),
                    icon=output_config.get("icon", "default"),
                    color=output_config.get("color", "#808080"),
                    emoji=output_config.get("emoji", ""),
                )
            else:
                # Old simple format: merchant -> category
                rule = MerchantRule(
                    name=merchant_name,
                    match_type="contains",
                    match_value=merchant_name.lower(),
                    category=str(rule_data),
                )
            rules.append(rule)
        return rules
    
    def get_merchant_rules(self) -> List[MerchantRule]:
        """Return all merchant matching rules."""
        return self._merchant_rules
    
    def get_account(self, institution: str) -> str:
        """Map institution to Cashew account name."""
        accounts = self._config.get("accounts", {})
        # Try exact match first, then fall back to default "_" key
        return accounts.get(institution, accounts.get("_", institution))
    
    def get_category_config(self, category: str) -> dict:
        """Get configuration for a category."""
        return self._config.get("categories", {}).get(category, {})
    
    def get_default(self, key: str) -> Any:
        """Get a default Cashew field value."""
        return self._config.get("defaults", {}).get(key, "")
    
    def get_all(self) -> dict:
        """Return the entire configuration."""
        return self._config


def load_config(config_dir: str = "config") -> Config:
    """Convenience function to load configuration."""
    return Config(config_dir)


# Default configuration templates

ACCOUNTS_TEMPLATE = """
# Map institutions to Cashew account names
# Keys are institution names from JSON files
# Values are Cashew account names

DBS: Bank
UOB: Bank
OCBC: Bank
Maybank: Bank
GrabPay: Wallet
ShopeePay: Wallet
PayNow: Wallet
"""

MERCHANT_RULES_TEMPLATE = """
# Merchant matching rules
# Each merchant can have multiple rules

# Format 1: Simple mapping (merchant -> category)
# McDonald's: Dining
# Starbucks: Dining

# Format 2: Full rule with match criteria
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

Steam:
  match:
    type: contains
    value: steam
  output:
    category: Entertainment
    icon: gamepad
    color: "#4A148C"
    emoji: "🎮"

Netflix:
  match:
    type: contains
    value: netflix
  output:
    category: Entertainment
    icon: tv
    color: "#E50914"
    emoji: "🎬"

Uber:
  match:
    type: contains
    value: uber
  output:
    category: Transport
    icon: local_taxi
    color: "#000000"
    emoji: "🚕"

Grab:
  match:
    type: contains
    value: grab
  output:
    category: Transport
    icon: local_taxi
    color: "#00B14F"
    emoji: "🚖"

Lazada:
  match:
    type: prefix
    value: lazada
  output:
    category: Shopping
    icon: shopping_cart
    color: "#FF6600"
    emoji: "🛍️"

Amazon:
  match:
    type: contains
    value: amazon
  output:
    category: Shopping
    icon: shopping_cart
    color: "#FF9900"
    emoji: "📦"

Spotify:
  match:
    type: contains
    value: spotify
  output:
    category: Entertainment
    icon: music
    color: "#1DB954"
    emoji: "🎵"

Apple:
  match:
    type: contains
    value: apple
  output:
    category: Entertainment
    icon: app_store
    color: "#A2AAAD"
    emoji: "🍎"

Google:
  match:
    type: contains
    value: google
  output:
    category: Entertainment
    icon: play_circle
    color: "#4285F4"
    emoji: "🔍"

PayNow:
  match:
    type: contains
    value: paynow
  output:
    category: Bills
    icon: credit_card
    color: "#000000"
    emoji: "💳"

Singtel:
  match:
    type: contains
    value: singtel
  output:
    category: Bills
    icon: phone
    color: "#E3001B"
    emoji: "📱"

StarHub:
  match:
    type: contains
    value: starhub
  output:
    category: Bills
    icon: phone
    color: "#000000"
    emoji: "📞"

M1:
  match:
    type: contains
    value: m1
  output:
    category: Bills
    icon: phone
    color: "#000000"
    emoji: "📲"

NTUC:
  match:
    type: contains
    value: ntuc
  output:
    category: Shopping
    icon: grocery
    color: "#006633"
    emoji: "🛒"

FairPrice:
  match:
    type: contains
    value: fairprice
  output:
    category: Shopping
    icon: grocery
    color: "#006633"
    emoji: "🥬"

ColdStorage:
  match:
    type: contains
    value: cold storage
  output:
    category: Shopping
    icon: grocery
    color: "#006633"
    emoji: "🥕"

"""

CATEGORY_DEFAULTS_TEMPLATE = """
# Category default settings for Cashew
# These apply when a category is matched but no specific icon/color is defined

Dining:
  icon: cutlery
  color: "#FF607D8B"
  emoji: "🍔"

Shopping:
  icon: shopping_cart
  color: "#FF9900"
  emoji: "🛒"

Transport:
  icon: local_taxi
  color: "#000000"
  emoji: "🚕"

Entertainment:
  icon: gamepad
  color: "#4A148C"
  emoji: "🎮"

Bills:
  icon: credit_card
  color: "#808080"
  emoji: "💳"

Income:
  icon: arrow_upward
  color: "#4CAF50"
  emoji: "💰"

Uncategorized:
  icon: default
  color: "#808080"
  emoji: ""

Transfer:
  icon: sync
  color: "#607D8B"
  emoji: "🔄"

"""

CASHEW_DEFAULTS_TEMPLATE = """
# Default values for Cashew transaction fields

budget: ""
objective: ""
extra: ""
"""


def create_default_configs(output_dir: str = "config"):
    """Create default configuration files if they don't exist."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    configs = {
        "accounts.yaml": ACCOUNTS_TEMPLATE,
        "merchant_rules.yaml": MERCHANT_RULES_TEMPLATE,
        "category_defaults.yaml": CATEGORY_DEFAULTS_TEMPLATE,
        "cashew_defaults.yaml": CASHEW_DEFAULTS_TEMPLATE,
    }
    
    for filename, content in configs.items():
        filepath = output_path / filename
        if not filepath.exists():
            with open(filepath, "w") as f:
                f.write(content)
            print(f"Created {filepath}")


if __name__ == "__main__":
    create_default_configs()
    print("Default configurations created.")
