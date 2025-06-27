# frontend/Dockerfile

# --- Stage 1: Build the React Application ---
FROM node:20-alpine AS builder
WORKDIR /app

COPY package*.json ./
RUN npm install
COPY . .
# This build now correctly uses the relative paths from apiService.js
RUN npm run build

# --- Stage 2: Serve the Application with Nginx ---
FROM nginx:stable-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
# Copy our new proxy configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
