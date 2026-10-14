FROM nginx:1.25.5-alpine

COPY nginx.conf /etc/nginx/nginx.conf

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=12 \
    CMD wget -qO- http://127.0.0.1/health || exit 1
