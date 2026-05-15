# TRID Backend — Bug Fixes Applied

## Files Changed

| File | Fix |
|------|-----|
| `requirements.txt` | Added `razorpay==1.4.2` |
| `app/models/pricing_snapshot.py` | Added missing `import uuid` |
| `app/services/payment_service.py` | Webhook now accepts `raw_body: bytes` instead of `str(dict)` |
| `app/api/v1/endpoints/payments.py` | Passes `await req.body()` (raw bytes) to webhook handler |
| `app/core/middleware.py` | Added `https://trid-2q3h.onrender.com` to `ALLOWED_ORIGINS` |
| `docker-compose.yml` | DB user changed from `postgres` → `trid_user` to match `DATABASE_URL` |
| `alembic/env.py` | Reads `DATABASE_URL_SYNC` from env; imports all models for autogenerate |
| `.env.example` | Added `DATABASE_URL_SYNC`, consistent `trid_user` across both URLs |

## How to Apply

Copy each file to its correct location in your project:

```bash
cp requirements.txt            → requirements.txt
cp app/models/pricing_snapshot.py     → app/models/pricing_snapshot.py
cp app/services/payment_service.py    → app/services/payment_service.py
cp app/api/v1/endpoints/payments.py   → app/api/v1/endpoints/payments.py
cp app/core/middleware.py             → app/core/middleware.py
cp docker-compose.yml                 → docker-compose.yml
cp alembic/env.py                     → alembic/env.py
cp .env.example                       → .env.example (update .env too)
```

## After Applying

```bash
pip install -r requirements.txt    # installs razorpay
cp .env.example .env               # update with real values
docker-compose up -d               # DB user now correct
alembic upgrade head               # env.py now works
uvicorn app.main:app --reload
```

## Frontend Connection

`https://trid-2q3h.onrender.com` is now in `ALLOWED_ORIGINS`.

Frontend should point API calls to your backend URL, e.g.:
```
VITE_API_URL=https://your-backend.onrender.com/api/v1
```
