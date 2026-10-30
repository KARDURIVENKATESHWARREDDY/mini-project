# CARD-Net — Credit Card Fraud Detection Platform

**Institution:** Anurag University, Department of Artificial Intelligence  
**Technology Stack:**
- **Frontend:** Next.js 16 (Turbopack, React 19, TypeScript, Tailwind CSS, TanStack Query, Zustand, Recharts, Framer Motion)
- **Backend:** FastAPI (Python 3.10+, SQLAlchemy, Pydantic v2, SlowAPI rate limiting, Jose JWT authentication)
- **Database:** SQLite (development default `cardnet_dev.db`) / PostgreSQL (production ready)
- **Machine Learning:** XGBoost (primary TAB-Net model), Random Forest, Logistic Regression, SHAP TreeExplainer

---

## Verified Services & Endpoints

| Service | URL | Status | Description |
|---|---|---|---|
| **Frontend UI** | `http://localhost:3000` | Operational | Dashboard, Transactions, Predictions, Investigations, Model Registry, Evaluation Lab, Audit |
| **Backend API Health** | `http://127.0.0.1:8000/health` | Operational | Liveness check |
| **Backend API Docs** | `http://127.0.0.1:8000/api/docs` | Operational | Interactive Swagger / OpenAPI documentation |
| **API Version 1 Root** | `http://127.0.0.1:8000/api/v1` | Operational | All protected and public REST endpoints |

---

## Default Login Credentials

- **Email:** `admin@cardnet.local`
- **Password:** `admin_change_me`
- **Role:** `admin`

---

## Exact PowerShell Commands to Run the Application

### 1. Start the Backend API (FastAPI / Uvicorn)

Open a PowerShell terminal:
```powershell
# Navigate to backend directory
cd "C:\Users\HP\Downloads\mini project\card-net\backend"

# Start Uvicorn on 127.0.0.1:8000
& "C:\Users\HP\Downloads\mini project\.venv\Scripts\uvicorn.exe" app.main:app --host 127.0.0.1 --port 8000
```

### 2. Start the Frontend (Next.js)

Open a second PowerShell terminal:
```powershell
# Navigate to frontend directory
cd "C:\Users\HP\Downloads\mini project\card-net\frontend"

# Start Next.js development server on port 3000
npm run dev
```

Visit **`http://localhost:3000`** in your browser.

---

## Verifying & Testing

### Run Backend Unit & Integration Tests (17 tests)
```powershell
cd "C:\Users\HP\Downloads\mini project\card-net\backend"
& "C:\Users\HP\Downloads\mini project\.venv\Scripts\pytest.exe" -v
```

### Run Frontend Production Build Check
```powershell
cd "C:\Users\HP\Downloads\mini project\card-net\frontend"
npm run build
```

### Re-seed Real Benchmark Data (Optional)
```powershell
cd "C:\Users\HP\Downloads\mini project\card-net\backend"
# Seed 100 benchmark transactions with real predictions & SHAP explanations
& "C:\Users\HP\Downloads\mini project\.venv\Scripts\python.exe" seed_dataset.py --count 100

# Or seed a specific dataset file:
& "C:\Users\HP\Downloads\mini project\.venv\Scripts\python.exe" seed_dataset.py --file ../datasets/sample_batch_mixed_50.csv
```

### Generate Curated Datasets (Optional)
```powershell
cd "C:\Users\HP\Downloads\mini project\card-net"
& "C:\Users\HP\Downloads\mini project\.venv\Scripts\python.exe" generate_datasets.py
```

### Re-train TAB-Net Model (Optional)
```powershell
cd "C:\Users\HP\Downloads\mini project\card-net"
& "C:\Users\HP\Downloads\mini project\.venv\Scripts\python.exe" ml/train_tabnet.py --data ml/data/creditcard.csv --output backend/ml_models
```

---

## Trained Model & Metrics (Held-out Test Split)

- **Model:** XGBoost TAB-Net v1 (500 estimators, scale_pos_weight for class imbalance)
- **Dataset:** Kaggle / ULB Credit Card Fraud Benchmark (284,807 samples, 492 frauds)
- **Test Set:** 56,962 chronologically split samples
- **Accuracy:** 99.96%
- **Precision:** 90.48%
- **Recall:** 76.00%
- **F1 Score:** 82.61%
- **PR-AUC:** 0.8071
- **ROC-AUC:** 0.9894
- **Explainability:** Real SHAP TreeExplainer feature attributions for all 30 features
