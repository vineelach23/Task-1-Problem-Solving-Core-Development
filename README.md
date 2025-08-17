
# Mini Leave Management System (APIs)

FastAPI-based MVP to manage employees and leave requests.

## Features
- Add/list/get employees
- Apply/list leaves
- Approve/Reject leave
- Fetch leave balance
- Validations: employee not found, leave before joining date, invalid date ranges, insufficient balance, idempotent approval/rejection rules.

## Tech
- FastAPI, Pydantic, SQLAlchemy, SQLite

## Setup
```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Open interactive docs: `http://127.0.0.1:8000/docs`

## API Summary
- `POST /employees` — create employee
- `GET /employees` — list employees
- `GET /employees/{id}` — get employee
- `GET /employees/{id}/balance` — get leave balance
- `POST /employees/{id}/leaves` — apply leave
- `GET /employees/{id}/leaves` — list leaves
- `POST /leaves/{leave_id}/approve` — approve leave
- `POST /leaves/{leave_id}/reject` — reject leave

## Edge Cases Handled
- Leave start before joining date
- End date earlier than start date
- Applying more days than available
- Non-existent employee/leave id
- Prevent re-approval or re-rejection

## How to Scale (50 → 500 employees)
- Swap SQLite with Postgres/MySQL; add DB indexes on email, status.
- Add auth (JWT) and role-based access (Admin/HR/Employee).
- Containerize with Docker; run behind a load balancer; enable connection pooling.
- Background jobs for notifications; rate limiting and request validation.
- Observability: logging + metrics + tracing (e.g., Prometheus + Grafana).

See `docs/` for diagrams.
