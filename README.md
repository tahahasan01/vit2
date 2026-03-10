# The Dirty Laundry V2 — AI Virtual Try-On Platform

> **Production-grade virtual try-on pipeline** for The Dirty Laundry streetwear brand.  
> Upload a photo, pick a garment, get a photorealistic try-on in seconds — with 360° 3D mesh and orbital video.

---

## Tech Stack

| Layer | Technology | Version |
|-------|------------|---------|
| **Backend** | FastAPI + Python | 3.12 |
| **Worker** | ARQ (async Redis queue) | 0.26 |
| **Frontend** | React + TypeScript + Vite | 18.3 / 5.x / 6.x |
| **3D Viewer** | Three.js + React Three Fiber | 0.170 / 8.17 |
| **State** | Zustand | 5.0 |
| **Styling** | Tailwind CSS + Framer Motion | 3.4 / 11.15 |
| **Routing** | React Router | 6.28 |
| **Auth/DB/Storage** | Supabase (Auth, Postgres, Storage, Realtime) | — |
| **Queue** | Redis 7 Alpine | 7.x |
| **VTO Primary** | Fashn.ai (tryon-v1.6, image-to-video) | — |
| **VTO Fallback** | Replicate (IDM-VTON, Flux-VTON, TRELLIS, Wan 2.2) | — |
| **Containerization** | Docker Compose | — |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Vite + React)                  │
│   HeroLanding → GarmentCatalog → PhotoUpload → Result Viewer   │
│   Three.js 3D · VideoPlayer · Zustand stores · Framer Motion   │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST / Realtime
┌────────────────────────────▼────────────────────────────────────┐
│                    FastAPI Backend (:8000)                       │
│  /auth  /tryon  /garments  /health  /metrics                    │
│  Middleware: CORS · Rate-Limit · Logging · Auth                 │
└───────┬──────────┬──────────┬──────────┬───────────────────────┘
        │          │          │          │
   ┌────▼───┐ ┌───▼────┐ ┌──▼───┐ ┌───▼──────────┐
   │Supabase│ │  Redis  │ │Fashn │ │  Replicate   │
   │Auth/DB │ │  Queue  │ │ .ai  │ │  (fallback)  │
   │Storage │ │  (ARQ)  │ │PRIMARY│ │IDM/Flux/Wan │
   └────────┘ └───┬─────┘ └──────┘ └──────────────┘
                  │
            ┌─────▼──────┐
            │ ARQ Worker  │
            │ Pipeline:   │
            │ Body Est →  │
            │ Synthesis → │
            │ 360° Video  │
            └─────────────┘
```

### 5-Layer Pipeline

| Layer | Component | Service |
|-------|-----------|---------|
| 1 | Body Estimation | MediaPipe (local) → HMR 2.0 (HuggingFace) |
| 2 | Garment Synthesis | Fashn.ai (primary) → IDM-VTON → Flux-VTON |
| 3 | 360° Rendering | TRELLIS (.glb mesh) + Fashn/Wan 2.2 I2V (MP4 video) |
| 4 | Async Infrastructure | ARQ + Redis + Supabase Realtime |
| 5 | Privacy & Consent | GDPR consent flow + Supabase RLS |

**Total pipeline cost:** ~$0.09/run | **Latency:** ~70 seconds

### Provider Chain (3-tier Failover)

**Garment Synthesis (VTO):**
1. **Fashn.ai tryon-v1.6** — Primary (if `FASHN_API_KEY` configured)
2. **Replicate IDM-VTON** — First fallback
3. **Replicate Flux-VTON** — Second fallback

**360° Video:**
1. **Fashn.ai image-to-video** — Primary
2. **Replicate Wan 2.2 I2V** — Fallback

**3D Mesh:** Replicate TRELLIS → `.glb` for Three.js viewer

### Circuit Breakers

| Breaker | Fail Max | Reset Timeout | Purpose |
|---------|----------|---------------|---------|
| `fashn_tryon` | 3 | 60s | Fashn VTO |
| `fashn_video` | 3 | 120s | Fashn video |
| `replicate_idm_vton` | 3 | 60s | IDM-VTON |
| `replicate_flux_vton` | 3 | 60s | Flux-VTON |
| `replicate_trellis` | 3 | 120s | TRELLIS 3D |
| `replicate_wan_video` | 3 | 120s | Wan 2.2 video |
| `hmr_body_estimation` | 3 | 60s | HMR 2.0 body |

---

## Frontend UX Flow

### Guest (Not Signed In)
```
HeroLanding → "Get Started" (sign-in modal) or "Browse Collection" (catalog only)
```
- Full-screen hero with gradient headline, animated badge, feature pills
- "My Looks" nav item is dimmed
- Clicking "Continue with Selected" or "Start Try-On" prompts sign-in

### Authenticated User
```
GarmentCatalog → Photo Upload → Processing (realtime) → Result (Photo/3D/Video)
```
- Full 4-step pipeline access
- My Looks history with 3D/video hover overlays
- Empty state links to "Start a Try-On"

### Animations (Framer Motion)
- Page transitions: `opacity + y` spring animations
- Nav pill: `layoutId="nav-pill"` spring bounce
- Cards: Staggered `delay: idx * 0.05` entrance
- Modals: `AnimatePresence` exit animations
- Hero badges: `scale` + delayed `opacity` enters

---

## Database Schema (Supabase)

```sql
-- Users: Supabase Auth (auth.users)
-- Consent tracking
consent_records (user_id, consent_type, ip_address, user_agent, granted_at)

