def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-request-id"]


def test_original_welcome(client):
    assert client.get("/").json() == {"message": "Welcome to the Dishari API"}


def test_swagger_and_documented_responses(client):
    response = client.get("/docs")
    assert response.status_code == 200
    assert "SwaggerUIBundle" in response.text
    spec = client.get("/openapi.json").json()
    for path, method, status in [
        ("/health", "get", "200"),
        ("/api/v1/workflows", "post", "201"),
        ("/api/v1/workflows/{workflow_id}", "get", "200"),
        ("/api/v1/documents", "post", "201"),
        ("/api/v1/rules/version", "get", "200"),
    ]:
        responses = spec["paths"][path][method]["responses"]
        assert responses[status]["content"]["application/json"]["schema"]["$ref"]
        assert responses["422"]["content"]["application/json"]["schema"]["$ref"].endswith("/ErrorResponse")


def test_cors_preflight(client):
    allowed = client.options("/api/v1/workflows", headers={
        "Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type",
    })
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    denied = client.get("/health", headers={"Origin": "https://unlisted.example"})
    assert "access-control-allow-origin" not in denied.headers
