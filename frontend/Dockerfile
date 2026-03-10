# ───────────────────────────────────────────────────
# The Dirty Laundry V2 — Multi-stage frontend build
# ───────────────────────────────────────────────────

# ─── Build stage ───
FROM node:20-alpine AS build

WORKDIR /app

# Install deps (cached layer)
COPY package.json package-lock.json* ./
RUN npm ci

# Copy source & build
COPY . .

ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY
ARG VITE_API_BASE_URL=/api/v1

ENV VITE_SUPABASE_URL=$VITE_SUPABASE_URL
ENV VITE_SUPABASE_ANON_KEY=$VITE_SUPABASE_ANON_KEY
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# ─── Production stage (nginx) ───
FROM nginx:alpine AS production

# Remove default config
RUN rm /etc/nginx/conf.d/default.conf

# Copy our config
COPY nginx.conf /etc/nginx/conf.d/app.conf

# Copy built assets
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
