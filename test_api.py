from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

print("\n--- Testing API Endpoints ---\n")

print("GET /:", client.get("/").json())

client.post("/set-tokens", data={
    "openai_api_key": "test-openai",
    "google_oauth": "test-google",
    "onedrive_oauth": "test-onedrive"
})
print("GET /get-tokens:", client.get("/get-tokens").json())

print("POST /upload-file:",
      client.post("/upload-file", files={"file": ("test.txt", b"hello")}).json())

print("GET /projects:", client.get("/projects").json())
print("GET /folders:", client.get("/folders").json())

print("\n--- Tests Completed ---")
