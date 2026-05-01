CREATE DATABASE sucursal_db;

\connect sucursal_db;

CREATE TABLE IF NOT EXISTS gold_sucursal_daily (
    id SERIAL PRIMARY KEY,
    sucursal_id INTEGER NOT NULL,
    sucursal_name VARCHAR(100) NOT NULL,
    report_date DATE NOT NULL,
    total_sales FLOAT NOT NULL,
    total_clients INTEGER NOT NULL,
    clients_churned INTEGER NOT NULL
);