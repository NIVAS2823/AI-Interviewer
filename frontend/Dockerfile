FROM node:20

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Fix npm registry connection + install modules
RUN npm config set registry https://registry.npmjs.org/ \
    && npm config set strict-ssl false \
    && npm install --no-progress

# Copy application files
COPY . .

# Expose port
EXPOSE 5173

# Start Vite dev server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
