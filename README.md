<div align="center">

# ✨ VIT — AI Virtual Try-On

**Upload a photo. Pick a garment. Get a photorealistic try-on in seconds.**
**Photo · 3D Mesh · 360° Video — all from a single pipeline.**

![React](https://img.shields.io/badge/React-18.3-61DAFB?style=for-the-badge&logo=react&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![Three.js](https://img.shields.io/badge/Three.js-0.170-000000?style=for-the-badge&logo=threedotjs&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-6.0-646CFF?style=for-the-badge&logo=vite&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/Tailwind-3.4-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)
![Framer Motion](https://img.shields.io/badge/Framer_Motion-11.15-0055FF?style=for-the-badge&logo=framer&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-Auth%20·%20DB%20·%20Realtime-3FCF8E?style=for-the-badge&logo=supabase&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=for-the-badge&logo=redis&logoColor=white)

</div>

---

## 🎯 What It Does

A production-grade **AI virtual try-on platform** that lets any e-commerce brand offer:

1. **📸 Photorealistic Try-On** — AI composites a garment onto the user's photo
2. **🧊 3D Mesh Viewer** — Interactive `.glb` model with orbit controls, PBR materials, and contact shadows
3. **🎬 360° Orbital Video** — Auto-generated MP4 showing the garment from every angle

> **Pipeline cost:** ~$0.09/run &nbsp;·&nbsp; **Latency:** ~70 seconds &nbsp;·&nbsp; **3-tier AI failover** for 99.9% uptime

---

## 🛠️ Frameworks & Technologies

### ⚛️ Frontend

```
React 18.3           →  Component architecture + hooks
TypeScript 5.6       →  End-to-end type safety
Vite 6.0             →  Sub-second HMR + optimized builds
Tailwind CSS 3.4     →  Utility-first dark theme with custom tokens
Framer Motion 11.15  →  Spring physics animations + layout transitions
Zustand 5.0          →  Minimal global state (auth, tryon, viewer stores)
React Router 6.28    →  Client-side routing with auth guards
Axios 1.7            →  HTTP client with interceptors
react-dropzone 14.3  →  Drag-and-drop photo uploads
Supabase JS 2.47     →  Auth + Realtime WebSocket subscriptions
ESLint 9.13          →  Code quality enforcement
PostCSS 8.4          →  CSS transforms + Autoprefixer 10.4
```

### 🧊 3D Engine

```
Three.js 0.170             →  WebGL rendering engine
React Three Fiber 8.17     →  Declarative R3F wrapper
React Three Drei 9.120     →  OrbitControls · ContactShadows · Grid · Environment · useGLTF
React Three Postprocessing  →  SMAA anti-aliasing (quality-adaptive)
  2.16
```

### ⚡ Backend

```
Python 3.12          →  Runtime
FastAPI 0.115        →  Async REST framework + auto-generated OpenAPI docs
Uvicorn 0.34         →  High-performance ASGI server
Pydantic 2.10        →  Data validation + settings management
httpx 0.28           →  Async HTTP client for AI provider calls
ARQ 0.26             →  Async Redis job queue (background pipeline)
Redis 7 Alpine       →  Queue broker + result cache (256MB LRU)
tenacity 9.0         →  Retry with exponential backoff
pybreaker 1.2        →  Circuit breaker pattern (7 breakers)
structlog 24.4       →  Structured JSON logging
Pillow 11.1          →  Image processing + resizing
MediaPipe 0.10       →  On-device body landmark estimation
```

### 🤖 AI / ML Providers

```
Fashn.ai tryon-v1.6       →  Primary garment synthesis (VTO)
Fashn.ai image-to-video   →  Primary 360° orbital video
Replicate IDM-VTON        →  1st synthesis fallback
Replicate Flux-VTON       →  2nd synthesis fallback
Replicate TRELLIS         →  3D .glb mesh reconstruction
Replicate Wan 2.2 I2V     →  Fallback 360° video
HuggingFace HMR 2.0       →  Full-body pose estimation
```

### 🏗️ Infrastructure

```
Docker Compose       →  4-service orchestration (redis · backend · worker · frontend)
Nginx                →  Reverse proxy · gzip · static caching · security headers
Supabase             →  Auth · Postgres · Storage (signed URLs) · Realtime (WebSocket)
```

---

## 🏛️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend  (Vite + React)                    │
│                                                                 │
│   HeroLanding → GarmentCatalog → PhotoUpload → Result Viewer   │
│   Three.js 3D  ·  Framer Motion  ·  Zustand  ·  Tailwind CSS  │
└────────────────────────────┬────────────────────────────────────┘
                             │  REST + Supabase Realtime
┌────────────────────────────▼────────────────────────────────────┐
│                   FastAPI Backend  (:8000)                       │
│                                                                 │
│   /auth   /tryon   /garments   /health   /metrics               │
│   CORS  ·  Rate-Limit  ·  Structured Logging  ·  Auth Guard    │
└───────┬──────────┬──────────┬──────────┬───────────────────────┘
        │          │          │          │
   ┌────▼───┐ ┌───▼────┐ ┌──▼──────┐ ┌▼──────────────┐
   │Supabase│ │ Redis  │ │ Fashn   │ │  Replicate    │
   │Auth/DB │ │ Queue  │ │  .ai    │ │  (fallback)   │
   │Storage │ │ (ARQ)  │ │ PRIMARY │ │ IDM/Flux/Wan  │
   └────────┘ └──┬─────┘ └─────────┘ └───────────────┘
                 │
           ┌─────▼──────┐
           │ ARQ Worker  │
           │             │
           │ Body Est  → │
           │ Synthesis → │
           │ 3D Mesh   → │
           │ 360° Video  │
           └─────────────┘
```

### 5-Layer Pipeline

| # | Layer | Service |
|---|-------|---------|
| 1 | 🦴 Body Estimation | MediaPipe (local) → HMR 2.0 (HuggingFace) |
| 2 | 👕 Garment Synthesis | Fashn.ai → IDM-VTON → Flux-VTON |
| 3 | 🎬 360° Rendering | TRELLIS (.glb) + Fashn/Wan 2.2 I2V (.mp4) |
| 4 | ⚡ Async Infra | ARQ + Redis + Supabase Realtime |
| 5 | 🔒 Privacy | GDPR consent flow + Supabase RLS |

### Provider Failover Chain

```
Garment Synthesis:   Fashn.ai tryon-v1.6  →  IDM-VTON  →  Flux-VTON
360° Video:          Fashn.ai I2V         →  Wan 2.2 I2V
3D Mesh:             TRELLIS              →  .glb for Three.js
```

Each provider has its own **circuit breaker** (pybreaker) — 3 failures trips the breaker, auto-recovery after 60–120s.

---

## ✨ Animations & Visual Effects

The UI is built with **60fps choreographed motion** using Framer Motion spring physics, Three.js real-time 3D, and custom CSS.

### 🎭 Framer Motion — Spring Physics

#### Page & Component Entrances

| Animation | Where | Config |
|-----------|-------|--------|
| **Fade-up entrance** | Hero, cards, grids | `opacity: 0→1` · `y: 30→0` · `0.7s easeOut` |
| **Staggered cards** | Garment grid, My Looks | `delay: idx × 0.05` · `opacity + y` slide |
| **Scale-in badge** | Hero status badge | `scale: 0.9→1` · `delay: 0.2s` |
| **Feature pills** | Hero section | `opacity: 0→1` · `delay: 0.5s` |
| **Partial result pop** | Processing step | `scale: 0.95→1` · `opacity: 0→1` |
| **Image/Video reveal** | Photo viewer, 360° player | `opacity: 0→1` · `0.5s` |

#### Interactive Feedback

| Animation | Where | Config |
|-----------|-------|--------|
| **Button press** | CTA buttons | `hover: scale 1.03` · `tap: scale 0.97` |
| **Selection check** | Garment card | `scale: 0→1` spring pop |
| **Dropdown slide** | User menu | `y: -8→0` · `AnimatePresence` exit |
| **Delete overlay** | My Looks hover | `opacity: 0→1` · `300ms` CSS |
| **Error slide-in** | Progress tracker | `opacity + y: -8→0` |

#### 🧲 Shared Layout Animations (`layoutId`)

Three spring-physics pill indicators that **slide smoothly** between active states:

| `layoutId` | Component | Tabs |
|------------|-----------|------|
| `nav-pill` | Header nav | Catalog · Try On · My Looks |
| `auth-tab` | Auth modal | Sign In · Sign Up |
| `viewmode-pill` | Result viewer | Photo · 3D · 360° |

> All use `type: 'spring'` · `bounce: 0.2` · `duration: 0.4s` for a consistent, snappy feel.

#### 🎬 AnimatePresence — Exit Animations

Modals (`AuthModal`, `ConsentModal`) mount/unmount with:
- **Enter:** `scale: 0.9→1` · `opacity: 0→1`
- **Exit:** reverse with automatic cleanup

### 🌊 CSS Animations & Keyframes

| Effect | Details |
|--------|---------|
| **🔄 Progress bar stripes** | `@keyframes stripe-move` — 45° diagonal stripes scrolling infinitely at 0.5s |
| **💜 Pulsing step dot** | `scale: [1 → 1.3 → 1]` at 1s repeat on active pipeline step |
| **✨ Slow pulse glow** | `pulse-slow` — 3s `cubic-bezier(0.4, 0, 0.6, 1)` breathing |
| **🌀 Slow spin** | `spin-slow` — 8s linear infinite rotation |

### 🪟 Glass Morphism & Visual Effects

| Effect | Implementation |
|--------|---------------|
| **Glass cards** | `backdrop-blur-xl` · `bg-white/5` · `border-white/10` · `rounded-2xl` |
| **Purple gradient** | `linear-gradient(→, #c084fc, #9333ea)` |
| **Glow shadows** | `box-shadow: 0 0 40px rgba(168,85,247,0.15), 0 0 80px rgba(168,85,247,0.05)` |
| **Sticky header** | `bg-surface-950/80` · `backdrop-blur-xl` · `border-white/5` |
| **Hero background** | Two blurred circles — 600px `blur-[120px]` + 400px `blur-[100px]` |
| **Custom scrollbar** | 6px · `rgba(255,255,255,0.15)` · 3px radius |
| **Dropzone glow** | Border → `brand-400` + `bg-brand-400/5` on active drag |

---

## 🧊 Three.js 3D Viewer

Interactive `.glb` mesh rendering with physically-based materials inside a React Three Fiber `<Canvas>`.

### Scene Setup

| Config | Value |
|--------|-------|
| Antialiasing | Enabled (MSAA + SMAA post-process) |
| Tone Mapping | ACES Filmic |
| DPR | `[1, 2]` adaptive |
| Shadows | Full cascade |

### Camera & Orbit Controls

| Feature | Value |
|---------|-------|
| Controls | Full pan · zoom · rotate with 0.05 damping |
| Zoom | 1× – 8× |
| Vertical | 18° – 153° (prevents flip) |
| Auto-rotate | Optional continuous spin |

### Lighting

| Light | Intensity | Notes |
|-------|-----------|-------|
| 🌍 Environment (preset) | 1.0 | Global IBL |
| 💡 Ambient | 0.3 | Soft fill |
| ☀️ Key directional | 0.8 | `[5,5,5]` — 1024² shadow map |
| 🌙 Fill directional | 0.3 | `[-3,3,-3]` — no shadows |
| 🟫 Contact shadows | 0.4 opacity | Ground plane, blur: 2 |

### GLB Processing Pipeline

```
Load .glb (useGLTF)
  → Auto-center via bounding box
  → Normalize scale to ~2 units height
  → Upgrade materials: MeshStandard → MeshPhysical
      + clearcoat: 0.05
      + clearcoat roughness: 0.3
      + env map intensity: 1.2
      + double-sided rendering
  → Enable cast + receive shadows
  → Idle Y-axis rotation at 0.02 rad/frame (~5.2s/rev)
```

### Post-Processing

- **SMAA** anti-aliasing (disabled on low quality)
- Optional **infinite grid** (0.5-unit cells, 2-unit sections, 10-unit fade)

---

## 🎨 Design System

### Color Palette

| Token | Scale | Usage |
|-------|-------|-------|
| `brand` | `#faf5ff` → `#a855f7` → `#3b0764` | Purple accent · gradients · interactive |
| `surface` | `#fafafa` → `#171717` → `#0a0a0a` | Dark backgrounds · cards · borders |

### Typography

| Role | Font | Weight |
|------|------|--------|
| Body (`sans`) | **Inter** | 400 · 500 · 600 |
| Display (`display`) | **Space Grotesk** | 600 · 700 |

---

## 🔌 API Reference

### Auth

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/v1/auth/signup` | — | Create account |
| `POST` | `/api/v1/auth/login` | — | Sign in |
| `POST` | `/api/v1/auth/logout` | 🔒 | Sign out |
| `POST` | `/api/v1/auth/consent` | 🔒 | GDPR consent (`consent_given` + `privacy_acknowledged`) |

### Garments

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/api/v1/garments` | — | List garments (filter by `category`) |
| `GET` | `/api/v1/garments/{id}` | — | Single garment |
| `POST` | `/api/v1/garments` | 🔒 | Upload new garment (admin) |

### Try-On

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/v1/tryon` | 🔒 | Start pipeline (multipart: `selfie` + `fullbody` + `garment_id`) |
| `GET` | `/api/v1/tryon/{job_id}` | 🔒 | Poll job status |
| `GET` | `/api/v1/tryon/history` | 🔒 | User's looks (returns `looks[]`) |
| `DELETE` | `/api/v1/tryon/{job_id}` | 🔒 | Delete a look |

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/health` | Service health + circuit breaker states |
| `GET` | `/api/v1/metrics` | Prometheus-format metrics |

---

## 🗄️ Database Schema

```sql
-- Auth: Supabase Auth (auth.users)

-- Privacy consent
consent_records (user_id, consent_type, ip_address, user_agent, granted_at)

-- Garment catalog
garments (id, slug, name, brand, category, color, price, image_url, ...)

-- Try-on jobs
tryon_jobs (
  id, user_id, garment_id,
  status  [pending | processing | completed | failed],
  result_photo_url, result_video_url, result_mesh_url,
  model_used, processing_time_ms, ...
)
```

---

## 🐳 Docker

4 services orchestrated with Docker Compose:

| Service | Port | Stack |
|---------|------|-------|
| **redis** | 6379 | Redis 7 Alpine · 256MB LRU · AOF persistence |
| **backend** | 8000 | FastAPI · Uvicorn |
| **worker** | — | ARQ async pipeline worker |
| **frontend** | 80 | Nginx · Gzip · Static caching |

### Nginx Highlights

- **Gzip** — JS, JSON, WASM, glTF, SVG (min 1KB)
- **Caching** — `/assets/` 1yr immutable · `.glb/.gltf/.hdr` 7 days
- **Proxy** — `/api/` → backend:8000 (120s timeout, 15MB uploads)
- **SPA** — `try_files $uri $uri/ /index.html`
- **Security** — X-Frame-Options, X-Content-Type-Options, Referrer-Policy

---

## ⚙️ Environment Variables

Copy `.env.example` → `.env`:

| Variable | Required | Description |
|----------|:--------:|-------------|
| `SUPABASE_URL` | ✅ | Supabase project URL |
| `SUPABASE_ANON_KEY` | ✅ | Supabase anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ | Supabase service role key |
| `FASHN_API_KEY` | ✅ | Fashn.ai API key |
| `REPLICATE_API_TOKEN` | — | Replicate token (fallback providers) |
| `REDIS_URL` | — | Default: `redis://localhost:6379/0` |
| `ENVIRONMENT` | — | `development` / `staging` / `production` |
| `USE_STUBS` | — | `true` = mock all AI APIs |
| `LOG_LEVEL` | — | `DEBUG` / `INFO` / `WARNING` |
| `CORS_ORIGINS` | — | Comma-separated allowed origins |

---

## 📁 Project Structure

```
├── backend/
│   ├── app/
│   │   ├── config.py                 # Pydantic settings
│   │   ├── main.py                   # FastAPI app factory + lifespan
│   │   ├── middleware/
│   │   │   ├── auth_middleware.py     # Bearer token → user
│   │   │   ├── logging_middleware.py  # Structured request logging
│   │   │   └── rate_limit.py         # Token bucket limiter
│   │   ├── models/                   # Pydantic schemas
│   │   ├── routers/                  # /auth /garments /tryon /health
│   │   ├── services/
│   │   │   ├── fashn_service.py      # Fashn.ai VTO + video (PRIMARY)
│   │   │   ├── synthesis_service.py  # 3-provider failover chain
│   │   │   ├── video_service.py      # 360° video + 3D mesh
│   │   │   ├── body_estimation_service.py
│   │   │   ├── auth_service.py
│   │   │   └── storage_service.py
│   │   ├── utils/                    # Circuit breakers + Prometheus
│   │   └── workers/                  # ARQ job handler + config
│   ├── Dockerfile
│   ├── requirements.txt
│   └── supabase_schema.sql
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/                   # 10 UI components (Hero, Catalog, Flow, etc.)
│   │   │   └── viewer/               # 4 viewer components (Scene, Model, Photo, Video)
│   │   ├── hooks/                    # useGarments · useConsent · useTryOnRealtime
│   │   ├── stores/                   # Zustand: auth · tryon · viewer
│   │   ├── lib/                      # API client · Supabase init
│   │   ├── types/                    # Shared TypeScript interfaces
│   │   └── index.css                 # Tailwind + glass effects + custom tokens
│   ├── tailwind.config.js
│   ├── vite.config.ts
│   ├── nginx.conf
│   └── Dockerfile
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

- **Node.js 20+** · **Python 3.12+** · **Redis** (or use Docker)

### Local Development

```bash
# Clone & configure
cp .env.example .env
# Fill in SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY, FASHN_API_KEY

# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Worker (new terminal)
cd backend
arq app.workers.worker_config.WorkerSettings

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### Docker

```bash
docker compose up --build
# Frontend → http://localhost
# Backend  → http://localhost:8000
# API Docs → http://localhost:8000/api/docs
```

---

## 🧠 Design Decisions

| Decision | Why |
|----------|-----|
| **Snapshot-first storage** | All AI outputs are immediately persisted to Supabase Storage with signed URLs — no ephemeral external links |
| **Zero-polling realtime** | Job updates via Supabase Realtime (Postgres → WebSocket). Polling is only a fallback |
| **Graceful degradation** | Each pipeline layer fails independently. No video? Photo still works. No mesh? Photo view available |
| **Circuit breakers** | 7 independent pybreaker circuits. Failures trip fast, auto-recover after 60–120s |
| **PBR material upgrade** | Raw `.glb` meshes auto-upgrade from `MeshStandard` → `MeshPhysical` with clearcoat + env mapping |
| **Adaptive quality** | SMAA post-processing disabled on low-quality, DPR scales `[1, 2]` based on device |

---

## 📄 License

MIT — Use it for any brand, any store, any project.
