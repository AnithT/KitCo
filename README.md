# KitCo — Phase 1 Backend

Menu Messaging & Order Orchestration for Cloud Kitchens.

## Architecture Overview

```
┌─────────────────┐     ┌──────────────┐     ┌──────────────────┐
│  Consumer App   │────▶│  FastAPI API  │◀────│ Management       │
│  (deep link PWA)│     │  (async)      │     │ Console (React)  │
└────────┬────────┘     └──────┬───────┘     └──────────────────┘
         │                     │
         │              ┌──────┴───────┐
         │              │   PostgreSQL  │
         │              │   (primary)   │
         │              └──────────────┘
         │                     │
    ┌────┴─────┐        ┌──────┴───────┐     ┌──────────────────┐
    │  Stripe  │        │    Redis     │────▶│  Celery Worker   │
    │ Checkout │        │ (cache+queue)│     │  (broadcast fan  │
    └──────────┘        └──────────────┘     │   out via Twilio)│
                                              └──────────────────┘
```

## Project Structure

```
kitco/
├── app/
│   ├── main.py                  # FastAPI entry point
│   ├── worker.py                # Celery worker
│   ├── core/
│   │   ├── config.py            # Settings from env
│   │   ├── database.py          # Async SQLAlchemy engine
│   │   ├── security.py          # JWT + password hashing
│   │   └── websocket.py         # WS connection manager
│   ├── models/
│   │   ├── kitchen.py           # Tenant model
│   │   ├── menu.py              # Menu + MenuItem
│   │   ├── customer.py          # Opted-in recipients
│   │   ├── order.py             # Order + OrderItem
│   │   └── broadcast.py         # Broadcast + Recipient tracking
│   ├── schemas/                 # Pydantic request/response models
│   │   ├── auth.py
│   │   ├── menu.py
│   │   ├── customer.py
│   │   ├── order.py
│   │   └── broadcast.py
│   ├── services/                # Business logic layer
│   │   ├── menu_service.py
│   │   ├── customer_service.py
│   │   ├── order_service.py
│   │   ├── broadcast_service.py
│   │   ├── payment_service.py
│   │   └── messaging_service.py
│   ├── events/
│   │   ├── event_bus.py         # In-process pub/sub
│   │   └── handlers.py          # Side-effect handlers
│   └── api/v1/
│       ├── router.py            # Aggregates all routers
│       └── endpoints/
│           ├── auth.py          # Register / Login / Refresh
│           ├── menus.py         # Menu CRUD (kitchen console)
│           ├── customers.py     # Customer list management
│           ├── orders.py        # Order board + consumer create
│           ├── broadcasts.py    # Trigger + monitor broadcasts
│           ├── webhooks.py      # Stripe + Twilio callbacks
│           ├── public.py        # Consumer-facing menu + checkout
│           └── ws.py            # WebSocket endpoints
├── alembic/                     # Database migrations
├── tests/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Quick Start

### 1. Clone and configure

```bash
cp .env.example .env
# Edit .env with your actual keys (Stripe, Twilio, secret key)
```

### 2. Start with Docker Compose

```bash
docker compose up -d
```

This starts PostgreSQL, Redis, the FastAPI API (port 8000), and a Celery worker.

### 3. Run migrations

```bash
docker compose exec api alembic revision --autogenerate -m "initial"
docker compose exec api alembic upgrade head
```

### 4. Open the docs

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health check: http://localhost:8000/health

## API Endpoints Summary

### Auth (no token required)
| Method | Endpoint              | Description              |
|--------|-----------------------|--------------------------|
| POST   | /api/v1/auth/register | Register a new kitchen   |
| POST   | /api/v1/auth/login    | Login, get JWT tokens    |
| POST   | /api/v1/auth/refresh  | Refresh access token     |

### Menus (kitchen console — token required)
| Method | Endpoint                          | Description              |
|--------|-----------------------------------|--------------------------|
| POST   | /api/v1/menus/                    | Create menu with items   |
| GET    | /api/v1/menus/                    | List menus (filterable)  |
| GET    | /api/v1/menus/{id}                | Get menu detail          |
| PATCH  | /api/v1/menus/{id}                | Update menu              |
| POST   | /api/v1/menus/{id}/publish        | Publish menu             |
| DELETE | /api/v1/menus/{id}                | Delete menu              |
| POST   | /api/v1/menus/{id}/items          | Add item to menu         |
| PATCH  | /api/v1/menus/items/{item_id}     | Update item              |
| DELETE | /api/v1/menus/items/{item_id}     | Delete item              |

### Customers (kitchen console — token required)
| Method | Endpoint                          | Description              |
|--------|-----------------------------------|--------------------------|
| POST   | /api/v1/customers/                | Add customer             |
| POST   | /api/v1/customers/bulk-import     | Bulk import customers    |
| GET    | /api/v1/customers/                | List customers           |
| GET    | /api/v1/customers/count           | Opted-in count           |
| GET    | /api/v1/customers/{id}            | Get customer             |
| PATCH  | /api/v1/customers/{id}            | Update customer          |

### Orders (kitchen console — token required)
| Method | Endpoint                          | Description              |
|--------|-----------------------------------|--------------------------|
| GET    | /api/v1/orders/                   | List orders (filterable) |
| GET    | /api/v1/orders/{id}               | Get order detail         |
| PATCH  | /api/v1/orders/{id}/status        | Update order status      |

### Orders (consumer — no token)
| Method | Endpoint                          | Description              |
|--------|-----------------------------------|--------------------------|
| POST   | /api/v1/orders/                   | Create order (post-pay)  |
| GET    | /api/v1/orders/track/{id}?phone=  | Track order by phone     |

### Broadcasts (kitchen console — token required)
| Method | Endpoint                          | Description              |
|--------|-----------------------------------|--------------------------|
| POST   | /api/v1/broadcasts/               | Send menu broadcast      |
| GET    | /api/v1/broadcasts/               | List past broadcasts     |
| GET    | /api/v1/broadcasts/{id}           | Broadcast detail + stats |

### Public (consumer — no token)
| Method | Endpoint                                    | Description                |
|--------|---------------------------------------------|----------------------------|
| GET    | /api/v1/public/menu/{kitchen_id}/{menu_id}  | View published menu        |
| POST   | /api/v1/public/checkout                     | Create Stripe checkout     |

### Webhooks (external services)
| Method | Endpoint                          | Description              |
|--------|-----------------------------------|--------------------------|
| POST   | /api/v1/webhooks/stripe           | Stripe payment callback  |
| POST   | /api/v1/webhooks/twilio/status    | Twilio delivery status   |

### WebSocket
| Endpoint                        | Description                    |
|---------------------------------|--------------------------------|
| ws://host/api/v1/ws/kitchen/{id}| Live order feed for console    |
| ws://host/api/v1/ws/order/{id}  | Live tracking for customer     |

## Order Status Flow

```
PENDING → ACCEPTED → IN_PREP → READY → OUT_FOR_DELIVERY → COMPLETED
   ↓         ↓
REJECTED  CANCELLED
```

Each transition is validated — the API rejects invalid status jumps and records timestamps for SLA tracking.

## Key Design Decisions

1. **Tenant isolation via kitchen_id**: Every query is scoped by the authenticated kitchen's ID. No cross-tenant data leakage.

2. **Order snapshots**: Customer name, phone, address, and item names/prices are copied into the order at creation time. This means historical orders remain accurate even if the menu or customer record changes.

3. **Broadcast attribution**: The deep link includes a `ref={broadcast_id}` parameter. When the order is created, this ties back to the broadcast for campaign analytics.

4. **Stock decrement at order time**: Stock is checked and decremented atomically during order creation. Items auto-hide when stock hits zero.

5. **Event bus**: Side effects (notifications, analytics) are decoupled from the main request via an in-process event bus. This can be swapped for RabbitMQ/SQS later without changing service code.

## Next Steps

- [ ] Add rate limiting (slowapi) on public endpoints
- [ ] Stripe Connect for multi-kitchen payment splitting
- [ ] Image upload for menu items (S3 + presigned URLs)
- [ ] OTP verification for customer phone at checkout
- [ ] Admin dashboard analytics queries
- [ ] Unit and integration test suite
