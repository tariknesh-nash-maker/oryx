# Pharmacy 300m Visualizer

An interactive map to visualize exclusion buffers (e.g., 300 meters) around existing pharmacies and suggest candidate areas that comply with spacing rules.

## Quick start
```bash
npm install
npm run dev
```

## Build
```bash
npm run build
```

## Deploy options
- **Vercel / Netlify:** framework = Vite, build = `npm run build`, output dir = `dist`.
- **GitHub Pages:** `npm run build && npm run deploy` (uses `gh-pages` to publish `dist/`).

## Data
Upload a CSV (headers: `name,lat,lon`) or a GeoJSON FeatureCollection of Point features.
