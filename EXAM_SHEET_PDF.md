# Exam Sheet PDF Pipeline

The exam-sheet PDF is generated server-side with Playwright (headless Chromium).

## Local

1. Install Python deps: `pip install -r requirements.txt`
2. Install Chromium for Playwright: `playwright install chromium`

## Heroku

The app uses `CHROMIUM_EXECUTABLE_PATH` when set (by the buildpack) and launches with `--no-sandbox` on Heroku.

### 1. Add buildpacks (order matters)

Python first, then the Playwright Python browsers buildpack, then the community buildpack for system deps:

```bash
# 1) Python (should already be set)
heroku buildpacks:add -i 1 heroku/python -a linguaformula-backend

# 2) Playwright Python – installs Chromium and sets CHROMIUM_EXECUTABLE_PATH
heroku buildpacks:add -i 2 https://github.com/Thomas-Boi/heroku-playwright-python-browsers -a linguaformula-backend

# 3) System dependencies for Chromium (required; playwright install --with-deps needs sudo)
heroku buildpacks:add -i 3 https://github.com/playwright-community/heroku-playwright-buildpack -a linguaformula-backend
```

If buildpacks already exist, use `heroku buildpacks` to list and `heroku buildpacks:remove` then add in the right order.

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
