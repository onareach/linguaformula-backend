# Exam Sheet PDF Pipeline

The exam-sheet PDF is generated server-side with Playwright (headless Chromium).

## Local

1. Install Python deps: `pip install -r requirements.txt`
2. Install Chromium for Playwright: `playwright install chromium`

## Heroku

Playwright needs a Chromium binary. Options:

1. **Buildpack**: Use [heroku-buildpack-google-chrome](https://github.com/heroku/heroku-buildpack-google-chrome) or a Playwright buildpack so Chromium is available at runtime. Then set `PLAYWRIGHT_BROWSERS_PATH` or use the buildpack’s path.

2. **Or** run `playwright install chromium` in the build phase (e.g. in a `bin/post_compile` or in the buildpack) so Chromium is installed in the slug.

Without Chromium on the server, `GET /api/exam_sheet/pdf` will fail at runtime when `html_to_pdf()` runs.
