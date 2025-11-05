# HL7 Yeeter - AI Coding Agent Instructions

## Project Overview
Full-stack HL7 message simulator with AI analysis (Google Gemini), MLLP client/server, DICOM generation, and multi-step simulation orchestration. Flask/React app deployed via Docker Compose with PostgreSQL backend.

## Architecture & Data Flow

### Backend Structure (Flask)
- **App Factory**: `app/__init__.py` - Creates Flask app, registers blueprints, initializes extensions (SQLAlchemy, SocketIO, JWT, CORS)
- **Blueprint Routes**: `app/routes/*_routes.py` - Modular API endpoints (auth, mllp, admin, simulator, listener, endpoints, util)
- **Models**: `app/models.py` - 14 SQLAlchemy models (User, Endpoint, SimulationTemplate, SimulationRun, Hl7Version, etc.)
- **Schemas**: `app/schemas.py` - Pydantic validation for all API inputs/outputs
- **CRUD Operations**: `app/crud.py` - Database access layer, business logic
- **Simulation Engine**: `app/util/simulation_runner.py` - Orchestrates multi-step workflows (HL7/DICOM generation, MLLP/DICOM sending, waits, context extraction)

### Frontend Structure (React + Vite)
- **Entry**: `src/main.jsx` - React root, Google OAuth provider, AuthProvider wrapper
- **Router**: `src/App.jsx` - Route protection based on `useAuth()` hook
- **Main UI**: `src/components/HL7Parser.jsx` - Interactive parser/editor with drag-drop, MLLP client, AI analysis
- **API Layer**: `src/api/*.js` - Centralized API functions with `getAuthHeaders()` and `handleResponse()` utilities
- **Auth Context**: `src/context/AuthContext.jsx` - Global auth state, stores `authToken` and `userData` in localStorage

### Real-Time Communication
- **SocketIO**: Used for simulation progress, terminology refresh status, listener messages
- **Rooms**: Simulation runs use room pattern: `simulation_run_{run_id}`
- **Events**: `simulation_event`, `terminology_status`, `listener_message`, `listener_ack`

## Critical Conventions

### Standards & Compliance
- Treat IHE integration profiles as the default rule set for workflow and data flow decisions; flag any planned deviation for explicit discussion before implementation.

### Authentication & Storage
- **Token Key**: ALWAYS use `authToken` (not `token`) for localStorage
- **Headers**: Use `src/api/apiUtils.js::getAuthHeaders()` - automatically adds JWT Bearer token
- **Protected Routes**: Backend uses `@jwt_required()` decorator; frontend checks `isAuthenticated` from AuthContext

### Database & Models
- **Connection**: PostgreSQL via SQLAlchemy, connection string in docker-compose.yml env vars
- **Migrations**: Not using Flask-Migrate - schema changes require manual updates to `app/models.py`
- **Foreign Keys**: All relationships use SQLAlchemy ORM (e.g., `User.templates`, `SimulationTemplate.steps`)

### API Patterns
- **Blueprint Prefixes**: 
  - `/api/auth/*` - Authentication (login, register, Google OAuth)
  - `/api/admin/*` - Admin features (requires `is_admin=True`)
  - `/api/*` - General endpoints (MLLP, parsing, analysis)
- **Response Format**: JSON with `error` or `msg` keys for errors, otherwise data directly
- **Validation**: Pydantic schemas validate ALL incoming requests

### Google Gemini Integration
- **Dynamic Models**: Fetches available models from `genai.list_models()`, cached 1 hour
- **Filtering**: Excludes models with "image-generation" in name
- **Endpoint**: `/api/available_models` returns current list
- **Environment**: Requires `GOOGLE_API_KEY` in `.env`, warns if missing but doesn't crash

