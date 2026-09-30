# Frontend V2 Architecture

`src/` is the editable source. `dist/` is generated output.

- `src/pages/` — page HTML. Existing filenames/routes are preserved.
- `src/components/` — shared HTML fragments. `nav.html` remains the runtime navigation component.
- `src/assets/` — CSS, JavaScript, images, and extracted page assets.
- `src/data/` — published structured data.
- `src/public/` — files copied unchanged to the site root, such as `.nojekyll` and root JSON.
- `build/build.ps1` — rebuilds and validates `dist/`.
- `build/serve.ps1` — serves `dist/` locally with Python for browser testing.
- `dist/` — deployable static website. Do not edit this directory directly.

## Working rule

Edit `src/`, then run:

```powershell
& .\build\build.ps1
```

Test locally with:

```powershell
& .\build\serve.ps1
```

## What changed in this migration

All inline `<style>` blocks and inline executable JavaScript from the snapshot were externalized into `src/assets/css/` and `src/assets/js/`. Exact duplicate blocks are shared rather than copied repeatedly.

The rendered URL structure is unchanged: pages still publish at the root of `dist/` using their existing filenames.

## Generator boundary

This archive contains only the frontend snapshot, not the Python scripts that originally generate some dashboard pages. The generated dashboard HTML has been normalized here, but the upstream Python generators must eventually be updated separately if this architecture is reconnected to the production pipeline. Until then, rerunning an old generator could recreate inline CSS/JavaScript in its output.
