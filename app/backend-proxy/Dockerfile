FROM node:20-alpine

# Set working directory
WORKDIR /app

# Copy package.json and package-lock.json (if exists)
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application
COPY . .

# Expose HTTP and HTTPS ports
EXPOSE 80 443

# Start the server
CMD ["node", "redirect-server.js"]
