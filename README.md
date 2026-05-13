<p align="center">
  <img src="docs/design/logo.png" alt="POSMART Logo" width="120" />
</p>

<h1 align="center">POSMART — Mini-Mart Management System</h1>

<p align="center">
  <strong>A full-stack microservices platform for mini-mart operations with AI-powered chatbot, hybrid recommendation engine, and omnichannel retail (POS + E-commerce).</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/node-%3E%3D20-brightgreen" alt="Node.js" />
  <img src="https://img.shields.io/badge/react-19-blue" alt="React 19" />
  <img src="https://img.shields.io/badge/microservices-9-orange" alt="9 Microservices" />
  <img src="https://img.shields.io/badge/AI-RAG%20%2B%20Hybrid%20Ensemble-purple" alt="AI" />
  <img src="https://img.shields.io/badge/deploy-DigitalOcean%20%2B%20Vercel-informational" alt="Deploy" />
</p>

---

## Overview

POSMART is a production-grade mini-mart management system designed for both **offline (POS)** and **online (E-commerce)** retail operations. The system is built on a **9-service microservices architecture** with an event-driven backbone (RabbitMQ), deployed via CI/CD on DigitalOcean and Vercel.

The standout feature is an **AI Chatbot** that goes beyond simple Q&A — it combines **4 recommendation algorithms** into a Hybrid Ensemble, learns from user behavior through a closed feedback loop, and functions as an **Action Assistant** capable of manipulating cart, orders, and payments through natural language.

---

## System Architecture

```mermaid
flowchart TD
    subgraph Clients["Frontend Clients"]
        ADMIN["Admin / POS Dashboard\n(React 19)"]
        CUSTOMER["Customer Web\n(React 19)"]
        CHATWIDGET["AI Chatbot Widget\n(Socket.IO Streaming)"]
    end

    subgraph GW["Nginx Gateway"]
        GATEWAY["CORS · GZIP · Rate Limit\nSSL · X-Request-ID Tracing"]
    end

    subgraph Services["Microservices (Docker)"]
        AUTH["Auth :3001"]
        CATALOG["Catalog :3002"]
        ORDER["Order :3003"]
        SETTINGS["Settings :3004"]
        SUPPLIER["Supplier :3005"]
        INVENTORY["Inventory :3006"]
        PAYMENT["Payment :3007"]
        STATS["Statistics :3009"]
        CHATBOT["Chatbot :3008\nRAG · Hybrid Ensemble · LLM"]
    end

    subgraph Infra["Cloud Infrastructure"]
        DB_AUTH[("Auth DB")]
        DB_CATALOG[("Catalog DB")]
        DB_ORDER[("Order DB")]
        DB_SETTINGS[("Settings DB")]
        DB_SUPPLIER[("Supplier DB")]
        DB_INVENTORY[("Inventory DB")]
        DB_PAYMENT[("Payment DB")]
        DB_CHATBOT[("Chatbot DB")]
        REDIS[("Redis Cloud")]
        MQ["RabbitMQ\n(CloudAMQP)"]
    end

    ADMIN & CUSTOMER & CHATWIDGET -->|HTTPS| GATEWAY
    GATEWAY --> AUTH & CATALOG & ORDER & SETTINGS & SUPPLIER & INVENTORY & PAYMENT & STATS & CHATBOT
    CHATBOT -.->|"S2S HTTP"| CATALOG & INVENTORY & ORDER & AUTH

    AUTH --> DB_AUTH
    CATALOG --> DB_CATALOG
    ORDER --> DB_ORDER
    SETTINGS --> DB_SETTINGS
    SUPPLIER --> DB_SUPPLIER
    INVENTORY --> DB_INVENTORY
    PAYMENT --> DB_PAYMENT
    CHATBOT --> DB_CHATBOT
    STATS --> REDIS

    AUTH & CATALOG & ORDER & INVENTORY & PAYMENT & CHATBOT & STATS <-->|Events| MQ

    style CHATBOT fill:#8b5cf6,color:#fff,stroke:#7c3aed
    style GATEWAY fill:#f59e0b,color:#000,stroke:#d97706
    style REDIS fill:#ef4444,color:#fff
    style MQ fill:#10b981,color:#fff
    style DB_AUTH fill:#3b82f6,color:#fff
    style DB_CATALOG fill:#3b82f6,color:#fff
    style DB_ORDER fill:#3b82f6,color:#fff
    style DB_SETTINGS fill:#3b82f6,color:#fff
    style DB_SUPPLIER fill:#3b82f6,color:#fff
    style DB_INVENTORY fill:#3b82f6,color:#fff
    style DB_PAYMENT fill:#3b82f6,color:#fff
    style DB_CHATBOT fill:#3b82f6,color:#fff
```

---

## Key Features

### 🏪 POS & Admin Dashboard

Full-featured back-office for in-store operations:

