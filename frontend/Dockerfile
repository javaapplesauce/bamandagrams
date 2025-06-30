# frontend/Dockerfile
FROM node:18-alpine

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
# expose Vite’s dev server
EXPOSE 3000

# run Vite in host‐bind mode
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
