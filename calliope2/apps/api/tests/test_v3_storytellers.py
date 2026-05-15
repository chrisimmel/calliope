async def test_list_storytellers(client):
    response = await client.get("/v3/storytellers")
    assert response.status_code == 200
    body = response.json()
    names = sorted(s["name"] for s in body)
    assert names == ["fern", "lavender", "literal", "narcissus", "simple_one_frame"]
    for entry in body:
        assert entry["description"]  # every storyteller has a description
