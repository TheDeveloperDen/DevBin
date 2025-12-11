# DevBin Frontend - Bin for All Your Pasting Needs

Simple straight forward UI for the DevBin pastes service programmed in Svelte

## 1 Prerequisites

You may require the backend running before you can create and view pastes instructions for settings this up at [DevBinBackendSetup](https://github.com/TheDeveloperDen/DevBin/blob/master/README.md)

> This may be simplified in the future to start off of a single command

then install node modules via:

```sh
pnpm i
```

## 2 Developing

```sh
pnpm dev
```

or, to start the server and open a browser:

```sh
pnpm dev -- --open
```

Always a good idea to setup make sure your api client is up to date:

```sh
pnpm update:api-client
```

## 3 Building

To build the application just run:

```sh
npm run build
```

> Depending on your environment, you may need an environment specific adapter [adapter](https://svelte.dev/docs/kit/adapters)
