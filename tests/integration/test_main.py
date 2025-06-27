from fastapi.testclient import TestClient


def test_read_root(client: TestClient):
    """
    Tests that the root endpoint returns the correct welcome message.
    This is an integration test that uses the client fixture, which provides
    a fully configured app instance connected to a test database.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the Image to PDF Converter API"}
