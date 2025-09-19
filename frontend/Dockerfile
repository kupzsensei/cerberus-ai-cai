

# --- Stage 1: Build the React Application ---
FROM node:20-alpine AS builder
WORKDIR /app

# Copy package files
COPY package*.json ./

# Remove package-lock.json and node_modules if they exist, then install dependencies
RUN rm -f package-lock.json && \
    npm install --legacy-peer-deps && \
    npm install esbuild@0.25.10 vite@5.4.10

# Copy application code
COPY . .

# Build the application
RUN npm run build

# --- Stage 2: Serve the Application with Nginx ---
FROM nginx:stable-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
