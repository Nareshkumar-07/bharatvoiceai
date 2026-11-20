# Desktop app (Tauri)

`tauri/` contains the shell for a desktop build. It is **optional**: the web app
is fully functional on its own.

## What it adds

- a real global shortcut (works while another application is focused), which a
  browser tab cannot do;
- a floating always-on-top microphone window;
- paste-into-active-app via clipboard + synthetic keystroke.

## What it still cannot do

- A browser-only deployment can never inject text into other applications. In the
  web app, "copy" is the honest boundary, and the UI says so.
- On macOS the synthetic paste needs Accessibility permission; on Windows it
  works from a normal user session; on Linux it depends on X11/Wayland (Wayland
  generally blocks synthetic input).

## Build

```bash
cd frontend && npm run build          # produces frontend/dist
cd ../tauri && cargo tauri build      # requires Rust + the Tauri CLI
```

Set the API origin before building the frontend:

```bash
VITE_API_BASE_URL=http://localhost:8000 npm run build
```

`src-tauri/tauri.conf.json` points `frontendDist` at `../../frontend/dist`.

## Files

| File | Purpose |
|---|---|
| `src-tauri/Cargo.toml` | dependencies (`tauri`, `tauri-plugin-global-shortcut`, `tauri-plugin-clipboard-manager`) |
| `src-tauri/src/main.rs` | shortcut registration, window management, clipboard bridge |
| `src-tauri/tauri.conf.json` | window config, permissions, bundle metadata |

## Shortcut configuration

Default: `Ctrl+Shift+Space` toggles recording, `Ctrl+Shift+C` copies the last
transcript. Change them in `main.rs` (`ACCELERATORS`) or make them configurable
through the settings table (`user_preferences.keyboard_shortcuts` already stores
the values the web UI shows).
