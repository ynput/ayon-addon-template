# Agent instructions

This is an AYON addon: a server part in `server/` and a web UI part in `frontend/`. Start with
`README.md`.

## Web UI: the addon SDK

The frontend adds UI to AYON through **slots** (`studio.page`, `project.page`,
`detailsPanel.tab`, `header.item`, `entityMenuItem`, `tableColumn`, ...), declared in
`frontend/src/manifest.ts`. Before writing frontend code, read the SDK's docs in the installed
packages (run `yarn install` in `frontend/` first). They match the installed version:

- `frontend/node_modules/@ynput/ayon-addon/AGENTS.md`: the slots, what each one's code gets, and
  the rules (pieces are dynamic imports, ids, `useSlot`, data and globals).
- `frontend/node_modules/@ynput/ayon-addon-dev/AGENTS.md`: `ayonAddon()` for Vite, the
  `ayon-addon` CLI and the dev shell.

In `frontend/`:

- `yarn ayon-addon slots` lists every slot with an example manifest entry.
- `yarn ayon-addon check` checks the manifest, the piece files and the types. Run it after each change to
  the manifest.
- `yarn ayon-addon open <slot> <id> --screenshot shot.png` renders one contribution in a headless
  browser against the server and reports errors.
- `yarn lint` and `yarn build` before a commit.

## Names that must match

The addon name (`my_addon` in the template) is in `package.py` (`name`), `server/__init__.py`
(the `frontend_modules` key) and `frontend/vite.config.ts` (`ayonAddon({ name })`). Nothing
checks that they match: compare the three yourself after a rename. The name is a lower case
letter, then lower case letters, digits and `_`.

## Server endpoints

Endpoints are added in `server/__init__.py` (`self.add_endpoint`). The frontend calls them through
`frontend/src/api/`: `yarn generate-rest` writes `src/api/generated/` from the OpenAPI schema of a
server that has this version installed. Never edit the generated file: add cache tags and export
hooks in the enhancing file next to it (`src/api/my_addon.ts`).

`create_package.py` writes the `package.py` version into `frontend/src/addonVersion.ts` and
`frontend/package.json`; the endpoints' URLs use it.
