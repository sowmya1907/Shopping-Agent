from .state import AgentState
from ..services.serper import search_product
from ..services.parser import extract_price

PLATFORMS = {
    "Amazon": "site:amazon.in",
    "Flipkart": "site:flipkart.com",
    "Blinkit": "site:blinkit.com",
    "Zepto": "site:zepto.in",
    "BigBasket": "site:bigbasket.com"
}

def price_search_node(state: AgentState, platform: str):
    query = f"{state['product_name']} {PLATFORMS[platform]}"
    data = search_product(query)

    for result in data.get("organic", []):
        price = extract_price(result.get("snippet", ""))
        if price:
            state["results"].append({
                "platform": platform,
                "price": price,
                "link": result.get("link")
            })
            break

    return state
