# The Dirty Laundry V2 — AI Virtual Try-On

Production-grade Virtual Try-On (VTO) system inspired by Zara × DRESSX's 5-layer pipeline architecture.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│   Frontend   │────▶│  FastAPI     │────▶│  ARQ Worker   │
│  React + R3F │◀────│  Backend     │◀────│  (Pipeline)   │
└─────────────┘     └──────┬──────┘     └──────┬───────┘
       │                   │                    │
       │            ┌──────┴──────┐      ┌──────┴───────┐
       │            │  Supabase   │      │  External AI  │
       └───────────▶│  (Auth/DB/  │      │  APIs         │
                    │   Storage/  │      │  • HMR 2.0    │
                    │   Realtime) │      │  • IDM-VTON   │
                    └─────────────┘      │  • TRELLIS    │
                                         │  • Wan 2.2    │
                                         └──────────────┘
```

### 5-Layer Pipeline

| Layer | Component | Service |
|-------|-----------|---------|
| 1 | Body Estimation | MediaPipe (local) → HMR 2.0 (HuggingFace) |
| 2 | Garment Synthesis | IDM-VTON (Replicate, $0.024/run) |
| 3 | 360° Rendering | TRELLIS (.glb mesh) + Wan 2.2 I2V (MP4 video) |
| 4 | Async Infrastructure | ARQ + Redis + Supabase Realtime |
| 5 | Privacy & Consent | GDPR consent flow + Supabase RLS |

**Total pipeline cost:** ~$0.09/run | **Latency:** ~70 seconds

## Tech Stack

### Backend
- **FastAPI** (Python 3.12) — async API with pydantic-settings
- **ARQ** — async job queue on Redis
- **pybreaker** — circuit breakers per external service
- **tenacity** — retry with exponential backoff
- **structlog** — structured JSON logging
- **mediapipe** — local pose validation
- **Supabase** — Auth, Postgres, Storage, Realtime

### Frontend
- **React 18** + TypeScript + Vite 6
- **Three.js** 0.170 + React Three Fiber + drei + postprocessing
- **Zustand 5** — state management
- **Tailwind CSS** — styling with custom design tokens
- **Framer Motion** — animations
- **Supabase JS** — auth + realtime subscriptions

### Infrastructure
- **Docker Compose** — 4 services (backend, worker, redis, frontend/nginx)
- **nginx** — reverse proxy + SPA routing + gzip

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Supabase project (free tier works)
- Replicate API token

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env with your keys
```

### 2. Set up Supabase

Run the SQL schema in your Supabase SQL editor:

```bash
# Copy contents of backend/supabase_schema.sql into Supabase SQL Editor
```

### 3. Start with Docker Compose

```bash
docker compose up --build
```

The app will be available at `http://localhost`.

### Development Mode

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Worker:**
```bash
cd backend
python -m arq app.workers.worker_config.WorkerSettings
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Project Structure

```
the-dirty-laundry-v2/
├── backend/
│   ├── app/
│   │   ├── config.py              # Centralized settings
│   │   ├── main.py                # FastAPI application
│   │   ├── models/                # Pydantic schemas
│   │   │   ├── tryon.py           # Core VTO contracts
│   │   │   ├── garment.py         # Garment catalog
│   │   │   ├── user.py            # Auth & consent
│   │   │   └── health.py          # Health check
│   │   ├── services/              # Business logic
│   │   │   ├── storage_service.py # Supabase Storage (snapshot-first)
│   │   │   ├── auth_service.py    # Supabase Auth + consent
│   │   │   ├── body_estimation_service.py  # Layer 1
│   │   │   ├── synthesis_service.py        # Layer 2
│   │   │   └── video_service.py            # Layer 3
│   │   ├── workers/               # ARQ job queue
│   │   │   ├── tryon_worker.py    # Pipeline orchestrator
│   │   │   └── worker_config.py   # Worker settings
│   │   ├── routers/               # API endpoints
│   │   │   ├── auth.py
│   │   │   ├── tryon.py
│   │   │   ├── garments.py
│   │   │   └── health.py
│   │   ├── middleware/
│   │   │   ├── auth_middleware.py
│   │   │   ├── logging_middleware.py
│   │   │   └── rate_limit.py
│   │   └── utils/
│   │       ├── circuit_breaker.py
│   │       └── monitoring.py
│   ├── supabase_schema.sql
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── index.css
│   │   ├── types/index.ts
│   │   ├── lib/
│   │   │   ├── supabase.ts
│   │   │   └── api.ts
│   │   ├── stores/
│   │   │   ├── useAuthStore.ts
│   │   │   ├── useTryOnStore.ts
│   │   │   └── useViewerStore.ts
│   │   ├── hooks/
│   │   │   ├── useTryOnRealtime.ts
│   │   │   ├── useGarments.ts
│   │   │   └── useConsent.ts
│   │   ├── components/
│   │   │   ├── viewer/
│   │   │   │   ├── Scene.tsx         # R3F canvas + postprocessing
│   │   │   │   ├── TryOnModel.tsx    # GLB loader + PBR materials
│   │   │   │   ├── PhotoView.tsx     # 2D hero image
│   │   │   │   └── VideoPlayer.tsx   # 360° video playback
│   │   │   └── ui/
│   │   │       ├── TryOnFlow.tsx     # Multi-step wizard
│   │   │       ├── ProgressTracker.tsx
│   │   │       ├── GarmentCatalog.tsx
│   │   │       ├── MyLooks.tsx
│   │   │       ├── ConsentModal.tsx
│   │   │       ├── AuthModal.tsx
│   │   │       ├── Header.tsx
│   │   │       ├── FallbackState.tsx
│   │   │       └── ViewModeSwitcher.tsx
│   │   └── vite-env.d.ts
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── nginx.conf
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

## Key Design Decisions

### Snapshot-First Storage
Every external API result (images, meshes, videos) is immediately downloaded and re-uploaded to Supabase Storage. Frontend never receives ephemeral external URLs.

### Zero-Polling Realtime
Job status updates flow through Supabase Realtime (Postgres → WebSocket). Polling is only a fallback if Realtime is unavailable.

### Graceful Degradation
Each pipeline layer can fail independently. If 360° video fails, the 2D hero image still works. If 3D mesh fails, the photo view is available.

### Circuit Breakers
Each external API has its own circuit breaker (pybreaker). When a service is down, requests fail fast instead of queuing up.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/signup` | Create account |
| POST | `/api/v1/auth/login` | Sign in |
| POST | `/api/v1/auth/consent` | Record GDPR consent |
| GET | `/api/v1/garments` | List garment catalog |
| POST | `/api/v1/tryon` | Start try-on pipeline (returns 202) |
| GET | `/api/v1/tryon/{job_id}` | Get job status |
| GET | `/api/v1/tryon/history` | Get user's past looks |
| GET | `/api/v1/health` | Service health + circuit breaker states |

## License

Proprietary — The Dirty Laundry
