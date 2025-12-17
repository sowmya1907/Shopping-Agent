import gradio as gr
import requests
import json
import pandas as pd

MASTER_CATEGORIES = ["grocery", "electronics", "fashion", "beauty"]

CATEGORIES_BY_MASTER = {
    "grocery": ["Rice", "Atta", "Detergent", "Oil"],
    "electronics": ["Mobiles", "Laptops", "Headphones", "Smartwatches"],
    "fashion": ["Men Clothing", "Women Clothing", "Footwear", "Watches", "Bags"],
    "beauty": ["Skincare", "Haircare", "Makeup", "Fragrance", "Personal Care"],
}

PRODUCTS_BY_CATEGORY = {
    # Grocery
    "Rice": ["India Gate Basmati Rice", "Daawat Basmati Rice"],
    "Atta": ["Aashirvaad Atta", "Pillsbury Chakki Fresh Atta"],
    "Detergent": ["Surf Excel", "Ariel Matic"],
    "Oil": ["Fortune Sunflower Oil", "Saffola Gold"],
    # Electronics
    "Mobiles": ["Samsung Galaxy M14 5G", "Redmi Note 13", "iPhone 13"],
    "Laptops": ["HP Pavilion 14", "Dell Inspiron 15", "Lenovo IdeaPad Slim 3"],
    "Headphones": ["boAt Rockerz 450", "Sony WH-CH520", "JBL Tune 760NC"],
    "Smartwatches": ["Noise ColorFit", "boAt Xtend", "Amazfit Bip"],
    # Fashion
    "Men Clothing": ["Levi's Men's Jeans", "Allen Solly Men's Shirt", "Puma Men's T-Shirt"],
    "Women Clothing": ["Biba Kurti", "W for Women Top", "Only Women's Jeans"],
    "Footwear": ["Bata Sneakers", "Puma Running Shoes", "Adidas Slides"],
    "Watches": ["Fastrack Watch", "Titan Watch", "Casio Watch"],
    "Bags": ["American Tourister Backpack", "Wildcraft Backpack", "Skybags Backpack"],
    # Beauty
    "Skincare": ["Cetaphil Gentle Skin Cleanser", "Nivea Soft Cream", "Minimalist Sunscreen SPF 50"],
    "Haircare": ["L'Oréal Shampoo", "Dove Shampoo", "Mamaearth Hair Oil"],
    "Makeup": ["Maybelline Mascara", "Lakmé Compact", "Sugar Lipstick"],
    "Fragrance": ["Fogg Scent", "Engage Perfume Spray", "Denver Hamilton"],
    "Personal Care": ["Colgate Toothpaste", "Nivea Deodorant", "Dettol Handwash"],
}

API_URL = "http://127.0.0.1:8000/compare"
ANOMALY_API_URL = "http://127.0.0.1:8000/detect-anomalies"  # 🆕 NEW
ARBITRAGE_API_URL = "http://127.0.0.1:8000/platform-arbitrage"



