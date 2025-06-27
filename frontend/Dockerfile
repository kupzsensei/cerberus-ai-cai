# --- Stage 1: Build the React Application ---
    FROM node:20-alpine AS builder

    # Set the working directory
    WORKDIR /app
    
    # Copy package.json and package-lock.json
    COPY package*.json ./
    
    # Install dependencies
    RUN npm install
    
    # Copy the rest of the frontend source code
    COPY . .
    
    # Build the application for production
    # This creates a 'dist' folder with static files
    RUN npm run build
    
    # --- Stage 2: Serve the Application with Nginx ---
    FROM nginx:stable-alpine
    
    # Copy the build output from the 'builder' stage to the nginx html directory
    COPY --from=builder /app/dist /usr/share/nginx/html
    
    # Copy the custom Nginx configuration
    COPY nginx.conf /etc/nginx/conf.d/default.conf
    
    # Expose port 80
    EXPOSE 80
    
    # The default Nginx command will start the server