FROM node:20-slim AS base
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
ENV CI=true
RUN apt-get update && apt-get install -y \
    fontconfig \
    fonts-dejavu-core \
    --no-install-recommends \
    && fc-cache -f \
    && rm -rf /var/lib/apt/lists/*

# enable corepacks for automatic package manager installation. Keeps things simple
RUN corepack enable
COPY . /app
WORKDIR /app

FROM base AS build
# copy pnpm lock files and source
COPY pnpm-lock.yaml /app
WORKDIR /app
RUN pnpm install --frozen-lockfile

# build application
COPY . /app
RUN pnpm build

RUN pnpm prune --prod

# We don't want to include artifacts etc. so include only build output
FROM node:20-slim AS prod

# add fontconfig and base fonts for sharp SVG rendering - this is for code preview gen
RUN apt-get update && apt-get install -y \
    fontconfig \
    fonts-dejavu-core \
    --no-install-recommends \
    && fc-cache -f \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=build /app/node_modules node_modules
COPY --from=build /app/dist dist
EXPOSE 3000
CMD [ "node", "dist/index.js" ]