- **Point of Sale** — Fast checkout with barcode scanning, draft orders, and direct payment processing
- **Product & Category Management** — CRUD with price history tracking and QR code generation
- **Inventory Control** — Batch tracking, stock-in/stock-out, warehouse management, expiry alerts
- **Order Management** — Omnichannel orders (POS + online), status lifecycle, refund processing
- **Supplier & Purchase Orders** — Supplier directory, purchase order workflows
- **Employee & Role Management** — RBAC with granular permissions
- **Payment Integration** — VNPay gateway + cash/card direct payment
- **Analytics Dashboard** — Revenue, top products, customer insights, real-time statistics
- **AI Chatbot Dashboard** — Monitor recommendation performance, force data re-learning, view conversation analytics

### 🛒 Customer E-commerce Web

Modern shopping experience for end customers:

- **Product Browsing** — Category filtering, search, detailed product pages with stock availability
- **Shopping Cart** — Add/remove/update with real-time price calculation
- **Multi-store Support** — Store selection with location-aware inventory
- **Online Checkout** — VNPay integration with order tracking and status updates
- **Order History** — Full order lifecycle visibility
- **AI Shopping Assistant** — Chatbot widget with product recommendations and cart management via natural language

### 🤖 AI Chatbot — Hybrid Recommendation & Action Assistant

> The core differentiator of POSMART. Not just a Q&A bot — a full recommendation engine + operational assistant.

#### Hybrid Ensemble Recommendation (4 Algorithms)

The chatbot combines **4 recommendation algorithms** with dynamically learned weights:

| Algorithm | Symbol | Purpose |
|-----------|--------|---------|
| **Content-Based RAG** | α | Semantic + keyword search using Vietnamese SBERT embeddings (768d) with Reciprocal Rank Fusion |
| **Collaborative Filtering** | β | Item-based CF using cosine similarity on user-product interaction matrices |
| **Apriori Association Rules** | γ | Co-purchase pattern mining with support, confidence, and lift metrics |
| **Session Personalization** | δ | Customer-type clustering with contextual boosting based on shopping patterns |

**Final score**: `final = α×Content + β×CF + γ×Apriori + δ×Personal`

Weights (α, β, γ, δ) are **not static** — they are automatically optimized nightly by a **Weight Learner** that analyzes conversion funnels.

#### RAG Pipeline

```mermaid
flowchart LR
    A["User Query"] --> B["Query Reformulation\n(multi-turn context)"]
    B --> C["Vietnamese SBERT\nEmbedding (768d)"]
    C --> D1["Semantic Search\n(pgvector HNSW)"]
    C --> D2["Keyword Search\n(tsvector + GIN)"]
    D1 & D2 --> E["RRF Fusion\n(k=60)"]
    E --> F["Hybrid Ensemble\nRe-ranking"]
    F --> G["LLM Generation\n(Qwen 2.5-7B)"]
    G --> H["Response +\nProduct Cards"]

    style A fill:#2563eb,color:#fff
    style E fill:#f59e0b,color:#000
    style F fill:#10b981,color:#fff
    style G fill:#8b5cf6,color:#fff
```

#### Closed-Loop Feedback System

The system tracks a **5-step conversion funnel** and uses it to continuously improve:

```mermaid
flowchart LR
    R["Recommended"] --> H["Hovered\n(≥1.5s dwell)"]
    H --> C["Clicked"]
    C --> AC["Added to Cart"]
    AC --> P["Purchased"]
    P -->|"Nightly 2AM"| WL["Weight Learner"]
    WL -->|"Update α β γ δ"| R

    style R fill:#6366f1,color:#fff
    style P fill:#10b981,color:#fff
    style WL fill:#f59e0b,color:#000
```

- **Dual-Tracking Analytics**: Browser-side hover/click tracking + server-side purchase attribution (24h lookback window)
- **Nightly Batch Pipeline** (2:00 AM): Weight optimization, similarity matrix recomputation, Apriori statistics refresh
- **Self-improving**: The more users interact, the better recommendations become

#### Action Assistant (Write Operations)

Beyond read-only chat, the assistant can **execute actions** through natural conversation:

| Capability | Customer | Employee (POS) |
|------------|----------|----------------|
| Add/remove/update cart items | ✅ Via natural language | ✅ POS cart integration |
| Track orders | ✅ Own orders only | ✅ All store orders |
| Cancel orders | ✅ Draft only, with confirmation | ✅ Draft/shipping |
| Create orders | — | ✅ Multi-turn conversation |
| Check payments | ✅ Own orders | ✅ All payments |

**Security**: 7-layer protection — Intent classification → Permission check → Ownership validation → Status check → Confirmation gate → Audit log → Rate limiting

**Contextual Pronoun Resolution**: When a user says *"add that to cart"* after receiving a recommendation, the system resolves *"that"* using `lastMentionedProducts` from the session context.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Node.js 20, Express, Socket.IO |
| **Frontend** | React 19, Vite, Tailwind CSS |
| **Gateway** | Nginx (rate limiting, CORS, GZIP, WebSocket) |
| **Database** | PostgreSQL (Supabase) |
| **Vector Search** | pgvector (HNSW index, 768d embeddings) |
| **Full-text Search** | PostgreSQL tsvector + GIN index |
| **LLM** | Qwen/Qwen2.5-7B-Instruct (HuggingFace Inference API) |
| **Embedding** | Vietnamese SBERT (local ONNX runtime) |
| **Message Queue** | RabbitMQ (CloudAMQP) |
| **Cache** | Redis (Redis Cloud) |
| **Payment** | VNPay Sandbox |
| **CI/CD** | GitHub Actions → GHCR → DigitalOcean |
| **Hosting** | DigitalOcean Droplet (backend) + Vercel (frontend) |

