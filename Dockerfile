FROM python:3.10-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

COPY hardhat_env/package.json hardhat_env/package-lock.json ./hardhat_env/
RUN cd hardhat_env && npm ci

FROM python:3.10-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    git \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*


COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

COPY --from=builder /app/hardhat_env/node_modules ./hardhat_env/node_modules

RUN pip install solc-select \
    && solc-select install 0.8.20 \
    && solc-select use 0.8.20
COPY . .

RUN chmod +x run_pipeline.sh

ENTRYPOINT ["./run_pipeline.sh"]