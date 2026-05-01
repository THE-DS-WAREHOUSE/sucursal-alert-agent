import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'agent'))

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# --- Default DAG arguments ---
default_args = {
    "owner": "jose",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# --- Task 1: Detect red zone sucursals ---
def task_detect_red_zones(**context):
    from detector import get_sucursal_data, detect_red_zones

    print("📊 Pulling Gold Layer data from PostgreSQL...")
    df = get_sucursal_data(days=30)

    print(f"✅ Pulled {len(df)} rows — running red zone detection...")
    flagged = detect_red_zones(df)

    print(f"🚨 {len(flagged)} sucursals in red zone today")

    # Push flagged sucursals to XCom so next task can use them
    context["ti"].xcom_push(key="flagged_sucursals", value=flagged)

# --- Task 2: Analyze root cause with LangGraph ---
def task_analyze_root_causes(**context):
    from analyzer import analyze_sucursal

    # Pull flagged sucursals from previous task via XCom
    flagged = context["ti"].xcom_pull(
        task_ids="detect_red_zones",
        key="flagged_sucursals"
    )

    if not flagged:
        print("✅ No sucursals in red zone — skipping analysis.")
        context["ti"].xcom_push(key="analyzed_sucursals", value=[])
        return

    print(f"🔍 Analyzing root causes for {len(flagged)} sucursals...")

    analyzed = []
    for sucursal in flagged:
        print(f"  → Analyzing {sucursal['sucursal_name']}...")
        alert_message = analyze_sucursal(sucursal)
        sucursal["alert_message"] = alert_message
        analyzed.append(sucursal)

    # Push analyzed sucursals to XCom for the next task
    context["ti"].xcom_push(key="analyzed_sucursals", value=analyzed)
    print(f"✅ Analysis complete for {len(analyzed)} sucursals")

# --- Task 3: Send Slack alerts ---
def task_send_slack_alerts(**context):
    from slack_sender import send_all_alerts

    # Pull analyzed sucursals from previous task via XCom
    analyzed = context["ti"].xcom_pull(
        task_ids="analyze_root_causes",
        key="analyzed_sucursals"
    )

    if not analyzed:
        print("✅ No alerts to send.")
        return

    print(f"📤 Sending {len(analyzed)} Slack alerts...")
    results = send_all_alerts(analyzed)

    print(f"✅ Done — {len(results['sent'])} sent, {len(results['failed'])} failed")

def task_init_and_seed(**context):
    from db import init_db, seed_sample_data
    print("🗄️ Initializing database and seeding sample data...")
    init_db()
    seed_sample_data()
    print("✅ Database ready.")
# --- DAG Definition ---
with DAG(
    dag_id="sucursal_alert_agent",
    default_args=default_args,
    description="Daily red zone detection and Slack alerts for sucursals",
    schedule_interval="0 8 * * *",  # runs every day at 8am
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["alerts", "sucursal", "langgraph"]
) as dag:

    init_seed = PythonOperator(
        task_id="init_and_seed",
        python_callable=task_init_and_seed,
        provide_context=True
    )

    detect = PythonOperator(
        task_id="detect_red_zones",
        python_callable=task_detect_red_zones,
        provide_context=True
    )

    analyze = PythonOperator(
        task_id="analyze_root_causes",
        python_callable=task_analyze_root_causes,
        provide_context=True
    )

    send = PythonOperator(
        task_id="send_slack_alerts",
        python_callable=task_send_slack_alerts,
        provide_context=True
    )

    # Task execution order
    init_seed >> detect >> analyze >> send