FROM node:20-alpine

WORKDIR /app

# Copy from the frontend directory relative to the build context
COPY app/frontend/package.json app/frontend/package-lock.json ./
RUN npm install

# Copy source after dependencies
COPY app/frontend/ .

# Run the development server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]