"""Seed the e-commerce demo database.

Generates realistic data for four tables:
  customers, products, orders, order_items

The target database is controlled by the ``DATABASE_URL`` environment variable
(SQLAlchemy connection URL). Defaults to ``sqlite:///data/ecommerce.db``.

The script is *idempotent*: it drops and recreates all four tables on every run,
so calling it twice produces the same result.

Usage:
    uv run python seed_data.py
    DATABASE_URL=postgresql+psycopg2://user:pass@localhost/mydb uv run python seed_data.py
"""

from __future__ import annotations

import os
import random
from datetime import date, timedelta
from pathlib import Path

import sqlalchemy as sa
from faker import Faker
from sqlalchemy import (
    Column,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
)

# ── Configuration ───────────────────────────────────────────────────────────────
_DEFAULT_DB_URL = "sqlite:///data/ecommerce.db"
DB_URL = os.getenv("DATABASE_URL", _DEFAULT_DB_URL)
SEED = 42

CUSTOMER_REGIONS = ["North", "South", "East", "West"]
CUSTOMER_TIERS = ["bronze", "silver", "gold", "platinum"]
ORDER_STATUSES = ["completed", "returned", "cancelled", "pending"]
PRODUCT_CATEGORIES = [
    "Electronics",
    "Home",
    "Apparel",
    "Beauty",
    "Sports",
    "Toys",
    "Books",
    "Grocery",
]

# ── Schema definition (dialect-agnostic) ────────────────────────────────────────
metadata = MetaData()

customers_table = Table(
    "customers",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(200), nullable=False),
    Column("email", String(320), nullable=False),
    Column("region", String(20), nullable=False),
    Column("signup_date", String(10), nullable=False),
    Column("tier", String(20), nullable=False),
)

products_table = Table(
    "products",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(300), nullable=False),
    Column("category", String(50), nullable=False),
    Column("price", Float, nullable=False),
    Column("cost", Float, nullable=False),
    Column("stock_qty", Integer, nullable=False),
)

orders_table = Table(
    "orders",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("customer_id", Integer, ForeignKey("customers.id"), nullable=False),
    Column("order_date", String(10), nullable=False),
    Column("status", String(20), nullable=False),
    Column("shipping_region", String(20), nullable=False),
)

order_items_table = Table(
    "order_items",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("order_id", Integer, ForeignKey("orders.id"), nullable=False),
    Column("product_id", Integer, ForeignKey("products.id"), nullable=False),
    Column("quantity", Integer, nullable=False),
    Column("unit_price", Float, nullable=False),
    Column("discount_pct", Float, nullable=False),
)


def _ensure_data_dir() -> None:
    """Create the data/ directory for the default SQLite path."""
    if DB_URL.startswith("sqlite:///"):
        rel_path = DB_URL.replace("sqlite:///", "")
        Path(rel_path).parent.mkdir(parents=True, exist_ok=True)


def _build_customers(fake: Faker) -> list[dict]:
    today = date.today()
    rows = []
    for i in range(1, 2001):
        rows.append(
            {
                "id": i,
                "name": fake.name(),
                "email": fake.unique.email(),
                "region": random.choice(CUSTOMER_REGIONS),
                "signup_date": (
                    today - timedelta(days=random.randint(0, 365 * 4))
                ).isoformat(),
                "tier": random.choices(
                    CUSTOMER_TIERS, weights=[45, 30, 18, 7], k=1
                )[0],
            }
        )
    return rows


def _build_products(fake: Faker) -> list[dict]:
    rows = []
    for i in range(1, 201):
        category = PRODUCT_CATEGORIES[(i - 1) % len(PRODUCT_CATEGORIES)]
        base_price = round(random.uniform(8.0, 450.0), 2)
        rows.append(
            {
                "id": i,
                "name": (
                    f"{fake.word().title()} "
                    f"{category[:-1] if category.endswith('s') else category}"
                ),
                "category": category,
                "price": base_price,
                "cost": round(base_price * random.uniform(0.4, 0.82), 2),
                "stock_qty": random.randint(0, 800),
            }
        )
    return rows


def _build_orders() -> list[dict]:
    end_date = date.today()
    start_date = end_date - timedelta(days=730)
    rows = []
    for i in range(1, 15001):
        offset = random.randint(0, (end_date - start_date).days)
        rows.append(
            {
                "id": i,
                "customer_id": random.randint(1, 2000),
                "order_date": (start_date + timedelta(days=offset)).isoformat(),
                "status": random.choices(
                    ORDER_STATUSES, weights=[76, 10, 6, 8], k=1
                )[0],
                "shipping_region": random.choice(CUSTOMER_REGIONS),
            }
        )
    return rows


def _build_order_items(product_prices: dict[int, float]) -> list[dict]:
    rows = []
    discounts = [0, 0, 0, 5, 10, 15, 20, 25, 30]
    for i in range(1, 40001):
        pid = random.randint(1, 200)
        rows.append(
            {
                "id": i,
                "order_id": random.randint(1, 15000),
                "product_id": pid,
                "quantity": random.randint(1, 5),
                "unit_price": round(
                    product_prices[pid] * random.uniform(0.92, 1.08), 2
                ),
                "discount_pct": round(float(random.choice(discounts)), 2),
            }
        )
    return rows


def _print_summary(engine: sa.Engine) -> None:
    table_objs = [customers_table, products_table, orders_table, order_items_table]
    with engine.connect() as conn:
        counts = {
            tbl.name: conn.execute(
                sa.select(sa.func.count()).select_from(tbl)
            ).scalar()
            for tbl in table_objs
        }
        min_max = conn.execute(
            sa.select(
                sa.func.min(orders_table.c.order_date),
                sa.func.max(orders_table.c.order_date),
            )
        ).fetchone()

    print(f"\nSeed complete: {DB_URL}")
    print("-" * 56)
    print(f"{'Table':<16}{'Rows':>12}")
    print("-" * 56)
    for tbl in table_objs:
        print(f"{tbl.name:<16}{counts[tbl.name]:>12}")
    print("-" * 56)
    print(f"Order date range: {min_max[0]} → {min_max[1]}")


def main() -> None:
    random.seed(SEED)
    Faker.seed(SEED)
    fake = Faker()

    _ensure_data_dir()
    engine = sa.create_engine(DB_URL)

    # Drop and recreate all tables (idempotent)
    metadata.drop_all(engine, checkfirst=True)
    metadata.create_all(engine)

    customers = _build_customers(fake)
    products = _build_products(fake)
    orders = _build_orders()
    product_prices = {p["id"]: p["price"] for p in products}
    order_items = _build_order_items(product_prices)

    batch = 2000
    with engine.begin() as conn:
        for i in range(0, len(customers), batch):
            conn.execute(customers_table.insert(), customers[i : i + batch])
        for i in range(0, len(products), batch):
            conn.execute(products_table.insert(), products[i : i + batch])
        for i in range(0, len(orders), batch):
            conn.execute(orders_table.insert(), orders[i : i + batch])
        for i in range(0, len(order_items), batch):
            conn.execute(order_items_table.insert(), order_items[i : i + batch])

    _print_summary(engine)
    engine.dispose()


if __name__ == "__main__":
    main()
