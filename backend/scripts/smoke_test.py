"""Real HTTP smoke checks using synthetic data only; never invokes Gemini."""
import argparse
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    checks = 0

    def call(path: str, expected: int = 200, data: bytes | None = None,
             headers: dict[str, str] | None = None) -> tuple[bytes, object]:
        nonlocal checks
        request = Request(base + path, data=data, headers=headers or {})
        try:
            response = urlopen(request, timeout=10)
        except HTTPError as error:
            response = error
        with response:
            body = response.read()
            assert response.status == expected, (path, response.status, body)
            checks += 1
            print(f"PASS {request.get_method()} {path}: HTTP {expected}")
            return body, response.headers

    body, _ = call("/")
    assert json.loads(body)["message"] == "Welcome to the Dishari API"
    body, _ = call("/health")
    assert json.loads(body) == {"status": "ok"}
    body, _ = call("/api/v1/rules/version")
    assert json.loads(body)["example_only"] is True
    body, _ = call("/api/v1/workflows", 201,
                   json.dumps({"facts": {"quantity": 1, "confirmed": True}}).encode(),
                   {"Content-Type": "application/json"})
    workflow = json.loads(body)
    assert workflow["state"] == "completed"
    assert workflow["result"]["rules"]["outcome"] == "passed"
    body, _ = call("/api/v1/workflows/" + workflow["id"])
    assert json.loads(body) == workflow
    body, _ = call("/api/v1/workflows", 422, b'{"facts":{"quantity":-1}}', {"Content-Type": "application/json"})
    assert json.loads(body)["code"] == "VALIDATION_ERROR"
    body, _ = call("/api/v1/workflows/not-a-uuid", 422)
    boundary = "dishari-synthetic-smoke-boundary"
    content = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"synthetic\"\r\n\r\ntrue\r\n"
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"synthetic.pdf\"\r\n"
        f"Content-Type: application/pdf\r\n\r\n%PDF-1.4\nSynthetic test only\n%%EOF\r\n--{boundary}--\r\n"
    ).encode()
    body, _ = call("/api/v1/documents", 201, content, {"Content-Type": f"multipart/form-data; boundary={boundary}"})
    assert json.loads(body)["synthetic"] is True
    body, _ = call("/docs")
    assert b"SwaggerUIBundle" in body
    body, _ = call("/openapi.json")
    assert "/api/v1/rules/version" in json.loads(body)["paths"]
    _, headers = call("/health", headers={"Origin": "http://localhost:5173"})
    assert headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
    _, headers = call("/health", headers={"Origin": "https://unlisted.example"})
    assert headers.get("Access-Control-Allow-Origin") is None
    print(f"{checks} real HTTP checks passed against {base}")


if __name__ == "__main__":
    main()
