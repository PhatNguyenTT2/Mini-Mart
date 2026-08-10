# -*- coding: utf-8 -*-
"""
Fast Item Similarity Computer (v2 Scaled — Step 4.5)

Connects to CHATBOT DB:
 1. Fetches user_product_interaction (1.1M rows)
 2. Constructs a scipy.sparse.csr_matrix (5000 users × 5200 items)
 3. Computes Item-Item Cosine Similarity matrix using sklearn in C++ core (~3-10s)
 4. Filters Top K=50 per item with similarity >= 0.05
 5. Replaces item_similarity table in CHATBOT DB via bulk INSERTs

Usage: python backend/docs/chatbot/seed-product/compute-similarity.py
"""

import os
import sys
import time
import psycopg2
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.metrics.pairwise import cosine_similarity
from pathlib import Path

# Load .env from backend
backend_env = Path(__file__).resolve().parent.parent.parent.parent / '.env'
if backend_env.exists():
    with open(backend_env, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                if not os.environ.get(key.strip()):
                    os.environ[key.strip()] = val.strip()

CHATBOT_DATABASE_URL = os.environ.get('CHATBOT_DATABASE_URL') or os.environ.get('DATABASE_URL')
STORE_ID = 1
TOP_K = 50
SIM_THRESHOLD = 0.05

def connect_db(url):
    if not url:
        raise ValueError("CHATBOT_DATABASE_URL missing!")
    try:
        return psycopg2.connect(url, sslmode='require')
    except Exception:
        return psycopg2.connect(url)

def compute_and_seed_similarity():
    start_time = time.time()
    print(f"\n🚀 Fast Item Similarity Computer (Step 4.5 — Python/SciPy)")
    print(f"🔗 Chatbot DB: {CHATBOT_DATABASE_URL.split('@')[1] if CHATBOT_DATABASE_URL else 'LOCAL'}\n")

    conn = connect_db(CHATBOT_DATABASE_URL)
    cur = conn.cursor()

    # 1. Load interaction matrix
    print("📖 Step 1/4: Fetching 1M+ user-product interactions from CHATBOT DB...")
    cur.execute("""
        SELECT user_id, product_id, interaction_score 
        FROM user_product_interaction 
        WHERE store_id = %s AND interaction_score > 0
    """, (STORE_ID,))
    rows = cur.fetchall()
    print(f"   ✓ Loaded {len(rows):,} interaction records in {time.time() - start_time:.2f}s.")

    df = pd.DataFrame(rows, columns=['user_id', 'product_id', 'interaction_score'])

    # Map user_ids and product_ids to contiguous 0-indexed integer indices
    unique_users = np.unique(df['user_id'])
    unique_prods = np.unique(df['product_id'])

    user_map = {uid: idx for idx, uid in enumerate(unique_users)}
    prod_map = {pid: idx for idx, pid in enumerate(unique_prods)}
    idx_to_prod = {idx: pid for pid, idx in prod_map.items()}

    row_indices = df['user_id'].map(user_map).values
    col_indices = df['product_id'].map(prod_map).values
    data = df['interaction_score'].values.astype(np.float32)

    n_users = len(unique_users)
    n_prods = len(unique_prods)

    # 2. Build Sparse Interaction Matrix (Items as rows for item similarity)
    print(f"⚡ Step 2/4: Building SciPy Sparse Matrix ({n_prods:,} items × {n_users:,} users)...")
    # Matrix shape: (n_prods, n_users)
    item_user_matrix = csr_matrix((data, (col_indices, row_indices)), shape=(n_prods, n_users))

    # 3. Compute Item-Item Cosine Similarity using Scikit-Learn (C++ core)
    print(f"🧮 Step 3/4: Computing Cosine Similarity for {n_prods:,} SKUs...")
    sim_start = time.time()
    # Resulting shape: (n_prods, n_prods)
    item_sim_matrix = cosine_similarity(item_user_matrix, dense_output=False)
    sim_duration = time.time() - sim_start
    print(f"   ✓ Cosine Similarity computed in {sim_duration:.2f} seconds!")

    # 4. Extract Top-K similarities per product & insert into DB
    print(f"💾 Step 4/4: Extracting Top K={TOP_K} (threshold >= {SIM_THRESHOLD}) and inserting into item_similarity table...")

    cur.execute("DELETE FROM item_similarity WHERE store_id = %s", (STORE_ID,))
    conn.commit()

    records_to_insert = []
    
    # Iterate through matrix rows
    for i in range(n_prods):
        pid_a = int(idx_to_prod[i])
        
        # Extract non-zero similarities for row i
        row = item_sim_matrix.getrow(i)
        cols = row.indices
        vals = row.data

        # Filter out self-similarity and below threshold
        valid_mask = (cols != i) & (vals >= SIM_THRESHOLD)
        if not np.any(valid_mask):
            continue

        valid_cols = cols[valid_mask]
        valid_vals = vals[valid_mask]

        # Top K sorting
        if len(valid_vals) > TOP_K:
            top_k_indices = np.argpartition(valid_vals, -TOP_K)[-TOP_K:]
            sorted_order = top_k_indices[np.argsort(-valid_vals[top_k_indices])]
            top_cols = valid_cols[sorted_order]
            top_vals = valid_vals[sorted_order]
        else:
            sorted_order = np.argsort(-valid_vals)
            top_cols = valid_cols[sorted_order]
            top_vals = valid_vals[sorted_order]

        for col_idx, sim_val in zip(top_cols, top_vals):
            pid_b = int(idx_to_prod[col_idx])
            records_to_insert.append((pid_a, pid_b, STORE_ID, round(float(sim_val), 4), 10))

    print(f"   ✓ Extracted {len(records_to_insert):,} similarity pairs.")

    # Bulk insert using psycopg2.extras.execute_values
    from psycopg2.extras import execute_values
    insert_start = time.time()
    query = """
        INSERT INTO item_similarity (item_a, item_b, store_id, similarity, common_users)
        VALUES %s
    """
    execute_values(cur, query, records_to_insert, page_size=5000)
    conn.commit()

    print(f"   ✓ Bulk inserted {len(records_to_insert):,} rows in {time.time() - insert_start:.2f}s.")
    print(f"\n✅ Fast Item Similarity Completed in {time.time() - start_time:.2f}s total!")

    cur.close()
    conn.close()

if __name__ == '__main__':
    compute_and_seed_similarity()
