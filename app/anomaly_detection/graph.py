from langgraph.graph import StateGraph, END
from .state import PriceAnomalyState
from .nodes import (
    product_discovery_node,
    variant_discovery_node,
    price_collection_node,
    normalization_node,
    anomaly_detection_node
)

def create_anomaly_graph():
    """
    Build LangGraph for anomaly detection
    Flow: ProductDiscovery → VariantDiscovery → PriceCollection → 
          Normalization → AnomalyDetection
    """
    builder = StateGraph(PriceAnomalyState)
    
    # Add nodes
    builder.add_node("product_discovery", product_discovery_node)
    builder.add_node("variant_discovery", variant_discovery_node)
    builder.add_node("price_collection", price_collection_node)
    builder.add_node("normalization", normalization_node)
    builder.add_node("anomaly_detection", anomaly_detection_node)
    
    # Define flow
    builder.set_entry_point("product_discovery")
    builder.add_edge("product_discovery", "variant_discovery")
    builder.add_edge("variant_discovery", "price_collection")
    builder.add_edge("price_collection", "normalization")
    builder.add_edge("normalization", "anomaly_detection")
    builder.add_edge("anomaly_detection", END)
    
    return builder.compile()
