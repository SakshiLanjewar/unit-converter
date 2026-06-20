"""
Automated tests for the Unit Converter Flask app.

Run with:
    pytest
"""

import pytest
from app import app, LINEAR_CATEGORIES, TEMPERATURE_UNITS


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# --------------------------------------------------------------------------
# Pages & static assets
# --------------------------------------------------------------------------

def test_index_page_loads(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Unit Converter" in resp.data


def test_static_assets_serve(client):
    assert client.get("/static/css/style.css").status_code == 200
    assert client.get("/static/js/script.js").status_code == 200


# --------------------------------------------------------------------------
# /api/categories
# --------------------------------------------------------------------------

def test_categories_endpoint(client):
    resp = client.get("/api/categories")
    assert resp.status_code == 200
    data = resp.get_json()
    keys = [c["key"] for c in data["categories"]]
    assert "length" in keys
    assert "temperature" in keys
    assert len(keys) == 10


# --------------------------------------------------------------------------
# /api/units/<category>
# --------------------------------------------------------------------------

def test_units_known_category(client):
    resp = client.get("/api/units/length")
    assert resp.status_code == 200
    units = [u["key"] for u in resp.get_json()["units"]]
    assert "m" in units and "ft" in units


def test_units_unknown_category(client):
    resp = client.get("/api/units/not-a-real-category")
    assert resp.status_code == 404
    assert "error" in resp.get_json()


# --------------------------------------------------------------------------
# /api/convert — happy paths
# --------------------------------------------------------------------------

def test_convert_length(client):
    resp = client.post("/api/convert", json={
        "category": "length", "from_unit": "mi", "to_unit": "m", "value": 1
    })
    assert resp.status_code == 200
    assert resp.get_json()["result"] == pytest.approx(1609.344)


def test_convert_temperature_c_to_f(client):
    resp = client.post("/api/convert", json={
        "category": "temperature", "from_unit": "c", "to_unit": "f", "value": 100
    })
    assert resp.status_code == 200
    assert resp.get_json()["result"] == pytest.approx(212)


def test_convert_temperature_k_to_c(client):
    resp = client.post("/api/convert", json={
        "category": "temperature", "from_unit": "k", "to_unit": "c", "value": 0
    })
    assert resp.status_code == 200
    assert resp.get_json()["result"] == pytest.approx(-273.15)


def test_convert_data_storage(client):
    resp = client.post("/api/convert", json={
        "category": "data", "from_unit": "gb", "to_unit": "mb", "value": 1
    })
    assert resp.get_json()["result"] == pytest.approx(1024)


# --------------------------------------------------------------------------
# /api/convert — error paths
# --------------------------------------------------------------------------

def test_convert_missing_fields(client):
    resp = client.post("/api/convert", json={"category": "length"})
    assert resp.status_code == 400


def test_convert_bad_number(client):
    resp = client.post("/api/convert", json={
        "category": "length", "from_unit": "m", "to_unit": "ft", "value": "abc"
    })
    assert resp.status_code == 400


def test_convert_empty_value(client):
    resp = client.post("/api/convert", json={
        "category": "length", "from_unit": "m", "to_unit": "ft", "value": ""
    })
    assert resp.status_code == 400


def test_convert_unknown_category(client):
    resp = client.post("/api/convert", json={
        "category": "bogus", "from_unit": "m", "to_unit": "ft", "value": 1
    })
    assert resp.status_code == 400


def test_convert_unknown_unit(client):
    resp = client.post("/api/convert", json={
        "category": "length", "from_unit": "xx", "to_unit": "ft", "value": 1
    })
    assert resp.status_code == 400


def test_convert_non_json_body(client):
    resp = client.post("/api/convert", data="not json", content_type="text/plain")
    assert resp.status_code == 400


def test_convert_infinite_value_rejected(client):
    resp = client.post("/api/convert", json={
        "category": "length", "from_unit": "m", "to_unit": "ft", "value": "Infinity"
    })
    assert resp.status_code == 400


def test_convert_below_absolute_zero_rejected(client):
    resp = client.post("/api/convert", json={
        "category": "temperature", "from_unit": "k", "to_unit": "c", "value": -10
    })
    assert resp.status_code == 400


def test_unknown_route_returns_404(client):
    resp = client.get("/api/does-not-exist")
    assert resp.status_code == 404


# --------------------------------------------------------------------------
# Round-trip correctness across every category/unit pair
# --------------------------------------------------------------------------

def test_round_trip_every_linear_unit(client):
    """Converting base -> unit -> base should return the original value."""
    for category, info in LINEAR_CATEGORIES.items():
        units = list(info["units"].keys())
        base = units[0]
        for unit in units:
            forward = client.post("/api/convert", json={
                "category": category, "from_unit": base, "to_unit": unit, "value": 1
            }).get_json()["result"]

            back = client.post("/api/convert", json={
                "category": category, "from_unit": unit, "to_unit": base, "value": forward
            }).get_json()["result"]

            assert back == pytest.approx(1, rel=1e-6), f"{category}:{unit} round-trip failed"


def test_round_trip_temperature(client):
    for from_u in TEMPERATURE_UNITS:
        for to_u in TEMPERATURE_UNITS:
            start_value = 25 if from_u == "c" else (77 if from_u == "f" else 298.15)
            forward = client.post("/api/convert", json={
                "category": "temperature", "from_unit": from_u, "to_unit": to_u, "value": start_value
            }).get_json()["result"]

            back = client.post("/api/convert", json={
                "category": "temperature", "from_unit": to_u, "to_unit": from_u, "value": forward
            }).get_json()["result"]

            assert back == pytest.approx(start_value, rel=1e-6), f"temperature:{from_u}->{to_u} round-trip failed"
