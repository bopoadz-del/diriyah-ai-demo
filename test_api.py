from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    print("GET /:", response.json())

def test_set_and_get_tokens():
    response = client.post(
        "/set-tokens",
        data={
            "openai_api_key": "test-openai-key",
            "google_oauth": "test-google-oauth",
            "onedrive_oauth": "test-onedrive-oauth"
        }
    )
    print("POST /set-tokens:", response.json())

    response = client.get("/get-tokens")
    print("GET /get-tokens:", response.json())

def test_upload_file():
    file_content = b"Hello, test file content!"
    response = client.post(
        "/upload-file",
        files={"file": ("test.txt", file_content)}
    )
    print("POST /upload-file:", response.json())

def test_projects():
    response = client.get("/projects")
    print("GET /projects:", response.json())

def test_folders():
    response = client.get("/folders")
    print("GET /folders:", response.json())

if __name__ == "__main__":
    print("\n--- Testing API Endpoints ---\n")
    test_root()
    test_set_and_get_tokens()
    test_upload_file()
    test_projects()
    test_folders()
    print("\n--- Tests Completed ---")