-- Garment catalog (13 seeded products from thedirtylaundry.pk)
garments (id, slug, name, brand, category, color, price_pkr, image_url, ...)

-- Try-on pipeline jobs
tryon_jobs (id, user_id, garment_id, status[pending/processing/completed/failed],
            hero_image_url, mesh_url, video_url, model_used, processing_time_ms, ...)
```

---

## API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/v1/auth/signup` | — | Create account |
| `POST` | `/api/v1/auth/login` | — | Sign in |
| `POST` | `/api/v1/auth/logout` | Bearer | Sign out |
| `POST` | `/api/v1/auth/consent` | Bearer | Record data consent |
| `GET` | `/api/v1/garments` | — | List garments (filterable) |
| `GET` | `/api/v1/garments/{id}` | — | Single garment details |
| `POST` | `/api/v1/garments` | Bearer | Upload new garment (admin) |
| `POST` | `/api/v1/tryon/submit` | Bearer | Start VTO pipeline job |
| `GET` | `/api/v1/tryon/{job_id}` | Bearer | Poll job status |
| `GET` | `/api/v1/tryon/history` | Bearer | User's try-on history |
| `DELETE` | `/api/v1/tryon/{job_id}` | Bearer | Delete a look |
| `GET` | `/api/v1/health` | — | Service health + circuit breakers |
| `GET` | `/api/v1/metrics` | — | Prometheus-format metrics |

---

## Environment Variables

Copy `.env.example` to `.env` and fill in values:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENVIRONMENT` | — | `development` | `development` / `staging` / `production` |
| `USE_STUBS` | — | `true` | Mock all external APIs |
| `LOG_LEVEL` | — | `INFO` | Python log level |
| `CORS_ORIGINS` | — | `localhost:5173,3000` | Comma-separated origins |
| `SUPABASE_URL` | ✅ | — | Supabase project URL |
| `SUPABASE_ANON_KEY` | ✅ | — | Supabase anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ | — | Supabase service role key |
| `FASHN_API_KEY` | ✅ | — | Fashn.ai API key (primary VTO) |
| `FASHN_BASE_URL` | — | `https://api.fashn.ai` | Fashn API base URL |
| `FASHN_TRYON_MODEL` | — | `tryon-v1.6` | Fashn try-on model |
| `FASHN_VIDEO_MODEL` | — | `image-to-video` | Fashn video model |
| `REPLICATE_API_TOKEN` | — | — | Replicate token (fallback) |
| `REDIS_URL` | — | `redis://localhost:6379/0` | Redis connection URL |

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── config.py                 # Pydantic settings (Supabase, Fashn, Replicate, Redis)
│   │   ├── main.py                   # FastAPI app factory + lifespan
│   │   ├── middleware/
│   │   │   ├── auth_middleware.py     # Bearer token → Supabase user
│   │   │   ├── logging_middleware.py  # Structured request logging
│   │   │   └── rate_limit.py         # Token bucket rate limiter
│   │   ├── models/
│   │   │   ├── garment.py            # Garment Pydantic schemas
│   │   │   ├── health.py             # Health/circuit breaker models
│   │   │   ├── tryon.py              # TryOn job schemas
│   │   │   └── user.py               # User/consent schemas
│   │   ├── routers/
│   │   │   ├── auth.py               # /auth/* endpoints
│   │   │   ├── garments.py           # /garments/* endpoints
│   │   │   ├── health.py             # /health + /metrics
│   │   │   └── tryon.py              # /tryon/* endpoints
│   │   ├── services/
│   │   │   ├── auth_service.py       # Supabase Auth wrapper
│   │   │   ├── body_estimation_service.py  # HMR 2.0 body estimation
│   │   │   ├── fashn_service.py      # Fashn.ai VTO + video (PRIMARY)
│   │   │   ├── storage_service.py    # Supabase Storage wrapper
│   │   │   ├── synthesis_service.py  # 3-provider VTO chain
│   │   │   └── video_service.py      # 360° video + 3D mesh
│   │   ├── utils/
│   │   │   ├── circuit_breaker.py    # pybreaker wrapper
│   │   │   └── monitoring.py         # Prometheus metrics
│   │   └── workers/
│   │       ├── tryon_worker.py       # ARQ job handler
│   │       └── worker_config.py      # Worker startup/shutdown
│   ├── Dockerfile
│   ├── requirements.txt
│   └── supabase_schema.sql
├── frontend/
│   ├── src/
│   │   ├── App.tsx                   # Auth-aware routing + loading state
│   │   ├── main.tsx                  # React DOM entry
│   │   ├── index.css                 # Tailwind + custom tokens
│   │   ├── components/
│   │   │   ├── ui/
│   │   │   │   ├── AuthModal.tsx     # Sign-in/sign-up modal
│   │   │   │   ├── ConsentModal.tsx  # GDPR consent flow
│   │   │   │   ├── FallbackState.tsx # Error/empty state card
│   │   │   │   ├── GarmentCatalog.tsx# Garment grid with filters
│   │   │   │   ├── Header.tsx        # Sticky nav + auth menu
│   │   │   │   ├── HeroLanding.tsx   # Guest landing page
│   │   │   │   ├── MyLooks.tsx       # Try-on history grid
│   │   │   │   ├── ProgressTracker.tsx# Pipeline step tracker
│   │   │   │   ├── TryOnFlow.tsx     # 4-step try-on wizard
│   │   │   │   └── ViewModeSwitcher.tsx# Photo/3D/Video toggle
│   │   │   └── viewer/
│   │   │       ├── PhotoView.tsx     # Zoomable photo viewer
│   │   │       ├── Scene.tsx         # R3F canvas + controls
│   │   │       ├── TryOnModel.tsx    # GLB mesh loader
│   │   │       └── VideoPlayer.tsx   # MP4 video player
│   │   ├── hooks/
│   │   │   ├── useConsent.ts         # Consent status hook
│   │   │   ├── useGarments.ts        # Garment fetch/filter hook
│   │   │   └── useTryOnRealtime.ts   # Supabase Realtime sub
│   │   ├── lib/
│   │   │   ├── api.ts               # Axios API client
│   │   │   └── supabase.ts          # Supabase client init
│   │   ├── stores/
│   │   │   ├── useAuthStore.ts      # Auth state (Zustand)
│   │   │   ├── useTryOnStore.ts     # Try-on pipeline state
│   │   │   └── useViewerStore.ts    # 3D viewer state
│   │   └── types/
│   │       └── index.ts             # Shared TypeScript types
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Quick Start

