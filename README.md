# The Dirty Laundry V2 — AI Virtual Try-On Platform

> **Production-grade virtual try-on pipeline** for The Dirty Laundry streetwear brand.
> Upload a photo, pick a garment, get a photorealistic try-on in seconds — with 360° 3D mesh and orbital video.

---

## Tech Stack

### Frontend

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.3.1 | Component UI library |
| TypeScript | 5.6.2 | Static type safety |
| Vite | 6.0.0 | Build tool + HMR dev server |
| Three.js | 0.170.0 | WebGL 3D engine |
| React Three Fiber | 8.17.0 | Declarative R3F wrapper for Three.js |
| React Three Drei | 9.120.0 | R3F helpers (OrbitControls, ContactShadows, Grid, Environment, useGLTF) |
| React Three Postprocessing | 2.16.0 | SMAA anti-aliasing post-processing |
| Framer Motion | 11.15.0 | Spring physics animations + layout transitions |
| Tailwind CSS | 3.4.17 | Utility-first styling + dark theme tokens |
| Zustand | 5.0.0 | Lightweight state management |
| React Router | 6.28.0 | Client-side routing |
| Axios | 1.7.0 | HTTP client |
| Supabase JS | 2.47.0 | Auth + Realtime subscriptions |
| react-dropzone | 14.3.0 | Drag-and-drop file uploads |
| ESLint | 9.13.0 | Code linting |
| PostCSS | 8.4.49 | CSS transforms |
| Autoprefixer | 10.4.20 | Vendor prefix insertion |

### Backend

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.12+ | Runtime |
| FastAPI | 0.115.x | Async REST framework |
| Uvicorn | 0.34.x | ASGI server |
| Pydantic | 2.10.x | Data validation + settings |
| httpx | 0.28.x | Async HTTP client |
| ARQ | 0.26.x | Async Redis job queue |
| Redis | 7 Alpine | Queue broker + cache |
| tenacity | 9.0.x | Retry with exponential backoff |
| pybreaker | 1.2.x | Circuit breaker pattern |
| structlog | 24.4.x | Structured JSON logging |
| Pillow | 11.1.x | Image processing + resizing |
| MediaPipe | 0.10.x | On-device body landmark estimation |

### AI / ML Providers

| Provider | Model | Purpose |
|----------|-------|---------|
| **Fashn.ai** (Primary) | tryon-v1.6 | Virtual garment synthesis |
| **Fashn.ai** (Primary) | image-to-video | 360° orbital video generation |
| **Replicate** (Fallback) | IDM-VTON | First garment synthesis fallback |
| **Replicate** (Fallback) | Flux-VTON | Second garment synthesis fallback |
| **Replicate** | TRELLIS | 3D `.glb` mesh reconstruction |
| **Replicate** (Fallback) | Wan 2.2 I2V | Fallback 360° video generation |
| HuggingFace | HMR 2.0 | Full-body pose estimation |

### Infrastructure

| Technology | Purpose |
|------------|---------|
| Docker Compose | Multi-container orchestration (4 services) |
| Nginx | Reverse proxy + static asset serving + gzip |
| Supabase | Auth · Postgres · Storage (signed URLs) · Realtime (WebSocket) |

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

