from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional, Any, Dict, List
from fastapi import Request, Form
from fastapi.responses import HTMLResponse

from dotenv import load_dotenv
import os

from gradio import mount_gradio_app
from app.ui.gradio_ui import demo, MASTER_CATEGORIES, CATEGORIES_BY_MASTER

load_dotenv()
print("SERPER loaded:", bool(os.getenv("SERPER_API_KEY")))

app = FastAPI()


@app.on_event("startup")
async def startup_event():
    print("Startup event called")


# -------------------------
# Initialize graph lazily
# -------------------------
graph = None

def get_graph():
    global graph
    if graph is None:
        from app.agent.graph import build_graph
        graph = build_graph()
    return graph


# -------------------------
# API: Price comparison
# -------------------------
@app.post("/compare")
def compare_prices(master_category: str, category: str, product_name: str):
    # Validation
    if master_category not in MASTER_CATEGORIES:
        raise HTTPException(status_code=400, detail="Invalid master_category")

    if category not in CATEGORIES_BY_MASTER.get(master_category, []):
        raise HTTPException(status_code=400, detail="Invalid category for master_category")

    if not product_name or not product_name.strip():
        raise HTTPException(status_code=400, detail="product_name cannot be empty")

    state = {
        "master_category": master_category,
        "category": category,
        "product_name": product_name.strip(),
        "results": [],
    }

    try:
        final_state = get_graph().invoke(state)
        results = final_state.get("results", [])
        # Sort by numeric price when possible
        def sort_key(x):
            p = x.get("price")
            return p if isinstance(p, (int, float)) else float("inf")

        return sorted(results, key=sort_key)
    except Exception as e:
        # keep it JSON for the UI
        return {"error": f"Failed to fetch prices: {str(e)}"}


# -------------------------
# API: Anomaly detection
# -------------------------
@app.post("/detect-anomalies")
def detect_price_anomalies(products: List[Dict[str, Any]]):
    """Detect price anomalies in products"""
    try:
        if not products:
            return {"status": "error", "anomalies": []}

        platform_prices: Dict[str, List[float]] = {}
        for product in products:
            platform = product.get("platform", "unknown")
            price = product.get("price")
            if isinstance(price, (int, float)):
                platform_prices.setdefault(platform, []).append(float(price))

        all_prices: List[float] = []
        for prices in platform_prices.values():
            all_prices.extend(prices)

        if not all_prices:
            return {"status": "error", "anomalies": [], "error": "No valid prices found"}

        avg_price = sum(all_prices) / len(all_prices)

        anomalies = []
        THRESHOLD = 0.10  # 10%

        for product in products:
            platform = product.get("platform", "unknown")
            price = product.get("price")
            link = product.get("link", "")

            if isinstance(price, (int, float)) and avg_price > 0:
                percentage_above = (float(price) / avg_price) - 1
                if percentage_above > THRESHOLD:
                    anomalies.append({
                        "product": f"Product from {platform}",
                        "site": platform,
                        "unit_price": float(price),
                        "average_price": avg_price,
                        "link": link,
                        "flag": f"{percentage_above*100:.1f}% above average",
                    })

        return {
            "status": "success",
            "anomalies": anomalies,
            "total_flagged": len(anomalies)
        }
    except Exception as e:
        return {"status": "error", "anomalies": [], "error": str(e)}


# -------------------------
# API: Arbitrage detection
# -------------------------
class ArbitrageRequest(BaseModel):
    query: str
    url: Optional[str] = None
    pincode: Optional[str] = None
    quantity: int = 1
    threshold_inr: float = 20.0


@app.post("/platform-arbitrage")
async def platform_arbitrage(req: ArbitrageRequest) -> Dict[str, Any]:
    from app.arbitrage_detection.agent import run_arbitrage_agent

    final_state = await run_arbitrage_agent(
        query=req.query,
        url=req.url,
        pincode=req.pincode,
        quantity=req.quantity,
        threshold_inr=req.threshold_inr,
    )
    return {
        "canonical_product": final_state.get("canonical_product", {}),
        "best_offer": final_state.get("best_offer"),
        "opportunities": final_state.get("opportunities", []),
        "normalized_offers": final_state.get("normalized_offers", []),
        "explanation": final_state.get("explanation", ""),
    }


# -------------------------
# PWA manifest (optional)
# -------------------------
@app.get("/manifest.json")
def manifest():
    return {
        "name": "Shopping Agent",
        "short_name": "ShopAgent",
        "description": "Find the best prices for products",
        "start_url": "/gradio",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#000000",
    }

USERNAME = os.getenv("APP_USER", "admin")
PASSWORD = os.getenv("APP_PASS", "admin123")
SESSION_COOKIE = "shopagent_session"
SESSION_VALUE = "ok"  # simple flag

