from langchain_openai import ChatOpenAI
import re
import json

def get_llm():
    """Lazy initialization of LLM to avoid import-time errors"""
    if not hasattr(get_llm, '_llm'):
        get_llm._llm = ChatOpenAI(model_name="gpt-4")
    return get_llm._llm

# llm = ChatOpenAI(model_name="gpt-4")  # Remove this line

# PARSER 1: Extract variants (pack sizes)
def parse_product_variants(product_name: str, search_results: list[dict]) -> list[dict]:
    """
    Extract size variants from search results
    Input: [{"title": "...", "snippet": "...", "link": "..."}]
    Output: [{"size": 100, "unit": "ml"}, {"size": 200, "unit": "ml"}]
    """
    # LLM extracts sizes
    snippets_text = "\n".join([r.get("snippet", "") for r in search_results])
    
    prompt = f"""
    Extract all size/pack variants from these snippets for {product_name}:
    {snippets_text}
    
    Return JSON: [{{"size": 100, "unit": "ml"}}, {{"size": 200, "unit": "ml"}}]
    Only return JSON array, nothing else.
    """
    
    response = get_llm().predict(prompt)
    try:
        return json.loads(response)
    except:
        return []

# PARSER 2: Extract prices (DETERMINISTIC - no LLM)
def parse_prices_from_results(search_results: list[dict]) -> dict:
    """
    Extract prices from e-commerce snippets
    Uses REGEX only (deterministic, no LLM)
    Input: [{"snippet": "Price: $99.99", "link": "..."}]
    Output: {"amazon.com": 99.99, "flipkart.com": 98.50}
    """
    prices = {}
    
    for result in search_results:
        snippet = result.get("snippet", "")
        link = result.get("link", "")
        
        # Extract price using regex
        price_match = re.search(r'\$(\d+(?:\.\d{2})?)', snippet)
        
        if price_match:
            price = float(price_match.group(1))
            domain = extract_domain(link)
            prices[domain] = price
    
    return prices

# PARSER 3: Normalize unit prices
def calculate_unit_prices(prices: dict, variant_size: float) -> dict:
    """
    Convert: price per unit = total_price / size
    Input: {"amazon.com": 99.99}, variant_size=100
    Output: {"amazon.com": 0.9999}  # per ml
    """
    return {site: price / variant_size for site, price in prices.items()}

# HELPER
def extract_domain(url: str) -> str:
    """Extract domain from URL"""
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc
    except:
        return url