### Prerequisites
- **Node.js 20+** and **npm**
- **Python 3.12+** and **pip**
- **Docker & Docker Compose** (optional, for containerised run)
- **Redis** (or Docker will provide it)

### Development (Local)

```bash
# 1. Clone & configure
cp .env.example .env
# Fill in SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY
# Fill in FASHN_API_KEY (get from app.fashn.ai)
# Set USE_STUBS=false for real inference

# 2. Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 3. Worker (separate terminal)
cd backend
arq app.workers.worker_config.WorkerSettings

# 4. Frontend
cd frontend
npm install
npm run dev
```

### Docker Compose

```bash
docker compose up --build
# Backend:  http://localhost:8000
# Frontend: http://localhost:5173
# Docs:     http://localhost:8000/api/docs
```

---

## Seeded Products

13 real products from [thedirtylaundry.pk](https://thedirtylaundry.pk):

| SKU | Name | Category | Price (PKR) |
|-----|------|----------|-------------|
| tdl-001 | Brooklyn Trousers – Grey | lower_body | 5,490 |
| tdl-002 | Brooklyn Trousers – Black | lower_body | 5,490 |
| tdl-003 | Core Quarter Zipper – Teal Green | upper_body | 5,990 |
| tdl-004 | Core Quarter Zipper – Grey | upper_body | 5,990 |
| tdl-005 | Essential Tracksuit – Mocha Brown | upper_body | 12,490 |
| tdl-006 | Kyoto Summer Hoodie – Beige | upper_body | 6,490 |
| tdl-007 | Oslo Embroidered Hoodie – Black | upper_body | 6,990 |
| tdl-008 | Oslo Embroidered Hoodie – Navy | upper_body | 6,990 |
| tdl-009 | Oslo Embroidered Hoodie – Olive Green | upper_body | 6,990 |
| tdl-010 | Vancouver Quarter Zipper – Black | upper_body | 6,490 |
| tdl-011 | Vancouver Quarter Zipper – Charcoal | upper_body | 6,490 |
| tdl-012 | Vancouver Quarter Zipper – Navy Blue | upper_body | 6,490 |
| tdl-013 | Vancouver Quarter Zipper – Olive Green | upper_body | 6,490 |

---

## Key Design Decisions

### Snapshot-First Storage
Every external API result (images, meshes, videos) is immediately downloaded and re-uploaded to Supabase Storage. Frontend never receives ephemeral external URLs.

### Zero-Polling Realtime
Job status updates flow through Supabase Realtime (Postgres → WebSocket). Polling is only a fallback if Realtime is unavailable.

### Graceful Degradation
Each pipeline layer can fail independently. If 360° video fails, the 2D hero image still works. If 3D mesh fails, the photo view is available.

### Circuit Breakers
Each external API has its own circuit breaker (pybreaker). When a service is down, requests fail fast instead of queuing up.

---

## License

Private — The Dirty Laundry. All rights reserved.
