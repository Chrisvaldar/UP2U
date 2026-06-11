# UP2U Learn — Backend

## Setup (Day 1)

```powershell
cd UP2U-learn\backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
docker run -d -p 6379:6379 redis
uvicorn main:app --reload
```

Open http://localhost:8000/docs

## Your first task

Implement `GET /` in `main.py` — replace the `NotImplementedError` with a real response.

Then follow [`LEARNING_PLAN.md`](../../LEARNING_PLAN.md) Day 1 checklist.

## Tests

```powershell
pytest
```

Tests are skipped until you implement each endpoint. Remove `pytest.skip(...)` as you go.
