# Quiick AI — AI-Powered Store Management

> Talk to your store. Sell, restock, and manage inventory with natural language commands in English & Hinglish.

---

## Tech Stack

- **Backend** — Django 4.2, Python 3.x
- **Database** — SQLite (dev) / PostgreSQL (prod)
- **AI** — Google Gemini API
- **Frontend** — Django Templates + Tailwind CSS (CDN)

---

## Local Setup

### 1. Clone & navigate

```bash
git clone https://github.com/your-username/shopai.git
cd shopai/backend
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
GEMINI_API_KEY=your-gemini-api-key-here
```

Generate a secret key:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 5. Run migrations

```bash
python manage.py migrate
```

### 6. Start server

```bash
python manage.py runserver
```

App runs at → `http://127.0.0.1:8000/`

---

## Project Structure

```
backend/
├── manage.py
├── requirements.txt
├── .env.example          ← copy to .env, fill values
│
├── shopai/               ← Django project config
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── core/                 ← Landing + onboarding pages
│   ├── views.py
│   └── urls.py
│
├── dashboard/            ← Main app (inventory, AI, sales, suppliers)
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   └── services/
│       ├── chatbot.py
│       └── intent_model.py
│
├── templates/
│   ├── base.html
│   ├── core/
│   │   ├── landing.html
│   │   ├── onboarding_start.html
│   │   └── onboarding_details.html
│   └── dashboard/
│       ├── base_dashboard.html
│       ├── main_dashboard.html
│       ├── inventory.html
│       ├── product_form.html
│       ├── ai_assistant.html
│       ├── sales.html
│       ├── analytics.html
│       ├── suppliers.html
│       ├── supplier_form.html
│       └── supplier_detail.html
│
└── static/               ← CSS, JS, images
```

---

## URL Routes

| URL | Page |
|-----|------|
| `/` | Landing Page |
| `/start/` | Onboarding — Shop Type |
| `/setup/` | Onboarding — Shop Details |
| `/dashboard/` | Main Dashboard |
| `/dashboard/inventory/` | Inventory Management |
| `/dashboard/inventory/add/` | Add Product |
| `/dashboard/sales/` | Sales Log |
| `/dashboard/analytics/` | Analytics |
| `/dashboard/suppliers/` | Suppliers List |
| `/dashboard/suppliers/add/` | Add Supplier |
| `/dashboard/ai/` | AI Chat Assistant |
| `/dashboard/ai/api/` | AI Chat JSON API |

---

## AI Chat API

`POST /dashboard/ai/api/`

```json
{
  "message": "sell 10 shirts",
  "intent_payload": {
    "intent": "sell",
    "quantity": 10,
    "category": "Shirts"
  }
}
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | ✅ | Django secret key |
| `DEBUG` | ✅ | `True` for dev, `False` for prod |
| `ALLOWED_HOSTS` | ✅ | Comma-separated allowed hosts |
| `GEMINI_API_KEY` | ⚠️ | Required for AI features |
| `DATABASE_URL` | ❌ | Optional — PostgreSQL for prod |

---

## Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -m "feat: add your feature"`
4. Push: `git push origin feature/your-feature`
5. Open a Pull Request
