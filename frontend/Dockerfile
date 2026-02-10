# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Set build-time environment variables for Next.js
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_AWS_REGION
ARG NEXT_PUBLIC_USE_MOCK_AUTH
ARG NEXT_PUBLIC_MOCK_TENANT_ID
ARG NEXT_PUBLIC_MOCK_USER_ID

ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_AWS_REGION=$NEXT_PUBLIC_AWS_REGION
ENV NEXT_PUBLIC_USE_MOCK_AUTH=$NEXT_PUBLIC_USE_MOCK_AUTH
ENV NEXT_PUBLIC_MOCK_TENANT_ID=$NEXT_PUBLIC_MOCK_TENANT_ID
ENV NEXT_PUBLIC_MOCK_USER_ID=$NEXT_PUBLIC_MOCK_USER_ID

# Build the application
RUN npm run build

# Stage 2: Production
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

# Copy necessary files from builder
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules

EXPOSE 3000

CMD ["npm", "start"]
