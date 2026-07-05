import pytest
from fastapi.testclient import TestClient
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import app
from database import init_db

client = TestClient(app)

def test_api_endpoints():
    # Make sure DB is initialized
    init_db()

    # Get comics (should be empty initially)
    response = client.get("/api/comics")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    # Try fetching a non-existent cover or progress
    response = client.get("/api/comics/nonexistent/cover")
    assert response.status_code == 404

    response = client.post("/api/comics/nonexistent/progress", json={"page": 5, "panel": 2})
    assert response.status_code == 200
