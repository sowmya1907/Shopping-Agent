# arbitrage_detection/parsers.py
from typing import Any, Dict, List, Optional

def compute_effective_price(item_price: Optional[float], delivery_fee: Optional[float]) -> Optional[float]:
    if item_price is None:
        return None
    return float(item_price) + float(delivery_fee or 0.0)

def normalize_offer(offer: Dict[str, Any], quantity: int = 1) -> Dict[str, Any]:
    """
    Expected offer fields (keep aligned with your other modules):
    {platform, title, product_url, item_price, delivery_fee, in_stock, seller, ...}
    """
    item_price = offer.get("item_price")
    delivery_fee = offer.get("delivery_fee", 0.0)

    eff = compute_effective_price(item_price, delivery_fee)
    if eff is not None:
        eff *= max(int(quantity), 1)

    out = dict(offer)
    out["effective_price"] = eff
    out["quantity"] = max(int(quantity), 1)
    return out

def pick_best_offer(offers: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    priced = [o for o in offers if o.get("effective_price") is not None]
    if not priced:
        return None
    return min(priced, key=lambda x: x["effective_price"])
