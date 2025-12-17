# arbitrage_detection/agent.py
from typing import Dict, Any, List

from .state import ArbitrageState
from .parsers import normalize_offer, pick_best_offer

# Reuse Serper wrapper + parsing utilities from existing modules
# (preferred: import from shopping_agent.serper_client to avoid duplicating API wrapper)
from ..services.serper import serper_search

# If you already have LLM parsing helpers in anomaly_detection/parsers.py, reuse them.
# Below are placeholders you should map to your real functions.

# Simple implementations for missing functions
async def extract_canonical_product_from_query(query: str, url: str = None) -> Dict[str, Any]:
    """Extract canonical product info from query and optional URL"""
    # Simple implementation - split query into brand and name
    parts = query.split()
    return {
        "brand": parts[0] if parts else "",
        "name": " ".join(parts[1:]) if len(parts) > 1 else query,
        "size": ""  # Could be extracted from query
    }

async def extract_price_offers_from_snippets(platform: str, serper_results, pincode: str = None):
    """Extract price offers from serper search results"""
    import re

    #print("----", platform, "----")
    for result in (serper_results or [])[:3]:
        if isinstance(result, dict):
            print("title:", result.get("title"))
            print("snippet:", (result.get("snippet") or "")[:160])
        else:
            print("non-dict result:", type(result), str(result)[:120])

    offers = []
    for result in serper_results or []:
        if not isinstance(result, dict):
            continue

        title = result.get("title", "") or ""
        snippet = result.get("snippet", "") or ""
        link = result.get("link", "") or ""

        text = f"{title} {snippet}".replace(",", "")

        # Only match when currency is present (prevents matching "5 kg", "27% OFF", "8 mins")
        price_matches = re.findall(
            r"(?:₹|Rs\.?|INR)\s*(\d+(?:\.\d{1,2})?)",
            text,
            flags=re.IGNORECASE
        )

        if not price_matches:
            continue

        try:
            price = float(price_matches[0].replace(",", ""))

        except ValueError:
            continue

        offers.append({
            "platform": platform,
            "title": title,
            "product_url": link,     # rename link -> product_url
            "item_price": price,     # rename price -> item_price
            "delivery_fee": 0.0,
            "in_stock": True,
            "snippet": snippet,
        })

    return offers


#async def extract_price_offers_from_snippets(platform, serper_results, pincode=None):
    #import re
    #offers = []

    #for result in serper_results or []:
        #if not isinstance(result, dict):
           # continue

        #snippet = result.get("snippet", "") or ""
        #title = result.get("title", "") or ""
        #link = result.get("link", "") or ""

       # price_matches = re.findall(r"(?:₹\s*)?(\d[\d,]*(?:\.\d{1,2})?)", snippet)
        #if not price_matches:
         #   continue

      #  try:
       #     price = float(price_matches[0].replace(",", ""))
        #except ValueError:
         #   continue

      #  offers.append({
       #     "platform": platform,
        #    "price": price,
         #   "title": title,
          #  "link": link,
        #    "snippet": snippet
       # })

    #return offers



PLATFORMS = {
    "amazon": "site:amazon.in",
    "flipkart": "site:flipkart.com",
    "jiomart": "site:jiomart.com",
    "zepto": "site:zepto.in",
    "blinkit": "site:blinkit.com",
    "bigbasket": "site:bigbasket.com",
}

# ---------- Nodes ----------

async def node_canonicalize(state: ArbitrageState) -> ArbitrageState:
    canonical = await extract_canonical_product_from_query(state["query"], state.get("url"))
    state["canonical_product"] = canonical
    return state

async def node_platform_search(state: ArbitrageState) -> ArbitrageState:
    canonical = state["canonical_product"]
    q = f'{canonical.get("brand","")} {canonical.get("name","")} {canonical.get("size","")}'.strip()

    platform_results: Dict[str, List[Dict[str, Any]]] = {}
    for platform, site_filter in PLATFORMS.items():
        results = await serper_search(f"{q} {site_filter}")

        # defensive: force list
        platform_results[platform] = results if isinstance(results, list) else []

    state["platform_results"] = platform_results
    return state


async def node_extract_offers(state: ArbitrageState) -> ArbitrageState:
    raw_offers: List[Dict[str, Any]] = []
    for platform, results in state["platform_results"].items():
        offers = await extract_price_offers_from_snippets(platform=platform, serper_results=results, pincode=state.get("pincode"))
        raw_offers.extend(offers)
    state["raw_prices"] = raw_offers
    return state

#async def node_normalize_offers(state: ArbitrageState) -> ArbitrageState:
#    qty = state.get("quantity", 1)
#    normalized = [normalize_offer(o, quantity=qty) for o in state.get("raw_prices", [])]

    # Optional: filter to comparable offers only (variant match)
    # If you already do this in anomaly_detection, reuse that logic here.
#    comparable = [o for o in normalized if o.get("effective_price") is not None]
#    state["normalized_offers"] = comparable
#    return state

async def node_normalize_offers(state: ArbitrageState) -> ArbitrageState:
    qty = state.get("quantity", 1)
    print("raw_prices count:", len(state.get("raw_prices", [])))
    if state.get("raw_prices"):
        print("raw sample:", state["raw_prices"][0])

    normalized = [normalize_offer(o, quantity=qty) for o in state.get("raw_prices", [])]
    print("normalized sample:", normalized[0] if normalized else None)

    comparable = [o for o in normalized if o.get("effective_price") is not None]
    print("comparable count:", len(comparable))

    state["normalized_offers"] = comparable
    return state


async def node_arbitrage(state: ArbitrageState) -> ArbitrageState:
    offers = state.get("normalized_offers", [])
    best = pick_best_offer(offers)
    state["best_offer"] = best

    threshold = float(state.get("threshold_inr", 20.0))
    opportunities: List[Dict[str, Any]] = []

    if best is None:
        state["opportunities"] = []
        state["explanation"] = "No comparable offers with valid prices found."
        return state

    best_price = best["effective_price"]
    best_platform = best.get("platform")

    for o in offers:
        if o.get("platform") == best_platform:
            continue
        delta = o["effective_price"] - best_price
        if delta >= threshold:
            opportunities.append({
                "platform": o.get("platform"),
                "effective_price": o.get("effective_price"),
                "delta_vs_best": round(delta, 2),
                "best_platform": best_platform,
                "best_effective_price": round(best_price, 2),
                "product_url": o.get("product_url"),
            })

    state["opportunities"] = opportunities
    state["explanation"] = (
        f"Cheapest is {best_platform} at ₹{best_price:.2f}. "
        f"Found {len(opportunities)} platform(s) with delta ≥ ₹{threshold:.2f}."
    )
    return state


# ---------- Graph runner (simple wrapper) ----------
# If your other modules expose something like `run_shopping_agent()` or `run_graph()`,
# keep the same naming style here.

async def run_arbitrage_agent(
    query: str,
    url: str | None = None,
    pincode: str | None = None,
    quantity: int = 1,
    threshold_inr: float = 20.0,
) -> ArbitrageState:
    state: ArbitrageState = {
        "query": query,
        "url": url,
        "pincode": pincode,
        "quantity": quantity,
        "threshold_inr": threshold_inr,
    }

    # sequential pipeline (matches “nodes” even if not using compiled LangGraph object)
    state = await node_canonicalize(state)
    state = await node_platform_search(state)
    state = await node_extract_offers(state)
    state = await node_normalize_offers(state)
    state = await node_arbitrage(state)
    return state
