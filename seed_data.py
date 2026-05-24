from __future__ import annotations

import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from faker import Faker

DB_PATH = Path("data/ecommerce.db")
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


def create_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.executescript(
        """
        DROP TABLE IF EXISTS order_items;
        DROP TABLE IF EXISTS orders;
        DROP TABLE IF EXISTS products;
        DROP TABLE IF EXISTS customers;

        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            region TEXT NOT NULL,
            signup_date TEXT NOT NULL,
            tier TEXT NOT NULL
        );

        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            cost REAL NOT NULL,
            stock_qty INTEGER NOT NULL
        );

        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            order_date TEXT NOT NULL,
            status TEXT NOT NULL,
            shipping_region TEXT NOT NULL,
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        );

        CREATE TABLE order_items (
            id INTEGER PRIMARY KEY,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            discount_pct REAL NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        );
        """
    )
    conn.commit()


def seed_customers(conn: sqlite3.Connection, fake: Faker) -> None:
    today = date.today()
    rows = []
    for customer_id in range(1, 2001):
        signup_days_ago = random.randint(0, 365 * 4)
        rows.append(
            (
                customer_id,
                fake.name(),
                fake.unique.email(),
                random.choice(CUSTOMER_REGIONS),
                (today - timedelta(days=signup_days_ago)).isoformat(),
                random.choices(CUSTOMER_TIERS, weights=[45, 30, 18, 7], k=1)[0],
            )
        )

    conn.executemany(
        """
        INSERT INTO customers (id, name, email, region, signup_date, tier)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()


def seed_products(conn: sqlite3.Connection, fake: Faker) -> None:
    rows = []
    for product_id in range(1, 201):
        category = PRODUCT_CATEGORIES[(product_id - 1) % len(PRODUCT_CATEGORIES)]
        base_price = round(random.uniform(8.0, 450.0), 2)
        cost_ratio = random.uniform(0.4, 0.82)
        cost = round(base_price * cost_ratio, 2)
        rows.append(
            (
                product_id,
                f"{fake.word().title()} {category[:-1] if category.endswith('s') else category}",
                category,
                base_price,
                cost,
                random.randint(0, 800),
            )
        )

    conn.executemany(
        """
        INSERT INTO products (id, name, category, price, cost, stock_qty)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()


def seed_orders(conn: sqlite3.Connection) -> list[tuple[int, str]]:
    end_date = date.today()
    start_date = end_date - timedelta(days=730)
    rows = []

    for order_id in range(1, 15001):
        customer_id = random.randint(1, 2000)
        order_day_offset = random.randint(0, (end_date - start_date).days)
        order_dt = start_date + timedelta(days=order_day_offset)
        rows.append(
            (
                order_id,
                customer_id,
                order_dt.isoformat(),
                random.choices(ORDER_STATUSES, weights=[76, 10, 6, 8], k=1)[0],
                random.choice(CUSTOMER_REGIONS),
            )
        )

    conn.executemany(
        """
        INSERT INTO orders (id, customer_id, order_date, status, shipping_region)
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()

    return [(order_id, order_date) for order_id, _, order_date, _, _ in rows]


def seed_order_items(conn: sqlite3.Connection) -> None:
    product_price_lookup = {
        row[0]: row[1]
        for row in conn.execute("SELECT id, price FROM products").fetchall()
    }

    rows = []
    for item_id in range(1, 40001):
        product_id = random.randint(1, 200)
        base_price = product_price_lookup[product_id]
        price_jitter = random.uniform(0.92, 1.08)
        unit_price = round(base_price * price_jitter, 2)
        rows.append(
            (
                item_id,
                random.randint(1, 15000),
                product_id,
                random.randint(1, 5),
                unit_price,
                round(random.choice([0, 0, 0, 5, 10, 15, 20, 25, 30]), 2),
            )
        )

    conn.executemany(
        """
        INSERT INTO order_items (id, order_id, product_id, quantity, unit_price, discount_pct)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()


def print_summary(conn: sqlite3.Connection) -> None:
    table_names = ["customers", "products", "orders", "order_items"]
    counts = {
        name: conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
        for name in table_names
    }
    min_max = conn.execute(
        "SELECT MIN(order_date), MAX(order_date) FROM orders"
    ).fetchone()

    print("\nSeed complete: data/ecommerce.db")
    print("-" * 56)
    print(f"{'Table':<16}{'Rows':>12}")
    print("-" * 56)
    for name in table_names:
        print(f"{name:<16}{counts[name]:>12}")
    print("-" * 56)
    print(f"Order date range: {min_max[0]} -> {min_max[1]}")


def main() -> None:
    random.seed(SEED)
    Faker.seed(SEED)
    fake = Faker()

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        create_schema(conn)
        seed_customers(conn, fake)
        seed_products(conn, fake)
        seed_orders(conn)
        seed_order_items(conn)
        print_summary(conn)


if __name__ == "__main__":
    main()
