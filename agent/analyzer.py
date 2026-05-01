import os
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY")
)

# --- Agent State ---
# Shared state that flows between all LangGraph nodes
class AlertState(TypedDict):
    sucursal_id: int
    sucursal_name: str
    report_date: str
    total_sales: float
    total_clients: int
    clients_churned: int
    avg_sales_7d: float
    avg_churn_7d: float
    sales_drop_pct: float
    churn_spike_pct: float
    sales_zscore: float
    churn_zscore: float
    reasons: List[str]
    root_cause: str
    recommendation: str
    alert_message: str

# --- Node 1: Analyze Root Cause ---
# Sends the flagged sucursal data to GPT-4o-mini
# and asks it to identify the most likely root cause
def analyze_root_cause(state: AlertState) -> AlertState:
    prompt = f"""You are a financial analyst monitoring retail sucursal performance.

A sucursal has entered a RED ZONE today. Here is the data:

Sucursal: {state['sucursal_name']} (ID: {state['sucursal_id']})
Date: {state['report_date']}

Today's Metrics:
- Total Sales: ${state['total_sales']:,.0f}
- Total Clients: {state['total_clients']}
- Clients Churned: {state['clients_churned']}

Historical Benchmarks:
- 7-day Avg Sales: ${state.get('avg_sales_7d', 0):,.0f}
- 7-day Avg Churn: {state.get('avg_churn_7d', 0):.1f}
- Sales Drop vs 7d Avg: {state.get('sales_drop_pct', 0):.1f}%
- Churn Spike vs 7d Avg: {state.get('churn_spike_pct', 0):.1f}%
- Sales Z-Score: {state.get('sales_zscore', 0):.2f}
- Churn Z-Score: {state.get('churn_zscore', 0):.2f}

Detection Reasons:
{chr(10).join([f'• {r}' for r in state['reasons']])}

In 2-3 sentences, identify the most likely root cause of this performance drop.
Be specific and data-driven. Focus on what the numbers suggest."""

    response = llm.invoke(prompt)
    state["root_cause"] = response.content
    return state

# --- Node 2: Generate Recommendation ---
# Based on the root cause, generates a concrete action recommendation
def generate_recommendation(state: AlertState) -> AlertState:
    prompt = f"""Based on this root cause analysis for {state['sucursal_name']}:

{state['root_cause']}

Provide ONE specific, actionable recommendation for the regional manager.
Keep it to 1-2 sentences. Be direct and practical."""

    response = llm.invoke(prompt)
    state["recommendation"] = response.content
    return state

# --- Node 3: Format Alert Message ---
# Builds the final Slack message in a clean, readable format
def format_alert_message(state: AlertState) -> AlertState:
    sales_drop = state.get("sales_drop_pct", 0)
    churn_spike = state.get("churn_spike_pct", 0)
    sales_zscore = state.get("sales_zscore", 0)
    churn_zscore = state.get("churn_zscore", 0)

    message = f"""🔴 *ALERTA — {state['sucursal_name']} (ID: {state['sucursal_id']})*
📅 Fecha: {state['report_date']}

*📊 Métricas de Hoy:*
- 💰 Total Ventas: ${state['total_sales']:,.0f}
- 👥 Total Clientes: {state['total_clients']}
- 🚨 Clientes Perdidos: {state['clients_churned']}

*📉 Comparativa Histórica:*
- Caída en Ventas vs 7d: {sales_drop:.1f}%
- Spike en Churn vs 7d: {churn_spike:.1f}%
- Z-Score Ventas: {sales_zscore:.2f}
- Z-Score Churn: {churn_zscore:.2f}

*🔍 Causa Identificada:*
{state['root_cause']}

*⚠️ Acción Recomendada:*
{state['recommendation']}

*🚩 Razones de Alerta:*
{chr(10).join([f'• {r}' for r in state['reasons']])}
"""
    state["alert_message"] = message
    return state

# --- Build LangGraph ---
def build_analyzer():
    graph = StateGraph(AlertState)

    graph.add_node("analyze_root_cause", analyze_root_cause)
    graph.add_node("generate_recommendation", generate_recommendation)
    graph.add_node("format_alert_message", format_alert_message)

    graph.set_entry_point("analyze_root_cause")
    graph.add_edge("analyze_root_cause", "generate_recommendation")
    graph.add_edge("generate_recommendation", "format_alert_message")
    graph.add_edge("format_alert_message", END)

    return graph.compile()

analyzer = build_analyzer()

def analyze_sucursal(metrics: dict) -> str:
    # Fills missing keys with defaults to avoid TypedDict errors
    state = AlertState(
        sucursal_id=metrics["sucursal_id"],
        sucursal_name=metrics["sucursal_name"],
        report_date=metrics["report_date"],
        total_sales=metrics["total_sales"],
        total_clients=metrics["total_clients"],
        clients_churned=metrics["clients_churned"],
        avg_sales_7d=metrics.get("avg_sales_7d", 0),
        avg_churn_7d=metrics.get("avg_churn_7d", 0),
        sales_drop_pct=metrics.get("sales_drop_pct", 0),
        churn_spike_pct=metrics.get("churn_spike_pct", 0),
        sales_zscore=metrics.get("sales_zscore", 0),
        churn_zscore=metrics.get("churn_zscore", 0),
        reasons=metrics["reasons"],
        root_cause="",
        recommendation="",
        alert_message=""
    )

    result = analyzer.invoke(state)
    return result["alert_message"]