### Circuit Breakers (pybreaker)

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
HeroLanding → "Get Started" (sign-in modal)  or  "Browse Collection" (catalog only)
```
- Full-screen hero with gradient headline, animated badge, feature pills
- "My Looks" nav item is dimmed
- Clicking "Continue with Selected" or "Start Try-On" prompts sign-in

### Authenticated User
```
GarmentCatalog → Photo Upload → Processing (realtime) → Result (Photo / 3D / 360°)
```
- Full 4-step pipeline access
- My Looks history with hover overlays
- Empty state links to "Start a Try-On"

---

## Animations & Transitions

The entire UI is choreographed with **Framer Motion 11.15** spring physics, **Three.js** real-time 3D, and custom **CSS keyframes**.

### Framer Motion Animations

| Component | Animation | Config |
|-----------|-----------|--------|
| **HeroLanding** | Container fade-in + slide-up | `opacity: 0→1, y: 30→0` · `duration: 0.7s, ease: easeOut` |
| **HeroLanding** | Badge zoom-in | `scale: 0.9→1, opacity: 0→1` · `delay: 0.2s` |
| **HeroLanding** | Feature pills fade-in | `opacity: 0→1` · `delay: 0.5s` |
| **HeroLanding** | CTA button press | `whileHover: scale 1.03` · `whileTap: scale 0.97` |
| **Header** | Nav pill indicator | `layoutId="nav-pill"` · `spring, bounce: 0.2, duration: 0.4s` |
| **Header** | User dropdown | `opacity: 0→1, y: -8→0` · `AnimatePresence` exit |
| **AuthModal** | Tab indicator | `layoutId="auth-tab"` · `spring, bounce: 0.2, duration: 0.4s` |
| **AuthModal** | Modal overlay | `scale: 0.9→1, opacity: 0→1` · `AnimatePresence` |
| **ConsentModal** | Modal entry | `scale: 0.9→1, opacity: 0→1` · `AnimatePresence` |
| **GarmentCatalog** | Card entrances | Staggered `delay: idx * 0.05` · `opacity: 0→1, y: 20→0` |
| **GarmentCatalog** | Selection checkmark | `scale: 0→1` · spring animation |
| **MyLooks** | History card grid | Staggered `delay: idx * 0.05` · `opacity: 0→1, y: 20→0` |
| **MyLooks** | Delete/hover overlays | `opacity: 0→1` · CSS `duration: 300ms` |
| **ViewModeSwitcher** | Tab active pill | `layoutId="viewmode-pill"` · `spring, bounce: 0.2, duration: 0.4s` |
| **ProgressTracker** | Progress bar fill | `width: 0→{progress}%` · `duration: 0.5s, ease: easeOut` |
| **ProgressTracker** | Active step pulse | `scale: [1, 1.3, 1]` · `duration: 1s, repeat: Infinity` |
| **ProgressTracker** | Error message | `opacity: 0→1, y: -8→0` |
| **TryOnFlow** | Partial result appear | `scale: 0.95→1, opacity: 0→1` |
| **PhotoView** | Image fade-in | `opacity: 0→1` · `duration: 0.5s` |
| **VideoPlayer** | Video fade-in | `opacity: 0→1` · `duration: 0.5s` |

### Layout Animations (Shared Layout)

Three `layoutId`-driven pill indicators provide smooth spring-physics sliding between active states:

- **`nav-pill`** — Header navigation (Catalog / Try On / My Looks)
- **`auth-tab`** — Auth modal (Sign In / Sign Up)
- **`viewmode-pill`** — Result viewer (Photo / 3D / 360°)

All use `type: 'spring', bounce: 0.2, duration: 0.4` for consistent feel.

### CSS Animations & Effects

| Effect | Implementation |
|--------|---------------|
| **Progress bar stripes** | `@keyframes stripe-move` — diagonal stripes scrolling at 0.5s linear infinite |
| **Active step pulse** | Tailwind `animate-pulse` (3s cubic-bezier cycle) on badge dot |
| **Slow pulse glow** | Custom `pulse-slow` — `pulse 3s cubic-bezier(0.4,0,0.6,1) infinite` |
| **Slow spin** | Custom `spin-slow` — `spin 8s linear infinite` |
| **Glass morphism cards** | `backdrop-blur-xl` + `bg-white/5` + `border-white/10` |
| **Brand gradient** | `linear-gradient(to right, #c084fc, #9333ea)` (brand-400 → brand-600) |
| **Glow shadows** | `0 0 40px rgba(168,85,247,0.15)` + `0 0 80px rgba(168,85,247,0.05)` |
| **Sticky header blur** | `bg-surface-950/80 backdrop-blur-xl border-white/5` |
| **Custom scrollbar** | 6px width, `rgba(255,255,255,0.15)` track, 3px border-radius |
| **Dropzone active state** | Border transitions to `brand-400` + `bg-brand-400/5` on drag |
| **Hero background glows** | 600px + 400px blurred circles (`blur-[120px]`, `blur-[100px]`) |

---

## Three.js / React Three Fiber — 3D Viewer

The 3D result viewer renders `.glb` meshes with physically-based materials inside an interactive R3F `<Canvas>`.

### Scene Configuration

```
Canvas: antialias · alpha · high-performance · preserveDrawingBuffer
DPR:    [1, 2] (adaptive pixel ratio)
Tone:   ACES Filmic (industry-standard color grading)
Shadows: enabled
```

### Camera & Controls

| Feature | Value |
|---------|-------|
| Type | Perspective (default) |
| Orbit Controls | Full pan + zoom + rotate |
| Damping | 0.05 factor (smooth inertia) |
| Zoom range | 1× – 8× |
| Vertical limits | 18° min – 153° max (prevents flipping) |
| Auto-rotate | Optional continuous rotation |

### Lighting Rig

| Light | Position | Intensity | Shadows |
|-------|----------|-----------|---------|
| Environment (preset) | — | 1.0 | — |
| Ambient | — | 0.3 | — |
| Directional (key) | `[5, 5, 5]` | 0.8 | 1024×1024 shadow map |
| Directional (fill) | `[-3, 3, -3]` | 0.3 | — |
| Contact shadows | Ground plane | 0.4 opacity | blur: 2, scale: 10 |

### GLB Model Processing

1. **Auto-centering** — Bounding box calculation → centers to origin
2. **Normalized scaling** — Scaled to ~2 units height via `2 / maxDimension`
3. **PBR material upgrade** — All `MeshStandardMaterial` → `MeshPhysicalMaterial`:
   - Preserves: albedo, normal, roughness, metalness, AO, emissive maps
   - Adds: clearcoat (0.05), clearcoat roughness (0.3), env map intensity (1.2)
   - Double-sided rendering, cast + receive shadows
4. **Idle rotation** — Continuous Y-axis spin at 0.02 rad/frame (~5.2s per revolution)

### Post-Processing

- **SMAA** anti-aliasing via `@react-three/postprocessing` (disabled on low-quality setting)
- Optional infinite grid overlay (0.5-unit cells, 2-unit sections, fade at 10 units)

---

## Tailwind CSS Theme

### Color System

**Brand (Purple):** 50 `#faf5ff` → 500 `#a855f7` → 950 `#3b0764`
**Surface (Dark):** 50 `#fafafa` → 900 `#171717` → 950 `#0a0a0a`

### Typography

| Family | Font | Fallbacks |
|--------|------|-----------|
| `sans` | Inter | ui-sans-serif, system-ui, -apple-system |
| `display` | Space Grotesk | ui-sans-serif, system-ui |

---

## Database Schema (Supabase)

```sql
-- Users: Supabase Auth (auth.users)

-- Consent tracking
consent_records (user_id, consent_type, ip_address, user_agent, granted_at)

-- Garment catalog (13 seeded products from thedirtylaundry.pk)
garments (id, slug, name, brand, category, color, price_pkr, image_url, ...)

-- Try-on pipeline jobs
tryon_jobs (id, user_id, garment_id,
            status [pending | processing | completed | failed],
            result_photo_url, result_video_url, result_mesh_url,
            model_used, processing_time_ms, ...)
```

---

## API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/v1/auth/signup` | — | Create account |
| `POST` | `/api/v1/auth/login` | — | Sign in |
| `POST` | `/api/v1/auth/logout` | Bearer | Sign out |
| `POST` | `/api/v1/auth/consent` | Bearer | Record GDPR consent (`consent_given` + `privacy_acknowledged`) |
| `GET` | `/api/v1/garments` | — | List garments (filterable by `category`) |
| `GET` | `/api/v1/garments/{id}` | — | Single garment details |
| `POST` | `/api/v1/garments` | Bearer | Upload new garment (admin) |
| `POST` | `/api/v1/tryon` | Bearer | Start VTO pipeline (multipart: `selfie` + `fullbody` files + `garment_id`) |
| `GET` | `/api/v1/tryon/{job_id}` | Bearer | Poll job status |
| `GET` | `/api/v1/tryon/history` | Bearer | User's try-on history (returns `looks` array) |
| `DELETE` | `/api/v1/tryon/{job_id}` | Bearer | Delete a look |
| `GET` | `/api/v1/health` | — | Service health + circuit breaker states |
| `GET` | `/api/v1/metrics` | — | Prometheus-format metrics |

---

## Docker Compose Services

| Service | Image / Build | Port | Purpose |
|---------|---------------|------|---------|
| **redis** | `redis:7-alpine` | 6379 | Job queue + cache (256MB LRU, AOF persistence) |
| **backend** | `./backend/Dockerfile` | 8000 | FastAPI REST API |
| **worker** | `./backend/Dockerfile` | — | ARQ async pipeline worker |
| **frontend** | `./frontend/Dockerfile` | 80 | Nginx + static SPA bundle |

### Nginx Configuration

- **Gzip:** text, JS, JSON, WASM, glTF, SVG (min 1024 bytes)
- **Static caching:** `/assets/` → 1 year immutable; `.glb/.gltf/.hdr` → 7 days
- **API proxy:** `/api/` → `backend:8000` (120s read timeout, 15MB upload limit)
- **SPA fallback:** `try_files $uri $uri/ /index.html`
- **Security headers:** X-Frame-Options, X-Content-Type-Options, Referrer-Policy, X-XSS-Protection

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
│   │   ├── index.css                 # Tailwind + custom tokens + glass effects
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
│   │   │       ├── Scene.tsx         # R3F canvas + controls + post-processing
│   │   │       ├── TryOnModel.tsx    # GLB mesh loader + PBR upgrade
│   │   │       └── VideoPlayer.tsx   # Looping MP4 360° player
│   │   ├── hooks/
│   │   │   ├── useConsent.ts         # Consent status hook
│   │   │   ├── useGarments.ts        # Garment fetch/filter hook
│   │   │   └── useTryOnRealtime.ts   # Supabase Realtime subscription
│   │   ├── lib/
│   │   │   ├── api.ts               # Axios API client
│   │   │   └── supabase.ts          # Supabase client init
│   │   ├── stores/
│   │   │   ├── useAuthStore.ts      # Auth state (Zustand)
│   │   │   ├── useTryOnStore.ts     # Try-on pipeline state
│   │   │   └── useViewerStore.ts    # 3D viewer state (camera, quality, grid)
│   │   └── types/
│   │       └── index.ts             # Shared TypeScript interfaces
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
# Frontend: http://localhost:80
# API Docs: http://localhost:8000/api/docs
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
Every external API result (images, meshes, videos) is immediately downloaded and re-uploaded to Supabase Storage with signed URLs. The frontend never receives ephemeral external URLs.

### Zero-Polling Realtime
Job status updates flow through Supabase Realtime (Postgres → WebSocket). Polling is only a fallback if Realtime is unavailable.

### Graceful Degradation
Each pipeline layer can fail independently. If 360° video fails, the 2D photo still works. If 3D mesh fails, the photo view is available. The UI adapts the ViewModeSwitcher to only show available result types.

### Circuit Breakers
Each external API has its own circuit breaker (pybreaker). When a service is down, requests fail fast instead of queuing up. After the reset timeout, the circuit half-opens to test recovery.

### PBR Material Upgrade
Raw `.glb` meshes from TRELLIS use basic `MeshStandardMaterial`. The viewer automatically upgrades every mesh to `MeshPhysicalMaterial` with clearcoat, environment mapping, and double-sided rendering for realistic fabric appearance.

---

## License

Private — The Dirty Laundry. All rights reserved.