### HL7 & MLLP
- **Definitions**: Stored in `segment-dictionary/{version}/` as JSON files, loaded into `Hl7Version` and `Hl7TableDefinition` models
- **MLLP Protocol**: VT (`\x0b`) + message + FS (`\x1c`) + CR (`\x0d`)
- **Parser**: `app/util/hl7_parser.py` uses HL7 definitions for field validation and description lookups
- **Listener**: Background thread in `app/util/mllp_listener.py`, stores messages in `ReceivedMessage` model

### Simulation Engine Workflow
1. User creates `SimulationTemplate` with multiple `SimulationStep` entries
2. Each step has `step_type`: GENERATE_HL7, GENERATE_DICOM, SEND_MLLP, SEND_DICOM, WAIT, DMWL_FIND, MPPS_UPDATE
3. `SimulationRunner` executes steps sequentially, maintains `run_context` dict for context extraction
4. Events logged to `SimulationRunEvent` and emitted via SocketIO for real-time UI updates
5. Uses Faker for patient data generation, persists to `run_context` across steps

## Development Workflows

### Local Docker Compose
```bash
# Full stack with Docker
docker compose up -d --build

# Frontend dev (hot reload)
npm run dev

# Backend dev (requires Python 3.11+)
source venv/bin/activate
flask run --port 5001
```

### Database Access
```bash
# Connect to Postgres (exposed on port 5434)
docker exec yeeter_postgres psql -U yeeter_user -d hl7_yeeter_db

# Common queries
SELECT id, username, email, is_admin FROM users;
SELECT id, version, is_enabled FROM hl7_versions;
```

### k3s / Kubernetes Deployment
- Use manifests in `k8s/` (backend `app.yaml`, frontend `frontend.yaml`, configmap/secret files) targeting the `yeeter` namespace.
- Rebuild and load images with `scripts/build_and_deploy_k3s.sh`; the script builds backend/frontend Docker images, imports them into the local k3s containerd (`sudo k3s ctr images import -`), and restarts deployments.
- Frontend deployment binds `hostPort: 5175`. During rollout, delete the previous pod (`kubectl -n yeeter delete pod <old-frontend-pod>`) if the new replica remains Pending due to hostPort contention.
- Verify updates with `kubectl -n yeeter rollout status deployment/yeeter-app` and `kubectl -n yeeter rollout status deployment/yeeter-frontend`; exposed NodePorts remain 30001 (backend) and 30175 (frontend).
- For any new workload (e.g., worker service), follow the same workflow: build locally, `docker save | sudo k3s ctr images import -`, and restart the deployment.

### Testing API Endpoints
```bash
# Login and get token
TOKEN=$(curl -s -X POST https://yeet.trazen.org/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "test", "password": "test"}' | \
  jq -r '.access_token')

# Test authenticated endpoint
curl -H "Authorization: Bearer $TOKEN" https://yeet.trazen.org/api/available_models
```

### Common Issues & Fixes
- **401 on API calls**: Check localStorage key is `authToken` not `token`
- **SocketIO not connecting**: Verify `VITE_API_URL` env var matches backend URL
- **Models not loading**: Backend needs `GOOGLE_API_KEY` in `.env`, check logs for API errors
- **MLLP listener fails**: Ensure port isn't in use, check Docker network configuration
- **Simulation stuck**: Check `SimulationRunEvent` table for error details, verify endpoints are reachable

## Key Files to Check First
- Backend changes: `app/__init__.py` (app factory), `app/routes/*_routes.py` (specific feature)
- Frontend changes: `src/components/HL7Parser.jsx` (main UI), `src/api/*.js` (API layer)
- Database schema: `app/models.py` (all tables), `app/schemas.py` (validation)
- Real-time features: `app/util/simulation_runner.py` (simulations), `app/util/mllp_listener.py` (MLLP server)

## Frontend Component Patterns

### State Management
- **No Redux/Context for most state**: Local component state with `useState`, `useRef` for non-reactive values
- **Auth State**: Global via `AuthContext` - access with `useAuth()` hook
- **Parent-Child Communication**: Props drilling for callbacks (e.g., `onFieldUpdate`, `onFieldMove`, `onShowDictionary`)
- **Refs for Performance**: `useRef` for scroll position (`scrollRef`), debounce timers (`debounceTimerRef`), socket instances

