# Admin / POS Dashboard — Frontend

> **Live**: [admin.mini-mart.dev](https://admin.mini-mart.dev)

Admin dashboard and Point of Sale (POS) interface for POSMART mini-mart management system. Provides complete back-office operations including product management, inventory control, order processing, and an integrated AI chatbot for employee assistance.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | React 19 + Vite (Rolldown) |
| Styling | Tailwind CSS v4 |
| Charts | Recharts + Chart.js |
| Icons | Lucide React |
| Real-time | Socket.IO Client |
| Routing | React Router v7 |
| QR Code | html5-qrcode + qrcode |

## Features

### Dashboard & Analytics
- Revenue overview with interactive charts
- Top-selling products and category breakdown
- Customer insights and employee performance
- Real-time statistics from Statistics Service

### Product Management
- Product CRUD with image upload
- Category hierarchy management
- Price history tracking
- QR code generation for products

### Inventory Control
- Stock-in / stock-out workflows
- Batch tracking with expiry dates
- Warehouse location management
- Purchase order lifecycle (draft → approved → received)

### Point of Sale (POS)
- Dedicated POS login flow for cashiers
- Fast product search and barcode scanning
- Draft order creation with direct payment
- VNPay integration + cash/card processing

### Order Management
- Omnichannel orders (POS + online)
- Status lifecycle: Draft → Paid → Shipping → Delivered
- Refund and cancellation processing
- Detailed order view with payment info

### Reports
- Sales reports (by date range, product, category)
- Employee sales performance
- Customer purchase analytics
- Inventory movement reports
- Profit analysis
- Purchase order summaries

### Employee & Access Control
- Employee CRUD with role assignment
- Role-based access control (RBAC)
- Granular permission management
- Protected routes based on user permissions

### AI Chatbot (Employee Assistant)
- Socket.IO real-time streaming responses
- Inventory checks and product search via natural language
- AI recommendation performance dashboard
- Markdown-rendered bot responses

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── ChatWidget/          # AI chatbot interface
│   │   ├── Dashboard/           # Dashboard widgets
│   │   ├── Layout/              # App shell (header, sidebar)
│   │   ├── LoginSignup/         # Authentication UI
│   │   ├── OrderList/           # Order management
│   │   ├── POSMain/             # POS checkout interface
│   │   ├── POSList/             # POS management
│   │   ├── ProductList/         # Product CRUD
│   │   ├── InventoryList/       # Inventory views
│   │   ├── PurchaseOrderList/   # Purchase workflows
│   │   ├── SupplierList/        # Supplier management
│   │   ├── PaymentList/         # Payment tracking
│   │   ├── ProtectedRoute.jsx   # RBAC route guard
│   │   └── ...                  # 36 component directories
│   ├── contexts/
│   │   ├── ChatContext.jsx      # Chatbot state
│   │   ├── NotificationContext.jsx
│   │   └── SidebarContext.jsx
│   ├── pages/                   # 20 page components
│   │   ├── pos/                 # POS login + main
│   │   ├── reports/             # 6 report pages
│   │   └── products/            # Product detail views
│   ├── services/                # 30 API service modules
│   └── hooks/                   # Custom React hooks
├── package.json
├── vite.config.js
└── tailwind.config.js
```

## Getting Started

```bash
npm install
npm run dev       # http://localhost:5173
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `VITE_API_URL` | Backend API Gateway URL (default: `http://localhost:8080`) |

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start dev server |
| `npm run build` | Production build |
| `npm run lint` | Run ESLint |
| `npm run preview` | Preview production build |
| `npm run check:colors` | Audit color palette usage |
