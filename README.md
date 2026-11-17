# ProcessCompass

One React frontend connects to one FastAPI backend. Backend code is grouped by application, with shared Confluence access and settings.

## Project Map

- `frontend/`: React/Vite UI. `src/App.jsx` hosts Compare; `src/ConfigBuilder.jsx` hosts XML workflows.
- `backend/app/applications/create_revision_config/`: page hierarchy and XML generation.
- `backend/app/applications/procman_utilities/`: revision configuration, comparison, and Excel reporting.
- `backend/app/core/` and `backend/app/shared/`: settings, temporary download storage, and Confluence client.
- `migration_reference/` and `MIGRATION_AUDIT.md`: source behavior notes and parity checks.
- `output/`: uploaded revision configuration. Keep this runtime data.

## Run

Start the backend from `backend/` so `OUTPUT_DIR` resolves to the repository's `output/` folder:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173`. The API defaults to `http://127.0.0.1:8000/api/v1/procman`; override it with `VITE_API_BASE_URL`.

## Workflows

1. **Create XML** generates and activates revision configuration; it can also upload existing XML.
2. **Compare** selects a configured process and two revisions, then generates an Excel report.
3. **Compass page tree** generates the separate Compass XML.

Generated Excel and XML files are stored in `%TEMP%\ProcessCompass`. Uploaded revision configuration remains in `output/`. Put Confluence settings in `backend/.env`; never commit credentials. Run backend tests from `backend/` with `python -m pytest`.
