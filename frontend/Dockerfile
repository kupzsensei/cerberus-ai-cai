# --- Stage 1: Build the React Application ---
FROM node:20-alpine AS builder

WORKDIR /app

# The ARG and ENV lines are no longer needed, so they have been removed.

COPY package*.json ./
RUN npm install --force
COPY . .
RUN npm run build

# --- Stage 2: Serve the Application with Nginx ---
FROM nginx:stable-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
