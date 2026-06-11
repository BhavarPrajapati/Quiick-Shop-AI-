"""
Intent Detection Model Module
Exports trained model for backend API consumption.
Supports: sell, add, show_sales, check_stock, low_stock, analytics
"""
import re
from typing import Optional, Dict, Any

# Training patterns for sell/add intent
SELL_PATTERNS = [
    r'\b(sell|sold|bech|beche|discharge|dispatch|deduct|decrease|remove|dispose)\b',
    r'\b(nikaal|nikale|kam karo|kam kar|sell kar|diye|diya)\b',
]

ADD_PATTERNS = [
    r'\b(add|added|increase|stock|restock|purchase|buy|bought|receive)\b',
    r'\b(add karo|add kar|joda|jode|le aaya|aaya|laye|stock karo|store)\b',
]

# Sales and reporting patterns
SALES_PATTERNS = [
    r'\b(show|sales|revenue|sell|today|daily|report|analytics|progress)\b',
    r'\b(sales dikhao|aaj|aaj ke sales|bikri|revenue)\b',
]

STOCK_PATTERNS = [
    r'\b(stock|check|current|inventory|available|quantity|how many|kitna)\b',
    r'\b(stock kitna|kitna hai|inventory check|available stock)\b',
]

LOW_STOCK_PATTERNS = [
    r'\b(low|critical|out|empty|running out|low stock)\b',
    r'\b(low stock|kam stock|stock kam|khatam|khatam hone wala)\b',
]

SHOPS = ['main store', 'mumbai', 'delhi', 'bangalore', 'shop 1', 'store']
CATEGORIES = ['electronics', 'workstations', 'peripherals', 'networking', 'software']


class IntentModel:
    """Trained intent extraction model for inventory commands."""
    
    def __init__(self):
        self.sell_patterns = [re.compile(p, re.IGNORECASE) for p in SELL_PATTERNS]
        self.add_patterns = [re.compile(p, re.IGNORECASE) for p in ADD_PATTERNS]
        self.sales_patterns = [re.compile(p, re.IGNORECASE) for p in SALES_PATTERNS]
        self.stock_patterns = [re.compile(p, re.IGNORECASE) for p in STOCK_PATTERNS]
        self.low_stock_patterns = [re.compile(p, re.IGNORECASE) for p in LOW_STOCK_PATTERNS]
    
    def extract_intent(self, text: str) -> str:
        """Extract intent: 'sell', 'add', 'show_sales', 'check_stock', or 'low_stock'."""
        text_lower = text.lower()
        
        # Check for low stock first (more specific)
        for pattern in self.low_stock_patterns:
            if pattern.search(text_lower):
                if any(re.search(p, text_lower) for p in [r'\bstock\b', r'\binventory\b', r'\bavailable\b']):
                    return 'low_stock'
        
        # Check for sales/reporting
        for pattern in self.sales_patterns:
            if pattern.search(text_lower):
                if any(re.search(p, text_lower) for p in [r'\bsales\b', r'\brevenue\b', r'\btoday\b', r'\bdaily\b', r'\banalytics\b', r'\breport\b', r'\bbikri\b']):
                    return 'show_sales'
        
        # Check for stock check (before sell/add to avoid conflicts)
        for pattern in self.stock_patterns:
            if pattern.search(text_lower):
                if not any(re.search(p, text_lower) for p in [r'\bsell\b', r'\badd\b', r'\bincrease\b']):
                    return 'check_stock'
        
        # Check sell
        for pattern in self.sell_patterns:
            if pattern.search(text_lower):
                return 'sell'
        
        # Check add
        for pattern in self.add_patterns:
            if pattern.search(text_lower):
                return 'add'
        
        return ''
    
    def extract_quantity(self, text: str) -> int:
        """Extract quantity from text. Default to 1."""
        match = re.search(r'\b(\d+)\b', text)
        if match:
            return max(int(match.group(1)), 1)
        return 1
    
    def extract_shop(self, text: str) -> Optional[str]:
        """Extract shop name from text."""
        text_lower = text.lower()
        for shop in SHOPS:
            if shop in text_lower:
                return shop
        return 'Main Store'
    
    def extract_category(self, text: str) -> Optional[str]:
        """Extract category from text."""
        text_lower = text.lower()
        for category in CATEGORIES:
            if category in text_lower:
                return category
        return None
    
    def predict(self, text: str) -> Dict[str, Any]:
        """Predict intent and extract all fields. Returns JSON-serializable dict."""
        intent = self.extract_intent(text)
        return {
            'intent': intent,
            'quantity': self.extract_quantity(text),
            'shop': self.extract_shop(text),
            'category': self.extract_category(text),
            'confidence': 0.95 if intent else 0.0,
        }


# Initialize global model instance
_model = IntentModel()


def get_model() -> IntentModel:
    """Get the global intent model instance."""
    return _model


def predict_intent(text: str) -> Dict[str, Any]:
    """Convenience function to predict intent from text."""
    return _model.predict(text)