### Drag-and-Drop Field Editing
- **Library**: `react-dnd` with `HTML5Backend`
- **Pattern**: Wrap draggable area in `<DndProvider backend={HTML5Backend}>`
- **Drag Source**: `useDrag()` in `FieldRow.jsx` - only enabled if field has non-empty value
- **Drop Target**: `useDrop()` accepts drops, calls `onFieldMove(source, destination)` with segment/field indices
- **Visual Feedback**: `isDragging` opacity changes, `cursor-grab` when draggable

### Real-Time Field Updates
- **Double-Click to Edit**: `onDoubleClick` sets `isEditing` state in `FieldRow.jsx`
- **Component Fields**: HL7 fields with `^` separators shown as individual inputs (e.g., PID-5 name components)
- **Sync Pattern**: `useEffect` syncs `field.components` prop to local `componentValues` state array
- **Blur to Save**: `onBlur` calls `onFieldUpdate(segmentIndex, fieldIndex, newValue)` propagated up to `HL7Parser.jsx`
- **Debounced Rebuild**: `updateHl7MessageText()` uses 300ms debounce to rebuild full HL7 message from segments

### Conditional Rendering & Loading States
- **Processing Overlay**: `isProcessing` shows `<YeetLoader />` with opacity transition on parent
- **Empty States**: Show placeholder messages when no data (e.g., "No message parsed yet")
- **Conditional UI**: `isAuthenticated` from `useAuth()` controls feature visibility, unauthenticated users see `<AuthTooltip />`
- **Tab-Based Views**: `activeTab` state controls sender/listener/simulator panels

### Toast Notifications
- **Library**: `react-hot-toast` configured in `App.jsx` with dark theme
- **Usage**: `toast.error()`, `toast.success()` for user feedback
- **Positioning**: `position="top-center"` with custom gray background

### Modal Patterns
- **State Control**: `isOpen` boolean state, handler functions for open/close
- **Example**: `SaveTemplateModal` - `isSaveModalOpen` state, `setIsSaveModalOpen(false)` on close
- **Error Display**: Modal-local error state (e.g., `saveTemplateError`) cleared on open

### Tooltip System
- **Custom Implementation**: `Tooltip.jsx` with `tooltipContent` state in parent
- **Trigger**: `onMouseEnter`/`onMouseLeave` on field rows
- **Position**: `tooltipPos` tracks mouse with `onMouseMove` handler
- **Content Types**: Error tooltips (validation) vs info tooltips (field descriptions)
- **Toggle**: `showTooltips` boolean allows user to disable

### Table/List Rendering
- **Segment Selector**: Left sidebar with buttons, `selectedSegmentIndex` controls displayed segment
- **Field Table**: Semantic `<table>` with `<thead>`/`<tbody>`, fixed column widths
- **Conditional Rows**: Filter with `showEmpty` toggle to hide empty fields
- **Error Badges**: Count errors per segment, show in red badge on selector button

## Code Style & Patterns
- **Python**: Follow PEP 8, use type hints where possible, log at INFO level
- **JavaScript**: ES6+, functional components with hooks, TailwindCSS for styling
- **Error Handling**: Backend logs errors then returns JSON with `error` key; frontend shows toast notifications
- **Comments**: Use `# ---` section headers in Python, `// ---` in JS for major sections
- **File Headers**: Include `# --- START OF FILE path/to/file.py ---` at top of files

## Deployment Context
- Production: `https://yeet.trazen.org` behind nginx proxy (network: `npm_web`)
- Database: PostgreSQL volume `databases_postgres_data` persists across restarts
- Environment: All config via `.env` file, no hardcoded secrets
- Networks: `yeeter_network` (internal), `npm_web` (nginx proxy), `axiom_shared_network` (external services)