# ==================== TAB 1: EXISTING PRICE COMPARISON ====================
def fetch_prices(master_category, category, product_name):
    """Existing function - keep as-is"""
    if not master_category or not category or not product_name:
        return [], "[]"

    response = requests.post(
        API_URL,
        params={
            "master_category": master_category,
            "category": category,
            "product_name": product_name,
        },
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()

    if isinstance(data, dict) and "error" in data:
        return [["Error", data["error"], ""]], json.dumps({"error": data["error"]})

    # Ensure data is a list before processing
    if not isinstance(data, list):
        return [["Error", "Invalid response format", ""]], json.dumps({"error": "Invalid response format"})

    # Return both table format and JSON format
    table_data = [[r.get("platform", "Unknown"), r.get("price", "N/A"), r.get("link", "")] for r in data]
    json_data = json.dumps(data, indent=2)
    return table_data, json_data


# 🆕 NEW FUNCTION FOR TAB 2: ANOMALY DETECTION
def detect_anomalies(products_json_str):
    """
    Detect price anomalies from product JSON
    Input: JSON string from tab 1
    Output: Analysis report
    """
    if not products_json_str or products_json_str.strip() == "":
        return "⚠️ Please paste products JSON from Tab 1"
    
    try:
        # Parse JSON
        products = json.loads(products_json_str)
        
        if not isinstance(products, list):
            return "❌ JSON must be an array of products"
        
        if not products:
            return "⚠️ Products list is empty"
        
        # Call anomaly detection API
        response = requests.post(
            ANOMALY_API_URL,
            json=products,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        
        # Format response
        if data.get("status") == "error":
            return f"❌ Error: {data.get('error', 'Unknown error')}"
        
        anomalies = data.get("anomalies", [])
        total_flagged = data.get("total_flagged", 0)
        
        if not anomalies:
            return "✅ GOOD NEWS!\nNo price anomalies detected.\nAll prices are within normal range (±10% of average)."
        
        # Format anomalies report
        output = f"⚠️ PRICE ANOMALIES DETECTED ({total_flagged} found):\n\n"
        
        for i, anomaly in enumerate(anomalies, 1):
            output += f"🚨 Anomaly #{i}\n"
            output += f"   Product: {anomaly.get('product', 'N/A')}\n"
            output += f"   Site: {anomaly.get('site', 'N/A')}\n"
            output += f"   Unit Price: ${anomaly.get('unit_price', 0):.2f}\n"
            output += f"   Average: ${anomaly.get('average_price', 0):.2f}\n"
            output += f"   Status: {anomaly.get('flag', 'N/A')}\n"
            output += "   " + "-"*40 + "\n\n"
        
        return output
    
    except json.JSONDecodeError:
        return "❌ Invalid JSON format.\n\nHow to use:\n1. Go to Tab 1\n2. Search for products\n3. Copy the results table data\n4. Paste here as JSON"
    except requests.exceptions.ConnectionError:
        return "🔌 Cannot connect to anomaly detection server.\nMake sure FastAPI is running on port 8000"
    except Exception as e:
        return f"❌ Error: {str(e)}"
    
#Arbritrage detection function tab3

def detect_platform_arbitrage(query, url, pincode, quantity, threshold_inr):
    """
    Calls FastAPI /platform-arbitrage (your async arbitrage agent).
    Returns: best_offer text, explanation text, offers table, opportunities JSON
    """
    if not query and not url:
        return "⚠️ Provide query or URL", "", [], []

    payload = {
    "query": query.strip() if isinstance(query, str) else "",
    "url": url.strip() if isinstance(url, str) and url.strip() else None,
    "pincode": pincode.strip() if isinstance(pincode, str) and pincode.strip() else None,
    "quantity": int(quantity) if quantity else 1,
    "threshold_inr": float(threshold_inr) if threshold_inr is not None else 20.0,
}

    try:
        r = requests.post(ARBITRAGE_API_URL, json=payload, timeout=120)
        r.raise_for_status()
        data = r.json()

        best_offer = data.get("best_offer") or {}
        best_text = (
            f"{best_offer.get('platform', 'N/A')} @ ₹{best_offer.get('effective_price', 'N/A')}"
            if best_offer else "No best offer found."
        )

        offers = data.get("normalized_offers", []) or []
        table_data = [[
            o.get("platform", ""),
            o.get("title", ""),
            o.get("item_price", ""),
            o.get("delivery_fee", ""),
            o.get("effective_price", ""),
            o.get("in_stock", ""),
            o.get("product_url", ""),
        ] for o in offers]

        opportunities = data.get("opportunities", []) or []
        explanation = data.get("explanation", "")

        return best_text, explanation, table_data, opportunities

    except requests.exceptions.ConnectionError:
        return "🔌 Cannot connect to server. Start FastAPI on port 8000.", "", [], []
    except Exception as e:
        return f"❌ Error: {str(e)}", "", [], []




# ==================== BUILD GRADIO INTERFACE ====================
def build_demo():
    with gr.Blocks(title="Shopping Agent - Price Comparison & Anomaly Detection") as demo:
        gr.Markdown("# 🛒 Shopping Agent - Price Comparison & Anomaly Detection")
        
        with gr.Tabs():
            # 📌 TAB 1: EXISTING PRICE COMPARISON (KEEP AS-IS)
            with gr.Tab("💰 Find Best Price"):
                gr.Markdown("Search products and compare prices across platforms")
                
                master = gr.Dropdown(MASTER_CATEGORIES, label="Master Category", value="grocery")
                category = gr.Dropdown([], label="Category")
                product_dropdown = gr.Dropdown([], label="Product (dropdown)", allow_custom_value=True)
                product_text = gr.Textbox(label="Product (type here)", placeholder="Type any product name...")
                
                with gr.Row():
                    output = gr.Dataframe(headers=["Platform", "Price", "Link"])
                    json_output = gr.Textbox(
                        label="Results as JSON",
                        lines=25,
                        interactive=False,
                        show_copy_button=True
                    )
                
                def set_categories(master_val):
                    cats = CATEGORIES_BY_MASTER.get(master_val, [])
                    return gr.Dropdown(choices=cats, value=(cats[0] if cats else None))

                def set_products(cat_val):
                    items = PRODUCTS_BY_CATEGORY.get(cat_val, [])
                    return gr.Dropdown(choices=items, value=(items[0] if items else None))

                master.change(set_categories, master, category)
                category.change(set_products, category, product_dropdown)

                def pick_product(typed, selected):
                    if typed and isinstance(typed, str) and typed.strip():
                        return typed.strip()
                    return selected

                btn = gr.Button("Find Best Price")
                btn.click(
                    fn=lambda m, c, pd, pt: fetch_prices(m, c, pick_product(pt, pd)),
                    inputs=[master, category, product_dropdown, product_text],
                    outputs=[output, json_output],
                )
            
            # 🆕 TAB 2: NEW ANOMALY DETECTION
            with gr.Tab("🔍 Detect Price Anomalies"):
                gr.Markdown("""
                ### Detect Price Anomalies
                
                **How to use:**
                1. Go to "Find Best Price" tab and search for products
                2. Copy the results (as JSON)
                3. Paste them below
                4. Click "Detect Anomalies" to find price outliers
                """)
                
                products_input = gr.Textbox(
                    label="Paste Products JSON",
                    placeholder='[{"platform": "amazon", "price": 999, ...}, ...]',
                    lines=20,
                    info="Copy from Tab 1 results"
                )
                
                anomaly_output = gr.Textbox(
                    label="Anomaly Analysis",
                    lines=30,
                    interactive=False
                )
                
                anomaly_btn = gr.Button("🔍 Detect Anomalies", variant="primary")
                anomaly_btn.click(
                    fn=detect_anomalies,
                    inputs=products_input,
                    outputs=anomaly_output
                )

            # 🆕 TAB 3: PLATFORM-TO-PLATFORM ARBITRAGE
            with gr.Tab("📈 Platform Arbitrage"):
                gr.Markdown("""
                ### Platform-to-Platform Price Arbitrage
                Compare the same product across platforms and highlight where you can save money.
    
                **How to use:**
                - Enter a product query (recommended), or paste a product URL.
                - Optionally set pincode, quantity and threshold.
                - Click "Check Arbitrage".
            """)

                arb_query = gr.Textbox(
                label="Product query",
                placeholder="e.g., 'Aashirvaad Atta 5kg'"
                )
                arb_url = gr.Textbox(
                label="Or product URL (optional)",
                placeholder="https://..."
                )
                arb_pincode = gr.Textbox(label="Pincode (optional)")

                with gr.Row():
                    arb_quantity = gr.Number(label="Quantity", value=1, precision=0)
                    arb_threshold = gr.Number(label="Threshold (₹)", value=20, precision=0)

                arb_btn = gr.Button("📈 Check Arbitrage", variant="primary")

                arb_best = gr.Textbox(label="Best offer")
                arb_explanation = gr.Textbox(label="Explanation", lines=2)

                arb_offers = gr.Dataframe(
                    headers=["Platform", "Title", "Item Price", "Delivery Fee", "Effective Price", "In Stock", "URL"],
                    interactive=False,
                    label="Normalized Offers")

                arb_opps = gr.JSON(label="Opportunities")

                arb_btn.click(
                    fn=detect_platform_arbitrage,
                    inputs=[arb_query, arb_url, arb_pincode, arb_quantity, arb_threshold],
                    outputs=[arb_best, arb_explanation, arb_offers, arb_opps],
                )
   

    return demo

demo = build_demo()

