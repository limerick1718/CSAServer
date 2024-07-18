from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_register():
    user = {
        "username": "test",
        "email": "test@qwq.com",
        "password": "asdfa"
    }
    request = client.build_request(
        method="post",
        url="/register",
        data=user
    )
    response = client.send(request)
    result = response.json()
    detail = result["detail"]
    assert detail == "Email already registered"
    assert response.status_code == 200