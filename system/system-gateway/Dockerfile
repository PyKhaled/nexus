FROM nginx:1.29-alpine

LABEL org.opencontainers.image.title="Nexus System Gateway"
LABEL org.opencontainers.image.description="NGINX edge gateway for Nexus services"

RUN rm /etc/nginx/conf.d/default.conf

COPY --chown=101:101 nginx.conf /etc/nginx/nginx.conf
COPY --chown=101:101 conf.d/ /etc/nginx/conf.d/
COPY --chown=101:101 snippets/ /etc/nginx/snippets/
COPY --chown=101:101 templates/ /etc/nginx/templates/

EXPOSE 80 443

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:80/healthz || exit 1

STOPSIGNAL SIGQUIT
