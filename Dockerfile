# syntax=docker/dockerfile:1

# --------------------------------------------------------------------------
# 1단계: React(Vite) 프론트엔드 빌드 → web/dist
# --------------------------------------------------------------------------
FROM node:20-slim AS web-build

WORKDIR /web

# 의존성 먼저 설치해서 소스만 바뀐 커밋에서는 이 레이어를 재사용합니다.
COPY web/package.json web/package-lock.json ./
RUN npm ci

COPY web/index.html web/vite.config.js ./
COPY web/src ./src
RUN npm run build

# --------------------------------------------------------------------------
# 2단계: FastAPI 런타임 (빌드된 SPA를 같이 서빙)
# --------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /usr/local/bin/uv

ENV PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# 의존성 레이어 (pyproject.toml / uv.lock이 바뀔 때만 다시 설치)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 애플리케이션 소스 + 답변 근거로 제공하는 공고문 PDF
COPY src ./src
COPY examples ./examples
RUN uv sync --frozen --no-dev

COPY --from=web-build /web/dist ./web/dist

# Render는 $PORT를 주입합니다. 로컬 docker run 시에는 8000으로 뜹니다.
EXPOSE 8000
CMD ["sh", "-c", "uvicorn api.main:app --app-dir src --host 0.0.0.0 --port ${PORT:-8000}"]
