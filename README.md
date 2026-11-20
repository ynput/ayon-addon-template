# AYON addon template

Start a new AYON addon from here. It works as soon as it is installed: a server part with one
endpoint and one setting, and a web UI part that adds a **My Addon** tab to the dashboard. The tab
shows AYON's project list and a greeting from the addon's endpoint.

The web UI part is built on the addon SDK, `@ynput/ayon-addon` and `@ynput/ayon-addon-dev`. It
declares what it adds to AYON's UI (its **slots**: pages, details panel tabs, header buttons, menu
items, table columns) in `frontend/src/manifest.ts`.

## Quick start

You need Python 3.9+, Node.js 20.19+ or 22.12+, and Yarn 1 (Classic).

1. Click **Use this template** on GitHub, or clone this repository.
2. Rename the addon: search and replace across the repository, matching case:
   `my_addon` → your addon's name (a lower case letter, then lower case letters, digits and `_`,
   e.g. `budget_tools`; no `-`), `myAddon` and `MyAddon` → the same
   name in camelCase and PascalCase, `My Addon` → its title. Then rename the two `my_addon.ts`
   files in `frontend/src/api/`. The name must be the same in `package.py` (`name`),
   `server/__init__.py` (the `frontend_modules` key) and `frontend/vite.config.ts`
   (`ayonAddon({ name })`).
3. Install the frontend's packages: `cd frontend && yarn install`.
4. Build the package: `python create_package.py` (from the repository root). It writes the
   version into the frontend, builds it, and creates `package/my_addon-<version>.zip`.
5. In AYON, go to **Studio settings > Bundles**, click **Install addons** and upload the zip.
   When the installation is done, restart the server. Then choose **Duplicate and Edit** on the
   production bundle, select the uploaded `my_addon` version, save the new bundle, choose
   **Set Production** and reload the page. The **My Addon** tab is on the dashboard.
6. After you change the server's endpoints, install that version and run `yarn generate-rest` in
   `frontend/`. It regenerates `src/api/generated/` from the server's OpenAPI schema.

## Develop the web UI

Run these in `frontend/`. The CLI signs in with `AYON_SERVER_URL` and `AYON_API_KEY` (shell,
`.env.local` or `.env`; the first run asks for them and writes `.env`).

| Command | What it does |
|---|---|
| `yarn dev` | The dev shell: your contributions in AYON's real components (project list, details panel, tables), with hot reload, without the AYON app |
| `yarn dev:ayon` | Builds on every change and prints a URL that loads your local build inside your AYON server (your user needs developer mode) |
| `yarn ayon-addon check` | Checks the manifest as AYON reads it, the piece files and the types |
| `yarn ayon-addon slots` | Lists every slot you can contribute to, with an example |
| `yarn generate-rest` | Generates RTK Query endpoints from the addon's server endpoints |
| `yarn lint`, `yarn build` | Before a commit |

The SDK's own docs are in `frontend/node_modules/@ynput/ayon-addon/AGENTS.md` (the slots and
their rules) and `frontend/node_modules/@ynput/ayon-addon-dev/AGENTS.md` (the CLI and dev shell).
For an addon that uses many slots, see
[ayon-addon-full-template](https://github.com/ynput/ayon-addon-full-template).

No web UI? Delete `frontend/` and the `frontend_modules` line in `server/__init__.py`.
`create_package.py` builds the frontend only when the folder exists.

## Folder structure

```
├─ server/              the server part (required): the addon class, settings, endpoints
│  ├─ __init__.py
│  └─ settings.py
├─ frontend/            the web UI part (optional), built into frontend/dist
│  ├─ src/manifest.ts   what the addon adds to AYON's UI
│  ├─ src/pages/        the studio page
│  └─ src/api/          the addon's endpoints in AYON's API client
├─ client/              desktop (launcher) code (optional), see below
├─ public/              files served without sign-in (optional)
├─ private/             files served to signed-in users (optional)
├─ create_package.py
├─ package.py           name, title, version
└─ LICENSE
```

### Server

`server/__init__.py` defines the addon on the server: its settings, endpoints and frontend
modules. Settings are in `server/settings.py`; use a folder when one file isn't enough.

### Public and private files

`public/` is served at `{server url}/addons/{addon name}/{addon version}/public/*` without
sign-in, for images, icons and other static content. `private/` is served at `.../private/*` to
signed-in users. The client zip goes into `private/` when the package is created.

### Client

Addons with code for the desktop launcher put it in `client/`, in one folder named the way it is
imported (e.g. `client/my_addon/`), and set `client_dir` in `package.py`. Client dependencies go in
`client/pyproject.toml`.
