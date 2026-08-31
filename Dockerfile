# syntax=docker/dockerfile:1
# CodeGuard -- multi-stage build to a small, non-root image.

FROM python:3.12-slim AS build
WORKDIR /src
COPY . .
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
 && /opt/venv/bin/pip install --no-cache-dir .

FROM python:3.12-slim AS runtime
LABEL org.opencontainers.image.source="https://github.com/mevichitra/codeguard" \
      org.opencontainers.image.description="Fast, offline multi-language SAST CLI" \
      org.opencontainers.image.licenses="Apache-2.0"
COPY --from=build /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN useradd --uid 1000 --create-home codeguard
USER codeguard
WORKDIR /src
ENTRYPOINT ["codeguard"]
CMD ["--help"]
