# CARD-Net — Credit Card Fraud Detection Research Platform

**Institution:** Anurag University, Department of Artificial Intelligence  
**Type:** Research prototype · Decision-support tool · NOT for production fraud blocking

> ⚠️ **Research Disclaimer**: CARD-Net is a research prototype. Predictions are decision-support information only. Do not use this system to automatically block or authorise banking transactions. Fraud thresholds (low=0.3, high=0.7) are configurable defaults and have not been validated on production data.

---

## Architecture

```
card-net/
├── backend/          # FastAPI + SQLAlchemy + PostgreSQL
│   ├── app/
│   │   ├── api/v1/   # REST endpoints (auth, dashboard, transactions, predictions, batch, …)
│   │   ├── core/     # Config, security, dependencies, logging
│   │   ├── db/       # ORM models + async session
│   │   ├── ml/       # TAB-Net inference pipeline + SHAP explainability
│   │   ├── schemas/  # Pydantic request/response models
│   │   └── services/ # Audit log service
│   ├── alembic/      # Database migrations
│   ├── tests/        # pytest-asyncio integration + unit tests
│   └── seed_admin.py # First-run admin user seed
├── frontend/         # Next.js 16 + Tailwind CSS 4 + React Query
│   └── src/
│       ├── app/      # Page routes (login, dashboard, transactions, …)
│       ├── components/
│       ├── lib/      # Typed API client + utilities
│       └── store/    # Zustand auth store
└── ml/               # Offline training scripts (TabNet / XGBoost)
    └── train_tabnet.py
```

## Quick Start

### Prerequisites
- Python ≥ 3.11
- Node.js ≥ 20
- PostgreSQL ≥ 15

### 1. Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — set DATABASE_URL, SECRET_KEY, etc.

# Run database migrations
alembic upgrade head

# Seed first admin user
python seed_admin.py

# Start dev server
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/api/docs

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:3000

Default login (after seeding):
- Email: `admin@cardnet.local`
- Password: `admin_change_me`

### 3. Train a model (optional — required for predictions)

```bash
cd ml
# Download the Kaggle creditcard.csv dataset to ml/data/
python train_tabnet.py
```

This trains an XGBoost pipeline and saves `ml_models/latest.pkl`.  
Register it in the Model Registry via the UI or API, then activate it.

---

## API Endpoints (v1)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/auth/login` | OAuth2 login (form) |
| `POST` | `/api/v1/auth/refresh` | Refresh access token |
| `GET` | `/api/v1/auth/me` | Current user info |
| `GET` | `/api/v1/dashboard/summary` | KPI counters |
| `GET` | `/api/v1/dashboard/volume-trend` | Transaction volume time series |
| `GET` | `/api/v1/dashboard/fraud-trend` | High-risk count time series |
| `GET` | `/api/v1/dashboard/risk-distribution` | Risk tier counts |
| `GET` | `/api/v1/dashboard/recent-alerts` | Latest high-risk predictions |
| `GET` | `/api/v1/dashboard/model-health` | Channel availability |
| `GET` | `/api/v1/transactions` | Paginated transaction list |
| `GET` | `/api/v1/transactions/{id}` | Transaction detail + predictions |
| `POST` | `/api/v1/predictions/single` | Score a single feature vector |
| `GET` | `/api/v1/predictions/{id}` | Get prediction by ID |
| `POST` | `/api/v1/batch/upload` | Upload CSV for batch screening |
| `GET` | `/api/v1/batch/jobs` | List batch jobs |
| `GET` | `/api/v1/batch/jobs/{id}` | Get job status |
| `GET` | `/api/v1/models` | List model versions |
| `POST` | `/api/v1/models` | Register model version (admin) |
| `PUT` | `/api/v1/models/{id}/activate` | Activate a model (admin) |
| `GET` | `/api/v1/evaluation/runs` | List evaluation runs |
| `POST` | `/api/v1/evaluation/runs` | Trigger evaluation (admin) |
| `GET` | `/api/v1/evaluation/runs/{id}` | Get run with curves |
| `GET` | `/api/v1/investigations` | List investigations |
| `POST` | `/api/v1/investigations` | Open investigation |
| `GET` | `/api/v1/investigations/{id}` | Investigation detail + timeline |
| `POST` | `/api/v1/investigations/{id}/events` | Add event/resolve |
| `GET` | `/api/v1/audit` | Audit log (admin only) |
| `GET` | `/api/v1/users` | List users (admin only) |
| `POST` | `/api/v1/users` | Create user (admin only) |
| `PUT` | `/api/v1/users/{id}` | Update user (admin only) |

## Frontend Pages

| Route | Description | Roles |
|-------|-------------|-------|
| `/login` | Authentication | All |
| `/dashboard` | KPI cards, charts, alerts | All |
| `/transactions` | Transaction list with filters | All |
| `/transactions/[id]` | Detail + SHAP attributions | All |
| `/predictions` | Manual single-transaction scoring | Analyst, Admin |
| `/batch` | CSV upload + job status | Analyst, Admin |
| `/evaluation` | Evaluation lab, PR/ROC curves | All |
| `/models` | Model registry | All (activate: Admin) |
| `/investigations` | Case management list | Analyst, Admin |
| `/investigations/[id]` | Case detail + timeline | Analyst, Admin |
| `/audit` | System audit log | Admin |
| `/users` | User management | Admin |
| `/settings` | Profile + system status | All |

## Running Tests

```bash
cd backend
pytest -v --cov=app --cov-report=term-missing
```

## User Roles

| Role | Capabilities |
|------|-------------|
| `viewer` | Read-only: dashboard, transactions, evaluation, models |
| `analyst` | + Predictions, batch screening, investigations |
| `admin` | + User management, audit log, model activation, trigger evaluation |

---

## Dataset

Uses the [ULB Machine Learning Group creditcard dataset](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud):
- 284,807 transactions (492 fraud, 284,315 legitimate)
- Features: Time, V1–V28 (PCA-transformed), Amount, Class
- Highly imbalanced — evaluation metrics use PR-AUC as primary metric

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI 0.115, Python 3.11 |
| ORM | SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 15 |
| Migrations | Alembic |
| Auth | JWT (python-jose) + bcrypt |
| ML | XGBoost, scikit-learn, SHAP |
| Frontend | Next.js 16, React 19, TypeScript |
| Styling | Tailwind CSS 4 |
| State | Zustand (auth), TanStack Query (server state) |
| Charts | Recharts |
| Animations | Framer Motion |
