# Kisii University AI Academic Adviser — full stack (React + Django)

Four portals on one backend: **Student, Lecturer, HOD, Staff (ICT/Registry)**.
Core idea: nothing proceeds until the data is complete and correct. The Django rules engine
(`backend/portal/rules.py`) is the single source of truth; the React UI only shows the verdicts early.

## Run it (two terminals)

**Backend**
```
cd backend
python -m venv venv
venv\Scripts\activate          # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
python manage.py makemigrations portal
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```
API at http://localhost:8000/api/

**Frontend**
```
cd frontend
npm install
npm run dev
```
App at http://localhost:5173  (set `VITE_API_URL` if the API is elsewhere; see `.env.example`).

## Demo accounts — DEMO ONLY
`seed_demo` creates fake people that all share the password **demo12345**. Never use it with real data
(the command refuses to run when `DJANGO_DEBUG=0`).

| Role | Username | Try this |
|---|---|---|
| Student | `brian` (or reg no `CIT/0001/2024`) | CIT 305 blocked (needs CIT 201); next-of-kin phone missing blocks registering |
| Student | `amina` | KES 15,000 fee balance blocks registration |
| Student | `peter` | One mark *pending* (approved reason), one *blocked* (value is on the score sheet) |
| Lecturer | `lec1`, `lec2` | Enter marks for own units; request an exception for a missing mark |
| HOD | `hod1` | Approve/reject exceptions and waivers; at-risk students |
| Staff | `staff1` | Validation queue, edit marks, release transcripts, graduation clearance, users/roles, audit log |

## Marks rule (enforced server-side)
- CAT and exam both captured → **complete**
- Missing + HOD/staff-approved reason → **pending** (allowed, not a final grade)
- Missing, no reason → **blocked**
- Missing but the value is on the score sheet → **blocked, even with a reason** (capture it)
- You cannot approve a request you raised yourself. Every gate decision goes to an append-only audit log.

## Optional AI wording
Without a key the adviser answers from templates built from the student's own records and cites rule codes.
Set `ANTHROPIC_API_KEY` to let Claude phrase those facts more naturally (it is told to use only the facts and
never promise exceptions). Anything outside the records is escalated to a human.

## Tests
```
cd backend
python manage.py test portal
```

## Honest status
Written and syntax-checked, but **not run end to end** in the environment I built it in (no Django/npm installs
there). The pure rules tests pass; the API tests (`portal/tests/test_api.py`) and the UI still need your first run.
Expect to fix small things on first launch, and send me the error text if so.

## Deploy
Frontend → Vercel (set `VITE_API_URL`). Backend → Render/Railway (set `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`,
`DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, Postgres vars). Not Vercel for Django.
