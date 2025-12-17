# arbitrage_detection/state.py
from typing import Dict, List, Optional, TypedDict, Any

class ArbitrageState(TypedDict, total=False):
    # input
    query: str
    url: Optional[str]
    pincode: Optional[str]
    quantity: int
    threshold_inr: float

    # canonical product representation (output of your existing LLM parsing style)
    canonical_product: Dict[str, Any]   # {brand, name, size, unit, variant...}

    # gathered data
    platform_results: Dict[str, List[Dict[str, Any]]]   # serper results per platform
    raw_prices: List[Dict[str, Any]]                    # extracted raw offers
    normalized_offers: List[Dict[str, Any]]             # comparable offers only

    # arbitrage output
    best_offer: Optional[Dict[str, Any]]
    opportunities: List[Dict[str, Any]]
    explanation: str