---

## Microservices

| Service | Port | Responsibility |
|---------|------|---------------|
| **Gateway** | 8080 | Nginx reverse proxy, CORS, rate limiting, request tracing |
| **Auth** | 3001 | Authentication, JWT, RBAC, employee & customer management |
| **Catalog** | 3002 | Products, categories, price history (dedicated database) |
| **Order** | 3003 | Order lifecycle, POS + online orders, refunds |
| **Settings** | 3004 | System configuration, discount policies |
| **Supplier** | 3005 | Supplier management, purchase orders |
| **Inventory** | 3006 | Stock tracking, batches, warehouse, stock-in/out |
| **Payment** | 3007 | VNPay integration, direct payments, refund processing |
| **Chatbot** | 3008 | AI/RAG, hybrid recommendations, Socket.IO, action assistant |
| **Statistics** | 3009 | Analytics, revenue reports, dashboard metrics |

All services communicate asynchronously via **RabbitMQ events** (`ORDER_COMPLETED`, `PRODUCT_CREATED`, `INVENTORY_UPDATED`, etc.) and synchronously via internal HTTP for real-time queries.

---

## Project Structure

```
Mini-Mart/
├── backend/
│   ├── gateway/                  # Nginx config + Dockerfile
│   ├── services/
│   │   ├── auth/                 # Authentication & RBAC
│   │   ├── catalog/              # Product management
│   │   ├── order/                # Order processing
│   │   ├── settings/             # System configuration
│   │   ├── supplier/             # Supplier management
│   │   ├── inventory/            # Stock management
│   │   ├── payment/              # Payment processing
│   │   ├── chatbot/              # AI Chatbot + RAG + Recommendations
│   │   └── statistics/           # Analytics & reporting
│   ├── shared/                   # Common utilities, DB, event bus
│   ├── docker-compose.yml        # Development orchestration
│   └── docker-compose.prod.yml   # Production orchestration
│
├── frontend/                     # Admin Dashboard + POS (React 19 + Vite + TW4)
├── customer/                     # Customer E-commerce (React 19 + Vite + TW3)
│
├── .github/workflows/            # CI/CD pipelines
│   ├── deploy-backend.yml        # Build → GHCR → DigitalOcean
│   ├── deploy-frontend.yml       # Lint → Build → Vercel
│   ├── deploy-customer.yml       # Lint → Build → Vercel
│   └── ci.yml                    # PR quality gate
│
├── infra/scripts/                # Server setup & deploy scripts
└── docs/                         # Architecture, database, deployment docs
```

---

## Deployment

The system uses a fully automated CI/CD pipeline:

| Component | Platform | Trigger |
|-----------|----------|---------|
| **Backend** (9 services) | DigitalOcean Droplet (2GB + 4GB Swap) | Push to `main` (backend/**) |
| **Admin/POS** | Vercel | Push to `main` (frontend/**) |
| **Customer Web** | Vercel | Push to `main` (customer/**) |

**Pipeline**: Code push → GitHub Actions → Build Docker images (parallel) → Push to GHCR → SSH deploy to Droplet → Health check verification

**Domains**:
- `api.mini-mart.dev` — Backend API (SSL via Let's Encrypt)
- [`admin.mini-mart.dev`](https://admin.mini-mart.dev) — Admin/POS Dashboard
- [`shop.mini-mart.dev`](https://shop.mini-mart.dev) — Customer Web

See [`docs/deploy/`](docs/deploy/) for detailed deployment documentation.

---

## Getting Started

### Prerequisites

- Node.js ≥ 20
- Docker & Docker Compose
- PostgreSQL credentials (Supabase)
- Redis & RabbitMQ credentials

### Development

```bash
# Clone the repository
git clone https://github.com/PhatNguyenTT2/Mini-Mart.git
cd Mini-Mart

# Backend — Start all microservices
cd backend
cp .env.prod.example .env    # Fill in your credentials
docker compose up -d

# Admin Dashboard
cd ../frontend
npm install && npm run dev   # http://localhost:5173

# Customer Web
cd ../customer
npm install && npm run dev   # http://localhost:5174
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [`docs/deploy/`](docs/deploy/) | Deployment guide & architecture overview |
| [`backend/docs/chatbot/report/`](backend/docs/chatbot/report/) | AI Chatbot & Recommendation Engine technical report |
| [`backend/docs/chatbot/assistant/`](backend/docs/chatbot/assistant/) | Action Assistant design & security protocol |

---

## License

This project is developed as part of an academic capstone project at UIT (University of Information Technology).
