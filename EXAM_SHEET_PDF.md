# Exam Sheet PDF Pipeline

The exam-sheet PDF is generated server-side with Playwright (headless Chromium).

## Local

1. Install Python deps: `pip install -r requirements.txt`
2. Install Chromium for Playwright: `playwright install chromium`

## Heroku

The app uses `CHROMIUM_EXECUTABLE_PATH` when set (by the buildpack) and launches with `--no-sandbox` on Heroku.

### 1. Add buildpacks (order matters)

On **Heroku-24** use three buildpacks: Python, Apt (Chromium system libs), then Playwright Python browsers. Chromium needs system libraries (e.g. `libatk-1.0.so.0`); the Aptfile lists them so the apt buildpack installs them.

```bash
# 1) Python (should already be set)
heroku buildpacks:add -i 1 heroku/python -a linguaformula-backend

# 2) Apt – install Chromium shared library deps (see Aptfile)
heroku buildpacks:add -i 2 https://github.com/heroku/heroku-buildpack-apt -a linguaformula-backend

# 3) Playwright Python – installs Chromium and sets CHROMIUM_EXECUTABLE_PATH
heroku buildpacks:add -i 3 https://github.com/Thomas-Boi/heroku-playwright-python-browsers -a linguaformula-backend
```

If buildpacks already exist, use `heroku buildpacks` to list and add/remove to get this order. The repo includes an `Aptfile` in `backend/linguaformula/` with the required packages for Ubuntu 24.04. Slug size will be ~350 MB (Chromium + headless shell).

### 2. Config (optional, reduces slug size)

```bash
heroku config:set PLAYWRIGHT_BUILDPACK_BROWSERS=chromium -a linguaformula-backend
```

### 3. Redeploy

After adding buildpacks and config, redeploy so the build runs with the new buildpacks:

```bash
cd backend/linguaformula
git commit --allow-empty -m "Trigger rebuild for Playwright buildpacks"
git push heroku main
```

Without Chromium on the server, `GET /api/exam_sheet/pdf` will fail at runtime when `html_to_pdf()` runs.
