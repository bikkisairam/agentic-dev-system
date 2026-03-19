Here is the refactored code:
import generated.aa_1.app as app

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_addition():
    result = addition(1, 2)
    assert result == 3