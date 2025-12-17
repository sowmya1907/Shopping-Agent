from typing import TypedDict

class PriceAnomalyState(TypedDict):
    category: str
    products: list[dict]           # Input from shopping agent
    variants: dict[str, list]      # {product_name: [variant1, variant2]}
    prices: dict[str, dict]        # {variant_id: {site: price}}
    unit_prices: dict[str, dict]   # {variant_id: {site: unit_price}}
    anomalies: list[dict]          # Output: detected anomalies
