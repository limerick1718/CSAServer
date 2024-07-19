from fastapi.testclient import TestClient
from main import app
import json

client = TestClient(app)

def test_register():
    user = {
        "username": "test_new",
        "email": "test@qwqq.com",
        "password": "asdfa"
    }
    request = client.build_request(
        method="post",
        url="/register",
        data=json.dumps(user)
    )
    response = client.send(request)
    result = response.json()
    assert result == {'message': 'user created successfully'}