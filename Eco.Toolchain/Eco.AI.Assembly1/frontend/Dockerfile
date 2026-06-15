FROM node:22-alpine

WORKDIR /app

COPY package*.json ./
# RUN npm install

# Используем официальный реестр npm с HTTPS
RUN npm config set registry https://registry.npmjs.org && \
    npm install

COPY . .

# Next.js telemetry disable
ENV NEXT_TELEMETRY_DISABLED 1

# Build for production
RUN npm run build

# Start
CMD ["npm", "start"]

