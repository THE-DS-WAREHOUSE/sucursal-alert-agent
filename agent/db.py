from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, Date
from databases import Database
from dotenv import load_dotenv
from datetime import date
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

database = Database(DATABASE_URL)
metadata = MetaData()
engine = create_engine(DATABASE_URL)

# --- Gold Layer table ---
# Stores daily reports for each sucursal
# 24 new rows added every day, one per sucursal
gold_layer = Table(
    "gold_sucursal_daily",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("sucursal_id", Integer, nullable=False),
    Column("sucursal_name", String(100), nullable=False),
    Column("report_date", Date, nullable=False),
    Column("total_sales", Float, nullable=False),
    Column("total_clients", Integer, nullable=False),
    Column("clients_churned", Integer, nullable=False),
)

def init_db():
    metadata.create_all(engine)

def seed_sample_data():
    import random
    from datetime import date, timedelta

    random.seed(42)
    sucursal_names = [f"Sucursal {i}" for i in range(1, 25)]

    with engine.begin() as conn:  # engine.begin() auto-commits
        for day_offset in range(30, 0, -1):
            report_date = date.today() - timedelta(days=day_offset)
            for i, name in enumerate(sucursal_names, start=1):
                if day_offset <= 3 and i in [3, 7, 14, 19]:
                    total_sales = random.uniform(8000, 12000)
                    clients_churned = random.randint(20, 30)
                else:
                    total_sales = random.uniform(18000, 25000)
                    clients_churned = random.randint(3, 10)

                total_clients = random.randint(130, 200)

                conn.execute(gold_layer.insert().values(
                    sucursal_id=i,
                    sucursal_name=name,
                    report_date=report_date,
                    total_sales=total_sales,
                    total_clients=total_clients,
                    clients_churned=clients_churned
                ))

if __name__ == "__main__":
    init_db()
    seed_sample_data()
    print("Database initialized and seeded.")