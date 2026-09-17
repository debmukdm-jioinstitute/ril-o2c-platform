# Free Deployment (Render + Vercel)

GitHub itself only serves static files (Pages) — it can't run the FastAPI backend or Postgres.
This repo deploys as two free services that both connect to this GitHub repo directly, so
pushes to `main` auto-redeploy:

- **Backend + Postgres → [Render](https://render.com)** (free web service + free Postgres)
- **Frontend → [Vercel](https://vercel.com)** (free hobby tier, built by the Next.js team)

Both require you to sign in with your own GitHub account and authorize the connection — that
step can't be done on your behalf, but everything else is pre-configured in this repo.

## 1. Backend + database (Render)

1. Go to [dashboard.render.com](https://dashboard.render.com) → **New** → **Blueprint**.
2. Connect your GitHub account if prompted, then pick this repo
   (`debmukdm-jioinstitute/ril-o2c-platform`).
3. Render reads [`render.yaml`](render.yaml) automatically — it defines one free web service
   (`ril-o2c-backend`) and one free Postgres database (`ril-o2c-db`), already wired together via
   `RIL_DATABASE_URL`. Click **Apply**.
4. Wait for both to deploy (first build takes a few minutes — installs `backend/requirements.txt`,
   including XGBoost/LightGBM; Render's Linux build environment doesn't need the macOS OpenMP
   workaround `scripts/fix_macos_openmp.sh` handles locally).
5. Copy the backend's public URL (something like `https://ril-o2c-backend.onrender.com`) — you'll
   need it for step 2.

**Free-tier limits to know:** the web service spins down after 15 minutes idle (first request
after that takes ~30-60s to wake up); the free Postgres database expires after 90 days and would
need recreating (fine for a demo, not for anything long-lived).

## 2. Frontend (Vercel)

1. Go to [vercel.com/new](https://vercel.com/new), connect GitHub, import this repo.
2. Set **Root Directory** to `frontend` (Vercel auto-detects Next.js once you do).
3. Add one environment variable: `NEXT_PUBLIC_API_BASE_URL` = the Render backend URL from step 1
   (no trailing slash).
4. Click **Deploy**. You'll get a URL like `https://ril-o2c-platform.vercel.app`.

## 3. Verify

Open the Vercel URL. The header should show `OK` / `Demo/Synthetic Data`, and the forecast chart
should populate. If it doesn't:
- Check the Vercel deployment's browser console for CORS errors — the backend's
  `RIL_CORS_ALLOW_ORIGIN_REGEX` (see `app/core/config.py`) already allows `*.vercel.app` by
  default, so this should work out of the box; a custom domain would need that regex updated.
- The first request after backend idle can take up to a minute (free-tier cold start) — a
  loading state, not a failure.

## Updating the deployment

Both Render and Vercel auto-redeploy on every push to `main` once connected — no further action
needed after the first setup.

## Local development

None of the above is required for local development — see the Quickstart in
[README.md](README.md) to run both services on your own machine.
