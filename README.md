# sucursal-alert-agent
LangGraph agent that monitors 24 sucursals daily via Apache Airflow, detects red zone alerts using fixed thresholds, rolling averages, and z-scores, performs GPT-4o-mini root cause analysis, and sends independent Slack alerts per sucursal from a PostgreSQL Gold Layer.
