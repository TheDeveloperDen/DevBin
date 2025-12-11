# DevBin Frontend - Bin for All Your Pasting Needs

Simple straight forward UI for the DevBin pastes service programmed in Svelte

## Prerequisites

You may require the backend running before you can create and view pastes instructions for settings this up at [DevBinBackendSetup](https://github.com/TheDeveloperDen/DevBin/blob/master/README.md)

> This may be simplified in the future to start off of a single command

then install node modules via:

```sh
pnpm i
```

## Developing

```sh
pnpm dev
```

or

```sh
# or start the server and open the app in a new browser tab
pnpm dev -- --open
```

Backend api endpoint/structure may change in the future you can simply update your client to match the backend openapi spec with:

```sh
pnpm update:api-client
```

## Building

To build the application just run:

```sh
npm run build
```

> Depending on your environment, you may need an environment specific adapter [adapter](https://svelte.dev/docs/kit/adapters)
