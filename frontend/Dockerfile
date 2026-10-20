FROM node:26.12.0-alpine
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi
COPY frontend .
COPY content /app/content
ARG PUBLIC_API_URL=/api
ENV PUBLIC_API_URL=$PUBLIC_API_URL
RUN npm run check && npm run build
EXPOSE 5173
CMD ["npm", "run", "preview", "--", "--port", "5173"]
