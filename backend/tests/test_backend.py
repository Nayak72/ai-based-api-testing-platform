import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token,
)
from app.db.models import (
    Assertion,
    ExpectedResponse,
    RequestSent,
    RequestTemplate,
    ResponseReceived,
    TestCaseBase,
    TestCaseMetadata,
    UserBase,
    UserInDB,
)
from app.executor.assertions import evaluate_assertions
from app.main import app
from app.parsers.openapi import parse_openapi_spec
from app.parsers.postman import parse_postman_collection


def test_password_hashing():
    pw = "SuperSecurePassword123!"
    hashed = hash_password(pw)
    assert verify_password(pw, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_tokens():
    user_id = str(ObjectId())
    access_token = create_access_token(user_id)
    assert verify_token(access_token, "access") == user_id
    assert verify_token(access_token, "refresh") is None

    refresh_token = create_refresh_token(user_id)
    assert verify_token(refresh_token, "refresh") == user_id
    assert verify_token(refresh_token, "access") is None


def test_pydantic_objectid_models():
    user_id = ObjectId()
    user = UserInDB(
        _id=user_id,
        email="test@example.com",
        password_hash="hashed",
    )
    assert user.id == user_id
    assert user.email == "test@example.com"

    tc = TestCaseBase(
        spec_id=ObjectId(),
        endpoint_id="get_users",
        category="functional",
        subcategory="happy_path",
        title="Get Users List",
        description="Verify users can be fetched",
        request=RequestTemplate(method="GET", path="/users"),
        expected=ExpectedResponse(status_code=200),
        metadata=TestCaseMetadata(
            generated_by="ai",
            generation_prompt_hash="hash",
            tokens_used=100,
            request_hash="reqhash",
        ),
    )
    assert isinstance(tc.spec_id, ObjectId)
    assert tc.endpoint_id == "get_users"


def test_assertions_evaluator():
    assertions = [
        Assertion(type="status_code", path="", operator="eq", value=200),
        Assertion(type="header", path="content-type", operator="contains", value="application/json"),
        Assertion(type="json_path", path="$.users[0].id", operator="eq", value=1),
    ]
    results = evaluate_assertions(
        assertions=assertions,
        status_code=200,
        headers={"content-type": "application/json; charset=utf-8"},
        body='{"users": [{"id": 1, "name": "Alice"}]}',
    )
    assert len(results) == 3
    assert all(r.result for r in results)


@pytest.mark.asyncio
async def test_openapi_parser():
    sample_spec = """
openapi: 3.0.3
info:
  title: Test API
  version: 1.0.0
paths:
  /users:
    get:
      summary: List users
      responses:
        '200':
          description: OK
"""
    spec, endpoints, version, base_url = await parse_openapi_spec(sample_spec)
    assert spec["info"]["title"] == "Test API"
    assert len(endpoints) == 1
    assert endpoints[0]["method"] == "GET"
    assert endpoints[0]["path"] == "/users"
    assert version == "3.0.3"


@pytest.mark.asyncio
async def test_postman_parser():
    sample_postman = """{
  "info": {
    "name": "Sample Postman Collection",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Get Items",
      "request": {
        "method": "GET",
        "url": {
          "raw": "https://api.example.com/items",
          "path": ["items"]
        }
      }
    }
  ]
}"""
    spec, endpoints, version, base_url = await parse_postman_collection(sample_postman)
    assert spec["info"]["title"] == "Sample Postman Collection"
    assert len(endpoints) == 1
    assert endpoints[0]["method"] == "GET"
    assert endpoints[0]["path"] == "/items"


def test_health_check():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
