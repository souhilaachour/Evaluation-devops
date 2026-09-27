def test_health_ok(client):
    reponse = client.get("/health")
    assert reponse.status_code == 200
    assert reponse.json() == {"status": "ok"}


def test_creer_puis_lister_un_item(client):
    reponse = client.post("/items", json={"name": "stylo"})
    assert reponse.status_code == 201
    item_id = reponse.json()["id"]

    reponse = client.get("/items")
    assert reponse.status_code == 200
    assert {"id": item_id, "name": "stylo"} in reponse.json()


def test_item_sans_nom_refuse(client):
    reponse = client.post("/items", json={})
    assert reponse.status_code == 422