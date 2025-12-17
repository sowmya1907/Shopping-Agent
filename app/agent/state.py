from typing import Dict, List, TypedDict

class PriceResult(TypedDict):
    platform: str
    price: float
    link: str

class AgentState(TypedDict):
    product_name: str
    category: str
    results: List[PriceResult]
