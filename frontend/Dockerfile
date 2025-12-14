FROM node:20-slim AS base
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
ENV CI=true
# enable corepacks for automatic package manager installation. Keeps things simple
RUN corepack enable
COPY . /app
WORKDIR /app

FROM base AS prod
# copy pnpm lock files and source
COPY pnpm-lock.yaml /app
WORKDIR /app
RUN pnpm install --frozen-lockfile

# build application
COPY . /app
RUN pnpm run build

# We don't want to include artifacts etc. so include only build output
FROM base
COPY --from=prod /app/dist /app/dist
EXPOSE 3000
CMD [ "pnpm", "start" ]
