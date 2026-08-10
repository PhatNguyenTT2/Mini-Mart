"""Read-only semantic-trap and Apriori formula validator."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
from urllib.parse import urlparse

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")
SPEC = json.loads((Path(__file__).with_name("benchmark-spec.json")).read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store-id", type=int, default=SPEC["store_id"])
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--benchmark-run-id")
    return parser.parse_args()


def connection_kwargs(url: str) -> dict[str, str]:
    if (urlparse(url).hostname or "").lower() in {"localhost", "127.0.0.1", "::1"}:
        return {}
    certificate = os.environ.get("SUPABASE_DB_CA_PATH")
    if not certificate or not Path(certificate).resolve().is_file():
        raise RuntimeError("SUPABASE_DB_CA_PATH is required for verified remote PostgreSQL TLS")
    return {"sslmode": "verify-full", "sslrootcert": str(Path(certificate).resolve())}


def main() -> int:
    args = parse_args()
    chat_url = os.environ.get("CHATBOT_DATABASE_URL")
    order_url = os.environ.get("ORDER_DATABASE_URL")
    if not chat_url or not order_url:
        raise RuntimeError("CHATBOT_DATABASE_URL and ORDER_DATABASE_URL are required")
    passed = 0
    with psycopg.connect(chat_url, **connection_kwargs(chat_url)) as chat, psycopg.connect(
        order_url, **connection_kwargs(order_url)
    ) as order:
        chat.read_only = True
        order.read_only = True
        with chat.cursor() as chat_cursor, order.cursor() as order_cursor:
            benchmark_run_id = args.benchmark_run_id
            if benchmark_run_id is None:
                chat_cursor.execute(
                    """
                    SELECT benchmark_run_id FROM ml_benchmark_run_v1
                    WHERE store_id=%s AND status='ready'
                    ORDER BY published_at DESC LIMIT 1
                    """,
                    (args.store_id,),
                )
                row = chat_cursor.fetchone()
                if row is None:
                    raise RuntimeError("no ready benchmark run exists")
                benchmark_run_id = str(row[0])
            order_cursor.execute(
                """
                SELECT count(*) FROM sale_order
                WHERE store_id=%s AND status='delivered' AND payment_status='paid'
                  AND order_date <= %s AND benchmark_run_id=%s
                """,
                (args.store_id, SPEC["cutoffs"]["train_end"], benchmark_run_id),
            )
            total_orders = int(order_cursor.fetchone()[0])
            for trap in SPEC["semantic_traps"]:
                trap_passed = False
                for target in trap["targets"]:
                    left, right = sorted((int(trap["anchor"]), int(target)))
                    order_cursor.execute(
                        """
                        SELECT count(*) FROM (
                          SELECT o.id FROM sale_order o
                          JOIN sale_order_detail a ON a.order_id=o.id AND a.product_id=%s
                          JOIN sale_order_detail b ON b.order_id=o.id AND b.product_id=%s
                          WHERE o.store_id=%s AND o.status='delivered' AND o.payment_status='paid'
                            AND o.order_date <= %s AND o.benchmark_run_id=%s
                          GROUP BY o.id
                        ) eligible
                        """,
                        (
                            left,
                            right,
                            args.store_id,
                            SPEC["cutoffs"]["train_end"],
                            benchmark_run_id,
                        ),
                    )
                    raw_count = int(order_cursor.fetchone()[0])
                    chat_cursor.execute(
                        """
                        SELECT co_purchase_count,support,confidence_ab,confidence_ba,lift,total_orders
                        FROM co_purchase_stats
                        WHERE store_id=%s AND product_id_a=%s AND product_id_b=%s
                        """,
                        (args.store_id, left, right),
                    )
                    stat = chat_cursor.fetchone()
                    if stat is None:
                        continue
                    count, support, confidence_ab, confidence_ba, lift, stored_total = stat
                    chat_cursor.execute(
                        """
                        SELECT product_id,order_count FROM product_order_frequency
                        WHERE store_id=%s AND product_id=ANY(%s)
                        """,
                        (args.store_id, [left, right]),
                    )
                    frequencies = {int(product): int(value) for product, value in chat_cursor.fetchall()}
                    if left not in frequencies or right not in frequencies:
                        continue
                    expected_support = raw_count / total_orders
                    expected_ab = raw_count / frequencies[left]
                    expected_ba = raw_count / frequencies[right]
                    expected_lift = raw_count * total_orders / (frequencies[left] * frequencies[right])
                    valid = (
                        int(count) == raw_count
                        and raw_count >= 100
                        and int(stored_total) == total_orders
                        and math.isclose(float(support), expected_support, rel_tol=1e-7, abs_tol=1e-9)
                        and math.isclose(float(confidence_ab), expected_ab, rel_tol=1e-7, abs_tol=1e-9)
                        and math.isclose(float(confidence_ba), expected_ba, rel_tol=1e-7, abs_tol=1e-9)
                        and math.isclose(float(lift), expected_lift, rel_tol=1e-7, abs_tol=1e-9)
                        and 0 < float(confidence_ab) <= 1
                        and 0 < float(confidence_ba) <= 1
                        and float(lift) >= 10
                    )
                    if valid:
                        trap_passed = True
                        break
                print(f"trap={trap['trap_id']} status={'PASS' if trap_passed else 'FAIL'}")
                passed += int(trap_passed)
    print(f"semantic_traps={passed}/{len(SPEC['semantic_traps'])}")
    return 0 if passed == len(SPEC["semantic_traps"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