@app.get("/login", response_class=HTMLResponse)
def login_page():
    return """
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Shopping Agent Login</title>
      <style>
        :root{
          --bg1:#0f172a;   /* slate-900 */
          --bg2:#111827;   /* gray-900 */
          --card:#0b1220cc;
          --accent:#ff6a00;
          --text:#e5e7eb;
          --muted:#9ca3af;
          --border:#243244;
        }
        *{ box-sizing:border-box; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial; }
        body{
          margin:0;
          min-height:100vh;
          display:flex;
          align-items:center;
          justify-content:center;
          color:var(--text);
          background:
            linear-gradient(135deg, var(--bg1), var(--bg2));
        }
        .wrap{
          width:min(960px, 92vw);
          display:grid;
          grid-template-columns: 1.1fr 0.9fr;
          gap:20px;
          align-items:stretch;
        }
        .hero{
          border:1px solid var(--border);
          border-radius:18px;
          overflow:hidden;
          background:#000;
          position:relative;
          min-height:380px;
        }
        .hero img{
          width:100%;
          height:100%;
          object-fit:cover;
          opacity:0.85;
          display:block;
        }
        .hero .overlay{
          position:absolute;
          inset:0;
          background:linear-gradient(180deg, rgba(0,0,0,0.25), rgba(0,0,0,0.75));
          padding:22px;
          display:flex;
          flex-direction:column;
          justify-content:flex-end;
        }
        .hero h1{ margin:0 0 6px; font-size:26px; }
        .hero p{ margin:0; color:var(--muted); line-height:1.4; }

        .card{
          border:1px solid var(--border);
          border-radius:18px;
          background:var(--card);
          backdrop-filter: blur(10px);
          padding:22px;
          min-height:380px;
          display:flex;
          flex-direction:column;
          justify-content:center;
        }
        .brand{
          display:flex;
          align-items:center;
          gap:10px;
          margin-bottom:16px;
        }
        .badge{
          width:40px; height:40px;
          border-radius:12px;
          background: linear-gradient(135deg, #ff6a00, #ff2d55);
          display:flex; align-items:center; justify-content:center;
          font-weight:800;
        }
        .brand h2{ margin:0; font-size:18px; }
        .field{ margin:10px 0; }
        label{ display:block; font-size:12px; color:var(--muted); margin-bottom:6px; }
        input{
          width:100%;
          padding:12px 12px;
          border-radius:12px;
          border:1px solid var(--border);
          background:#0b1220;
          color:var(--text);
          outline:none;
        }
        input:focus{ border-color: var(--accent); box-shadow:0 0 0 3px rgba(255,106,0,0.18); }
        button{
          width:100%;
          margin-top:12px;
          padding:12px 14px;
          border:none;
          border-radius:12px;
          background: var(--accent);
          color:#111;
          font-weight:700;
          cursor:pointer;
        }
        button:hover{ filter:brightness(1.05); }
        .hint{
          margin-top:12px;
          font-size:12px;
          color:var(--muted);
          text-align:center;
        }

        @media (max-width: 820px){
          .wrap{ grid-template-columns:1fr; }
          .hero{ min-height:220px; }
          .card{ min-height:auto; }
        }
      </style>
    </head>
    <body>
      <div class="wrap">
        <div class="hero">
          <img src="https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?auto=format&fit=crop&w=1400&q=60" alt="Shopping" />
          <div class="overlay">
            <h1>Shopping Agent</h1>
            <p>Compare prices, detect anomalies, and find arbitrage opportunities across platforms.</p>
          </div>
        </div>

        <div class="card">
          <div class="brand">
            <div class="badge">SA</div>
            <h2>Login</h2>
          </div>

          <form method="post" action="/login">
            <div class="field">
              <label>Username</label>
              <input name="username" placeholder="Enter username" required />
            </div>
            <div class="field">
              <label>Password</label>
              <input name="password" type="password" placeholder="Enter password" required />
            </div>
            <button type="submit">Sign in</button>
          </form>

          <div class="hint">Tip: credentials come from APP_USER / APP_PASS in your .env</div>
        </div>
      </div>
    </body>
    </html>
    """


@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    if username == USERNAME and password == PASSWORD:
        resp = RedirectResponse(url="/gradio", status_code=303)
        resp.set_cookie(SESSION_COOKIE, SESSION_VALUE, httponly=True)
        return resp
    return HTMLResponse("<h3>Invalid credentials</h3><a href='/login'>Try again</a>", status_code=401)

@app.middleware("http")
async def protect_gradio(request: Request, call_next):
    path = request.url.path

    # allow login + docs + openapi
    if path.startswith("/login") or path.startswith("/docs") or path.startswith("/openapi.json"):
        return await call_next(request)

    # protect gradio UI + its assets/api calls
    if path.startswith("/gradio"):
        if request.cookies.get(SESSION_COOKIE) != SESSION_VALUE:
            return RedirectResponse(url="/login", status_code=303)

    return await call_next(request)

# -------------------------
# Mount Gradio UI at /gradio
# -------------------------
app = mount_gradio_app(app, demo, path="/gradio")  # /gradio works 


# -------------------------
# Root: open UI
# -------------------------
@app.get("/")
def root():
    return RedirectResponse(url="/login", status_code=303)



print("Routes registered:", [route.path for route in app.routes])
