FROM node:18-alpine
WORKDIR /app

COPY package.json package-lock.json ./

RUN npm ci

COPY . .
RUN npm install -g vite && \
    chmod +x node_modules/.bin/vite && \
    npm run build

EXPOSE 4173

CMD ["npm", "run", "preview"]
