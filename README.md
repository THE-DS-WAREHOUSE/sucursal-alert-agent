# sucursal-alert-agent

A LangGraph agent that monitors 24 sucursals daily via Apache Airflow, detects red zone alerts using fixed thresholds, rolling averages, and z-scores, performs GPT-4o-mini root cause analysis, and sends independent Slack alerts per sucursal from a PostgreSQL Gold Layer.

---

## Project Structure

```
sucursal-alert-agent/
├── agent/
│   ├── analyzer.py         # LangGraph agent — root cause analysis + alert formatting
│   ├── db.py               # PostgreSQL connection, table definition, and data seeding
│   ├── detector.py         # Red zone detection — 3 methods
│   └── slack_sender.py     # Slack webhook alert sender
├── dags/
│   └── alert_dag.py        # Airflow DAG — runs daily at 8am
├── logs/                   # Airflow logs (auto-generated)
├── init_db.sql             # PostgreSQL initialization script
├── .env                    # Environment variables (not committed)
├── docker-compose.yml      # Airflow + PostgreSQL orchestration
├── README.md
└── requirements.txt
```

---

## How It Works

```
[ PostgreSQL Gold Layer ]
  └── 24 rows added daily — one per sucursal
          ↓
[ Airflow DAG — runs every day at 8am ]
          ↓
[ Task 1: init_and_seed ]
  └── Creates table and seeds 30 days of synthetic data
          ↓
[ Task 2: detect_red_zones ]
  ├── Method 1: Fixed threshold (sales < $15,000 or churn > 15)
  ├── Method 2: % drop vs 7-day rolling average (>20% drop)
  └── Method 3: Z-score (sales z < -2.0 or churn z > 2.0)
          ↓
[ Task 3: analyze_root_causes ]
  └── LangGraph agent sends flagged data to GPT-4o-mini
  └── Generates root cause + actionable recommendation
          ↓
[ Task 4: send_slack_alerts ]
  └── One independent Slack message per sucursal in red zone
```

---

## Slack Alert Example

```
🔴 ALERTA — Sucursal 14 (ID: 14)
📅 Fecha: 2026-04-30

📊 Métricas de Hoy:
• 💰 Total Ventas: $9,842
• 👥 Total Clientes: 156
• 🚨 Clientes Perdidos: 24

📉 Comparativa Histórica:
• Caída en Ventas vs 7d: 47.6%
• Spike en Churn vs 7d: 180.0%
• Z-Score Ventas: -3.21
• Z-Score Churn: 3.45

🔍 Causa Identificada:
The churn rate nearly tripled vs the 7-day average while sales
dropped by almost half, suggesting a sudden loss of recurring
clients rather than a drop in new acquisition.

⚠️ Acción Recomendada:
Contact the sucursal manager immediately to investigate recent
service or operational changes that may have driven client departures.
```

---

## Prerequisites

- Python 3.11+
- Docker Desktop
- OpenAI API key
- Slack workspace with an incoming webhook

---

## Step 1 — Create a Slack Account

1. Go to **https://slack.com**
2. Click **"Get started for free"**
3. Sign up with your email
4. Create a new workspace — name it something like `Business Alerts`
5. Complete the setup wizard

---

## Step 2 — Create a Slack Channel

1. Open your Slack workspace
2. On the left sidebar, scroll to **Channels**
3. Click the **+** button next to Channels
4. Select **"Create a channel"**
5. Name it `sucursal-alerts`
6. Set visibility to **Private** or **Public**
7. Click **Create**

---

## Step 3 — Generate a Slack Webhook URL

1. Go to **https://api.slack.com/apps**
2. Click **"Create New App"** → **"From scratch"**
3. Name it `Sucursal Alert Bot` and select your workspace
4. Click **Create App**
5. On the left menu click **"Incoming Webhooks"**
6. Toggle **"Activate Incoming Webhooks"** to **ON**
7. Click **"Add New Webhook to Workspace"** at the bottom
8. Select the `sucursal-alerts` channel
9. Click **Allow**
10. Copy the webhook URL — it looks like:
```
https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX
```

---

## Step 4 — Configure Environment Variables

Create a `.env` file in the project root:

```
OPENAI_API_KEY=sk-your-openai-key-here
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/your/webhook/url
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/sucursal_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=sucursal_db
```

> ⚠️ Never commit `.env` to GitHub — add it to `.gitignore`

---

## Step 5 — Run with Docker

### 1. Make sure Docker Desktop is running

### 2. Clone the repository
```bash
git clone https://github.com/your-username/sucursal-alert-agent.git
cd sucursal-alert-agent
```

### 3. Start all services
```bash
docker compose up
```

This will start:
- **PostgreSQL** — Gold Layer database
- **Airflow Webserver** — UI at `http://localhost:8080`
- **Airflow Scheduler** — runs DAGs on schedule
- **Airflow Init** — creates admin user on first run

First startup takes a few minutes while it installs Python dependencies.

### 4. Access Airflow UI
```
http://localhost:8080
Username: admin
Password: admin
```

### 5. Trigger the DAG manually
1. Find `sucursal_alert_agent` in the DAG list
2. Toggle it **ON** if it's paused
3. Click the ▶️ **Play** button to trigger a manual run
4. Watch the tasks execute: `init_and_seed → detect_red_zones → analyze_root_causes → send_slack_alerts`

### 6. Check Slack
Alerts will appear in your `sucursal-alerts` channel — one message per sucursal in the red zone.

---

## Red Zone Detection Methods

| Method | Metric | Threshold |
|--------|--------|-----------|
| Fixed Threshold | Total Sales | < $15,000 |
| Fixed Threshold | Clients Churned | > 15 |
| Rolling Average (7d) | Sales Drop | > 20% below avg |
| Rolling Average (7d) | Churn Spike | > 50% above avg |
| Z-Score | Sales | z-score < -2.0 |
| Z-Score | Churn | z-score > 2.0 |

A sucursal is flagged if **any** of the three methods triggers.

---

## DAG Schedule

The DAG runs automatically every day at **8:00 AM UTC**:
```python
schedule_interval="0 8 * * *"
```

To change the schedule, modify this line in `alert_dag.py`.

---

## Docker Commands

| Command | Description |
|---------|-------------|
| `docker compose up` | Start all services |
| `docker compose up --build` | Rebuild and start |
| `docker compose down` | Stop and remove containers |
| `docker compose down -v` | Stop, remove containers and delete DB volume |
| `docker compose logs airflow-scheduler` | View scheduler logs |

---

## Requirements

```
apache-airflow
langgraph
langchain-openai
langchain
sqlalchemy==1.4.52
psycopg2-binary
databases
asyncpg
pandas
numpy
scipy
python-dotenv
slack-sdk
openai
```

---

## Notes

- The `init_and_seed` task runs every DAG execution — it uses `CREATE TABLE IF NOT EXISTS` so it won't duplicate the table, but it will insert new rows each run. In production, replace seeding with real Gold Layer data ingestion
- Sucursals 3, 7, 14, and 19 are hardcoded to drop into red zone in the last 3 days of synthetic data — these will always trigger alerts
- LangGraph agent runs independently per sucursal — each gets its own root cause analysis
- The `.env` file must use `@postgres:5432` (not `@localhost:5432`) when running inside Docker
