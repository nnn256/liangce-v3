FROM node:24-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONUTF8=1 HOST=0.0.0.0 PORT=8810 LIANGCE_PUBLIC_MODE=1
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
COPY --from=frontend /build/web/dist ./web/dist
RUN useradd --create-home --uid 10001 liangce && mkdir -p /app/.runtime && chown -R liangce:liangce /app
USER liangce
EXPOSE 8810
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD python -c "from urllib.request import urlopen;urlopen('http://127.0.0.1:8810/api/research/health',timeout=4)" || exit 1
CMD ["python","-m","uvicorn","web.research_server:app","--host","0.0.0.0","--port","8810"]
