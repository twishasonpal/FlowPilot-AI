import pytest
from app import create_app

@pytest.fixture
def client(tmp_path):
    app=create_app({"TESTING":True,"DATABASE_URL":f"sqlite:///{tmp_path / 'test.db'}"})
    return app.test_client()
