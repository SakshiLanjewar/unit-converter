"""
Unit Converter Tool — Flask backend.

Serves the front-end (HTML/CSS/JS) and exposes a small JSON API that
performs the actual unit conversions in Python.

Endpoints
---------
GET  /                      -> renders the single-page app
GET  /api/categories        -> list of supported categories
GET  /api/units/<category>  -> units available for a category
POST /api/convert           -> performs a conversion

Run with:
    python app.py
"""

from __future__ import annotations

from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# --------------------------------------------------------------------------
# Conversion data
#
# For every "linear" category we store a dict of {unit_key: (label, factor)}
# where `factor` converts FROM that unit INTO the category's base unit.
# Temperature is handled separately because it is not a simple multiplier.
# --------------------------------------------------------------------------

LINEAR_CATEGORIES = {
    "length": {
        "base_label": "meter",
        "units": {
            "mm": ("Millimeter (mm)", 0.001),
            "cm": ("Centimeter (cm)", 0.01),
            "m": ("Meter (m)", 1),
            "km": ("Kilometer (km)", 1000),
            "in": ("Inch (in)", 0.0254),
            "ft": ("Foot (ft)", 0.3048),
            "yd": ("Yard (yd)", 0.9144),
            "mi": ("Mile (mi)", 1609.344),
            "nmi": ("Nautical Mile (nmi)", 1852),
        },
    },
    "weight": {
        "base_label": "gram",
        "units": {
            "mg": ("Milligram (mg)", 0.001),
            "g": ("Gram (g)", 1),
            "kg": ("Kilogram (kg)", 1000),
            "t": ("Metric Ton (t)", 1_000_000),
            "oz": ("Ounce (oz)", 28.349523125),
            "lb": ("Pound (lb)", 453.59237),
            "st": ("Stone (st)", 6350.29318),
        },
    },
    "volume": {
        "base_label": "liter",
        "units": {
            "ml": ("Milliliter (ml)", 0.001),
            "l": ("Liter (l)", 1),
            "m3": ("Cubic Meter (m\u00b3)", 1000),
            "tsp": ("Teaspoon (tsp)", 0.00492892),
            "tbsp": ("Tablespoon (tbsp)", 0.0147868),
            "cup": ("Cup", 0.236588),
            "pt": ("Pint (pt)", 0.473176),
            "qt": ("Quart (qt)", 0.946353),
            "gal": ("Gallon, US (gal)", 3.78541),
            "floz": ("Fluid Ounce, US (fl oz)", 0.0295735),
        },
    },
    "area": {
        "base_label": "square meter",
        "units": {
            "mm2": ("Square Millimeter (mm\u00b2)", 0.000001),
            "cm2": ("Square Centimeter (cm\u00b2)", 0.0001),
            "m2": ("Square Meter (m\u00b2)", 1),
            "ha": ("Hectare (ha)", 10000),
            "km2": ("Square Kilometer (km\u00b2)", 1_000_000),
            "in2": ("Square Inch (in\u00b2)", 0.00064516),
            "ft2": ("Square Foot (ft\u00b2)", 0.09290304),
            "yd2": ("Square Yard (yd\u00b2)", 0.83612736),
            "acre": ("Acre", 4046.8564224),
            "mi2": ("Square Mile (mi\u00b2)", 2_589_988.110336),
        },
    },
    "speed": {
        "base_label": "meter per second",
        "units": {
            "mps": ("Meters per Second (m/s)", 1),
            "kph": ("Kilometers per Hour (km/h)", 0.277778),
            "mph": ("Miles per Hour (mph)", 0.44704),
            "knot": ("Knot (kn)", 0.514444),
            "fps": ("Feet per Second (ft/s)", 0.3048),
        },
    },
    "time": {
        "base_label": "second",
        "units": {
            "ms": ("Millisecond (ms)", 0.001),
            "s": ("Second (s)", 1),
            "min": ("Minute (min)", 60),
            "hr": ("Hour (hr)", 3600),
            "day": ("Day", 86400),
            "week": ("Week", 604800),
            "month": ("Month (avg.)", 2_629_746),
            "year": ("Year (avg.)", 31_556_952),
        },
    },
    "data": {
        "base_label": "byte",
        "units": {
            "bit": ("Bit", 0.125),
            "byte": ("Byte (B)", 1),
            "kb": ("Kilobyte (KB)", 1024),
            "mb": ("Megabyte (MB)", 1024**2),
            "gb": ("Gigabyte (GB)", 1024**3),
            "tb": ("Terabyte (TB)", 1024**4),
            "pb": ("Petabyte (PB)", 1024**5),
        },
    },
    "energy": {
        "base_label": "joule",
        "units": {
            "j": ("Joule (J)", 1),
            "kj": ("Kilojoule (kJ)", 1000),
            "cal": ("Calorie (cal)", 4.184),
            "kcal": ("Kilocalorie (kcal)", 4184),
            "wh": ("Watt-hour (Wh)", 3600),
            "kwh": ("Kilowatt-hour (kWh)", 3_600_000),
            "ev": ("Electronvolt (eV)", 1.602176634e-19),
        },
    },
    "pressure": {
        "base_label": "pascal",
        "units": {
            "pa": ("Pascal (Pa)", 1),
            "kpa": ("Kilopascal (kPa)", 1000),
            "bar": ("Bar", 100000),
            "psi": ("PSI (psi)", 6894.757293168),
            "atm": ("Atmosphere (atm)", 101325),
            "torr": ("Torr", 133.322368421),
        },
    },
}

