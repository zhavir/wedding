FROM node:26.12.0-bookworm-slim
WORKDIR /app
COPY package*.json ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi \
    && npx playwright install --with-deps chromium
COPY playwright.config.ts ./
COPY tests/browser tests/browser
CMD ["npx", "playwright", "test"]
