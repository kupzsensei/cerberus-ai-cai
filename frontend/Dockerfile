# --- Stage 1: Build the React Application ---
FROM node:20-alpine AS builder

# Set the working directory
WORKDIR /app

# ---- This is the new part ----
# Declare the build argument that we expect from docker-compose.yml
ARG VITE_API_URL

# Set it as an environment variable for the rest of the build stage
ENV VITE_API_URL=$VITE_API_URL
# ---- End of new part ----

# Copy package.json and package-lock.json
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the frontend source code
COPY . .

# Build the application for production.
# The 'npm run build' script will now have access to VITE_API_URL.
RUN npm run build


# --- Stage 2: Serve the Application with Nginx ---
FROM nginx:stable-alpine

# Copy the build output from the 'builder' stage to the nginx html directory
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy the custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80
