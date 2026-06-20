# Unit Converter

A precision-instrument styled unit converter built with **Python (Flask)** on the
backend and **HTML/CSS/JavaScript** on the frontend. All conversion math runs in
Python and is exposed through a small JSON API; the browser only handles
input, display, and talking to that API.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Flask](https://img.shields.io/badge/Flask-3.x-black)
![License](https://img.shields.io/badge/license-MIT-green)
![CI](https://github.com/SakshiLanjewar/unit-converter/actions/workflows/ci.yml/badge.svg)

---

## Features

- **10 conversion categories**: Length, Weight/Mass, Temperature, Volume, Area,
  Speed, Time, Data Storage, Energy, Pressure.
- **40+ units** across those categories (metric, imperial, and a few specialty
  units like knots, stones, and electronvolts).
- **Correct temperature math** — Celsius/Fahrenheit/Kelvin are handled as true
  offset conversions, not linear factors, with an absolute-zero guard.
- **Live conversion** — results update automatically as you type (debounced)
  or change a unit, no "Convert" button needed.
- **Swap button** to instantly flip the From/To units.
- **Copy result** to the clipboard in one click.
- **Conversion log** — keeps your last 10 conversions, saved in the browser
  (`localStorage`) so it survives a page reload; clearable any time.
- **"1 X = Y Z" formula line** under the readout so you can see the
  conversion rate at a glance.
- **Full input validation and error handling**, on both ends:
  - Empty / non-numeric input is caught client-side before it ever reaches
    the server.
  - The server independently validates category, units, and value, and
    returns clear JSON error messages with proper HTTP status codes
    (`400` for bad input, `404` for unknown routes, `500` only as a last
    resort safety net).
  - Network/API failures (e.g. the server isn't running) show a friendly
    inline message instead of a blank screen or console error.
- **Keyboard support** — `Enter` converts immediately, `Esc` clears the
  field.
- **Responsive design** — works down to small mobile screens; the two
  readout "ports" stack vertically and the swap button rotates accordingly.
- **Accessible** — labeled form controls, `aria-live` result region, visible
  focus states, and `prefers-reduced-motion` support.

## Project structure

```
unit-converter/
├── .github/
│   └── workflows/
│       └── ci.yml           # GitHub Actions: runs tests on every push/PR
├── tests/
│   └── test_app.py          # Automated test suite (pytest)
├── app.py                   # Flask app: routes + all conversion logic
├── conftest.py              # Empty file — lets pytest resolve `import app`
├── Procfile                 # Tells a host (e.g. Render) how to start the app
├── requirements.txt         # Runtime dependencies (Flask, gunicorn)
├── requirements-dev.txt     # Runtime + test dependencies (pytest)
├── .gitignore
├── .gitattributes
├── LICENSE                  # MIT
├── README.md
├── templates/
│   └── index.html           # Single-page UI
└── static/
    ├── css/
    │   └── style.css        # Visual design (blueprint/instrument theme)
    └── js/
        └── script.js        # Front-end logic (fetches the API, renders UI)
```

## How it works

1. The browser loads `/`, which Flask renders from `templates/index.html`.
2. On load, `script.js` calls `GET /api/categories` to build the category
   buttons, then `GET /api/units/<category>` to populate the "From"/"To"
   dropdowns for whichever category is selected.
3. Whenever you type a value or change a unit, the page sends
   `POST /api/convert` with `{ category, from_unit, to_unit, value }`.
4. `app.py` validates the request and performs the conversion in Python
   (using per-category factor tables, or dedicated formulas for
   temperature), then returns `{ result, ... }` as JSON.
5. The page formats and displays the result, updates the formula line, and
   logs the conversion to the history panel.

## Getting started

### Prerequisites

- Python 3.8 or newer
- `pip`

### Installation

```bash
# 1. Move into the project folder
cd unit-converter

# 2. (Recommended) create a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

### Run it

```bash
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

> The app runs in debug mode by default for local development (auto-reload
> on file changes). See [Deployment](#deployment) below for running it in
> production.

## API reference

All responses are JSON.

### `GET /api/categories`

Returns the list of supported categories.

```json
{ "categories": [{ "key": "length", "label": "Length" }, ...] }
```

### `GET /api/units/<category>`

Returns the units available for a category.

```json
{
  "category": "length",
  "units": [{ "key": "m", "label": "Meter (m)" }, ...]
}
```

`404` if the category doesn't exist.

### `POST /api/convert`

**Body:**

```json
{ "category": "length", "from_unit": "mi", "to_unit": "m", "value": 1 }
```

**Success (200):**

```json
{
  "category": "length",
  "from_unit": "mi",
  "to_unit": "m",
  "input": 1.0,
  "result": 1609.344
}
```

**Error (400):**

```json
{ "error": "Value must be a valid number." }
```

## Supported categories & units

| Category      | Units |
|---------------|-------|
| Length        | mm, cm, m, km, in, ft, yd, mi, nautical mile |
| Weight / Mass | mg, g, kg, metric ton, oz, lb, stone |
| Temperature   | Celsius, Fahrenheit, Kelvin |
| Volume        | ml, l, m³, tsp, tbsp, cup, pt, qt, gal (US), fl oz (US) |
| Area          | mm², cm², m², hectare, km², in², ft², yd², acre, mi² |
| Speed         | m/s, km/h, mph, knot, ft/s |
| Time          | ms, s, min, hr, day, week, month (avg.), year (avg.) |
| Data Storage  | bit, byte, KB, MB, GB, TB, PB (binary/1024-based) |
| Energy        | J, kJ, cal, kcal, Wh, kWh, eV |
| Pressure      | Pa, kPa, bar, psi, atm, torr |

## Tech stack

- **Backend:** Python 3, [Flask](https://flask.palletsprojects.com/)
- **Frontend:** vanilla HTML5, CSS3 (custom properties, CSS Grid/Flexbox, no
  framework), vanilla JavaScript (no build step, no dependencies)
- **Fonts:** Space Grotesk (display), Inter (UI text), JetBrains Mono
  (numeric readouts), loaded from Google Fonts

## Testing & CI

A `pytest` suite in `tests/test_app.py` covers:

- Page and static asset loading
- Every API endpoint's happy path
- Every error path (missing fields, non-numeric input, unknown
  category/unit, malformed JSON, infinite/NaN values, the temperature
  absolute-zero guard, unknown routes)
- A round-trip check (convert every unit to its category's base unit and
  back) across all 10 categories, confirming the math is correct to within
  floating-point tolerance

Run it locally:

```bash
pip install -r requirements-dev.txt
pytest -v
```

> The empty `conftest.py` at the project root exists so pytest adds the
> project root to `sys.path` — without it, `tests/test_app.py` can't
> `import app` since it lives one directory up.

A GitHub Actions workflow (`.github/workflows/ci.yml`) runs this same suite
automatically on every push and pull request against `main`, on Python 3.9,
3.11, and 3.12 — so any change that breaks something is caught before it's
merged.

## Configuration

The app reads two optional environment variables, useful if you ever deploy
it instead of just running it locally:

| Variable      | Default | Purpose |
|---------------|---------|---------|
| `FLASK_DEBUG` | `1`     | Set to `0` to turn off Flask's debug/auto-reload mode (recommended for anything other than local development). |
| `PORT`        | `5000`  | Which port the dev server listens on. |

```bash
FLASK_DEBUG=0 PORT=8080 python app.py
```

## Deployment

The app is deployment-ready out of the box:

- **`requirements.txt`** includes [`gunicorn`](https://gunicorn.org/), a
  production-grade WSGI server (Flask's built-in dev server is fine for
  local use but isn't meant to serve real traffic).
- **`Procfile`** tells a hosting platform how to start the app in
  production:
  ```
  web: gunicorn app:app
  ```

### Deploying to Render (free)

1. Push this repo to GitHub.
2. On [render.com](https://render.com), create a **New Web Service** and
   connect this repo.
3. Configure:
   | Field | Value |
   |---|---|
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `gunicorn app:app` |
   | Instance Type | Free |
4. Add an environment variable: `FLASK_DEBUG=0`.
5. Click **Create Web Service**. Render builds and deploys automatically,
   and redeploys on every future push to `main`.

> Render's free tier sleeps after ~15 minutes of inactivity; the first
> request after that takes 30–50s to "wake" the service back up. This is
> fine for personal/portfolio projects; a paid tier removes the sleep.

The same `Procfile` / `gunicorn app:app` setup works on most other
Python-friendly hosts (Railway, Heroku, Fly.io, PythonAnywhere, etc.) with
minor platform-specific configuration.

## Possible extensions

- Add more categories (currency, angle, fuel economy, cooking units)
- Add a dark theme toggle
- Add a "favorite conversions" pinned list
- Package as a desktop app (e.g. with PyInstaller) or a PWA

## License

MIT — see [LICENSE](LICENSE). Before pushing to GitHub, open `LICENSE` and
replace `Your Name` with your actual name or GitHub username.