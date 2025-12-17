from .state import PriceAnomalyState
from ..services.serper import search_product
from .parser import (
    parse_product_variants,
    parse_prices_from_results,
    calculate_unit_prices
)

# ✅ REMOVE async - make it synchronous

def product_discovery_node(state: PriceAnomalyState) -> PriceAnomalyState:
    """
    For each product, search on Serper to validate and get variants
    """
    for product in state["products"]:
        # Use platform or fallback to a generic product name
        product_name = product.get('platform', product.get('name', 'product'))
        query = f"best selling {product_name}"
        results = search_product(query)
        state["search_results"] = results

    return state


def variant_discovery_node(state: PriceAnomalyState) -> PriceAnomalyState:
    """
    Discover pack sizes/denominations per product
    """
    for product in state["products"]:
        product_name = product.get('platform', product.get('name', 'product'))
        query = f"{product_name} 100ml 200ml 500ml 1L sizes"
        results = search_product(query)
        variants = parse_product_variants(product_name, results)
        state["variants"][product_name] = variants

    return state


def price_collection_node(state: PriceAnomalyState) -> PriceAnomalyState:
    """
    Collect prices from 6-7 e-commerce sites
    """
    for product_name, variants in state["variants"].items():
        for variant in variants:
            variant_id = f"{product_name}_{variant['size']}{variant['unit']}"
            query = f"{product_name} {variant['size']}{variant['unit']} price buy online"
            results = search_product(query)
            prices = parse_prices_from_results(results)
            state["prices"][variant_id] = prices
    
    return state


def normalization_node(state: PriceAnomalyState) -> PriceAnomalyState:
    """
    Calculate unit prices
    """
    for product_name, variants in state["variants"].items():
        for variant in variants:
            variant_id = f"{product_name}_{variant['size']}{variant['unit']}"
            
            if variant_id in state["prices"]:
                prices = state["prices"][variant_id]
                size = variant["size"]
                unit_prices = calculate_unit_prices(prices, size)
                state["unit_prices"][variant_id] = unit_prices
    
    return state


def anomaly_detection_node(state: PriceAnomalyState) -> PriceAnomalyState:
    """
    Detect price outliers using pure logic (no LLM)
    """
    THRESHOLD = 0.1  # 10%
    
    for variant_id, unit_prices in state["unit_prices"].items():
        if not unit_prices:
            continue
        
        avg_price = sum(unit_prices.values()) / len(unit_prices)
        
        for site, price in unit_prices.items():
            percentage_above = (price / avg_price) - 1
            
            if percentage_above > THRESHOLD:
                state["anomalies"].append({
                    "product": variant_id,
                    "site": site,
                    "unit_price": price,
                    "average_price": avg_price,
                    "flag": f"{percentage_above*100:.1f}% above average ⚠️"
                })
    
    return state
