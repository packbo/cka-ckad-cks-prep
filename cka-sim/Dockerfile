FROM python:3.11-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl jq ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && curl -fsSL https://dl.k8s.io/release/v1.27.3/bin/linux/amd64/kubectl \
      -o /usr/local/bin/kubectl \
 && chmod +x /usr/local/bin/kubectl

WORKDIR /app
COPY cka_sim /app/cka_sim
COPY cka_sim/static /app/cka_sim/static
COPY scenarios /app/scenarios
COPY exams /app/exams
COPY data /app/data
RUN pip install --no-cache-dir pyyaml

ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python3", "-m", "cka_sim.web"]