TEMPERATURE_UNITS = {
    "c": "Celsius (\u00b0C)",
    "f": "Fahrenheit (\u00b0F)",
    "k": "Kelvin (K)",
}

CATEGORY_LABELS = {
    "length": "Length",
    "weight": "Weight / Mass",
    "temperature": "Temperature",
    "volume": "Volume",
    "area": "Area",
    "speed": "Speed",
    "time": "Time",
    "data": "Data Storage",
    "energy": "Energy",
    "pressure": "Pressure",
}

# Order in which categories should appear in the UI.
CATEGORY_ORDER = [
    "length", "weight", "temperature", "volume", "area",
    "speed", "time", "data", "energy", "pressure",
]


class ConversionError(ValueError):
    """Raised for any user-facing conversion problem."""


def _celsius_to_kelvin(c: float) -> float:
    return c + 273.15


def _kelvin_to_celsius(k: float) -> float:
    return k - 273.15


def convert_temperature(value: float, from_unit: str, to_unit: str) -> float:
    if from_unit not in TEMPERATURE_UNITS or to_unit not in TEMPERATURE_UNITS:
        raise ConversionError("Unknown temperature unit.")

    # Normalize to Celsius first.
    if from_unit == "c":
        celsius = value
    elif from_unit == "f":
        celsius = (value - 32) * 5 / 9
    elif from_unit == "k":
        celsius = _kelvin_to_celsius(value)

    # Basic sanity check: absolute zero is -273.15 C / 0 K / -459.67 F
    if celsius < -273.15 - 1e-9:
        raise ConversionError("Value is below absolute zero.")

    if to_unit == "c":
        return celsius
    if to_unit == "f":
        return celsius * 9 / 5 + 32
    if to_unit == "k":
        return _celsius_to_kelvin(celsius)

    raise ConversionError("Unknown temperature unit.")  # pragma: no cover


def convert_linear(category: str, value: float, from_unit: str, to_unit: str) -> float:
    data = LINEAR_CATEGORIES.get(category)
    if data is None:
        raise ConversionError(f"Unknown category '{category}'.")

    units = data["units"]
    if from_unit not in units:
        raise ConversionError(f"Unknown unit '{from_unit}' for category '{category}'.")
    if to_unit not in units:
        raise ConversionError(f"Unknown unit '{to_unit}' for category '{category}'.")

    _, from_factor = units[from_unit]
    _, to_factor = units[to_unit]

    base_value = value * from_factor
    return base_value / to_factor


def perform_conversion(category: str, value: float, from_unit: str, to_unit: str) -> float:
    if category == "temperature":
        return convert_temperature(value, from_unit, to_unit)
    return convert_linear(category, value, from_unit, to_unit)


def get_units_payload(category: str):
    if category == "temperature":
        return [{"key": k, "label": v} for k, v in TEMPERATURE_UNITS.items()]

    data = LINEAR_CATEGORIES.get(category)
    if data is None:
        return None

    return [{"key": k, "label": v[0]} for k, v in data["units"].items()]


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/categories")
def api_categories():
    payload = [
        {"key": key, "label": CATEGORY_LABELS[key]}
        for key in CATEGORY_ORDER
    ]
    return jsonify({"categories": payload})


@app.route("/api/units/<category>")
def api_units(category):
    units = get_units_payload(category)
    if units is None:
        return jsonify({"error": f"Unknown category '{category}'."}), 404
    return jsonify({"category": category, "units": units})


@app.route("/api/convert", methods=["POST"])
def api_convert():
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "Request body must be valid JSON."}), 400

    category = payload.get("category")
    from_unit = payload.get("from_unit")
    to_unit = payload.get("to_unit")
    raw_value = payload.get("value")

    if not category or not from_unit or not to_unit:
        return jsonify({"error": "Fields 'category', 'from_unit' and 'to_unit' are required."}), 400

    if raw_value is None or str(raw_value).strip() == "":
        return jsonify({"error": "Please enter a numeric value."}), 400

    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return jsonify({"error": "Value must be a valid number."}), 400

    if value != value or value in (float("inf"), float("-inf")):  # NaN / Inf guard
        return jsonify({"error": "Value must be a finite number."}), 400

    try:
        result = perform_conversion(category, value, from_unit, to_unit)
    except ConversionError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:  # pragma: no cover - safety net for unexpected errors
        return jsonify({"error": "Something went wrong while converting. Please try again."}), 500

    return jsonify({
        "category": category,
        "from_unit": from_unit,
        "to_unit": to_unit,
        "input": value,
        "result": result,
    })


@app.errorhandler(404)
def not_found(_error):
    return jsonify({"error": "Not found."}), 404


@app.errorhandler(500)
def server_error(_error):  # pragma: no cover - safety net
    return jsonify({"error": "Internal server error."}), 500


if __name__ == "__main__":
    import os

    # Debug mode defaults to ON for local development (same as before).
    # Set FLASK_DEBUG=0 to turn it off, e.g. when running on a server.
    debug_mode = os.environ.get("FLASK_DEBUG", "1") != "0"
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=debug_mode, port=port)
