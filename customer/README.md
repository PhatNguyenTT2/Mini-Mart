# Customer E-commerce Web

> **Live**: [shop.mini-mart.dev](https://shop.mini-mart.dev)

Customer-facing e-commerce web application for POSMART mini-mart. Enables online shopping with product browsing, cart management, VNPay checkout, order tracking, and an AI chatbot shopping assistant with hybrid product recommendations.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | React 19 + Vite 8 |
| Styling | Tailwind CSS v3 + tailwindcss-animate |
| UI Components | Headless UI |
| Carousel | Embla Carousel (with autoplay) |
| Icons | Lucide React |
| Real-time | Socket.IO Client |
| Routing | React Router v6 |
| Notifications | React Hot Toast |
| Utilities | clsx, tailwind-merge |

## Features

### Shopping Experience
- Multi-store selection with location-aware inventory
- Product browsing with category filtering
- Detailed product pages with stock availability and pricing
- Product image gallery and related recommendations

### Cart & Checkout
- Add/remove/update items with real-time price calculation
- Persistent cart state across sessions
- VNPay online payment integration
- Order creation with delivery details

### Order Tracking
- Full order history with status timeline
- Real-time order status updates (Draft → Paid → Shipping → Delivered)
- Payment result verification (VNPay callback handling)
- Visibility API optimized polling (pauses when tab is inactive)

### AI Shopping Assistant (Chatbot)
- Real-time Socket.IO streaming responses
- **Hybrid product recommendations** (RAG + CF + Apriori + Session Personalization)
- Product cards with "Add to Cart" actions directly from chat
- **Dual-Tracking Analytics**: hover dwell time (≥1.5s), click, and cart tracking for recommendation feedback
- Contextual pronoun resolution ("add *that* to cart")
- Markdown-rendered responses with product carousels

### Authentication
- Customer registration and login
- Guest browsing with cart persistence
- JWT-based session management

## Project Structure

```
customer/
├── src/
│   ├── components/
│   │   ├── ChatWidget/          # AI chatbot + recommendation UI
│   │   ├── Cart/                # Shopping cart
│   │   ├── Checkout/            # Checkout flow
│   │   ├── Product/             # Product cards and lists
│   │   ├── HomeMerchandising/   # Homepage hero + promotions
│   │   ├── Header/              # Navigation bar
│   │   ├── Footer/              # Site footer
│   │   ├── LoginSignup/         # Auth UI
│   │   └── ErrorBoundary.jsx    # Crash protection
│   ├── contexts/
│   │   ├── AuthContext.jsx      # Authentication state
│   │   ├── CartContext.jsx      # Cart state + chatbot integration
│   │   ├── ChatContext.jsx      # Chatbot connection state
│   │   └── StoreContext.jsx     # Multi-store selection
│   ├── pages/
│   │   ├── Home.jsx             # Landing page
│   │   ├── ProductDetail.jsx    # Product detail + recommendations
│   │   ├── CartPage.jsx         # Cart view
│   │   ├── CheckoutPage.jsx     # Checkout + VNPay
│   │   ├── OrderHistoryPage.jsx # Order list
│   │   ├── OrderStatusPage.jsx  # Order tracking timeline
│   │   ├── StoreSelection.jsx   # Store picker
│   │   └── LoginSignup.jsx      # Auth page
│   └── services/
│       ├── api.js               # Axios instance + interceptors
│       ├── authService.js       # Login/register API
│       ├── productService.js    # Product browsing API
│       ├── categoryService.js   # Category listing API
│       ├── orderService.js      # Order creation + tracking
│       ├── paymentService.js    # VNPay payment API
│       ├── chatSocketService.js # Socket.IO connection
│       ├── chatFeedbackService.js # Recommendation tracking
│       └── storeService.js      # Store listing API
├── package.json
├── vite.config.js
└── tailwind.config.js
```

## Getting Started

```bash
npm install
npm run dev       # http://localhost:5174
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
