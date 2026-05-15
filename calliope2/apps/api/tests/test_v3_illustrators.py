"""GET /v3/illustrators — list available illustrators with admin-aware filtering."""

from __future__ import annotations

from sqlalchemy import update

from calliope2.db.models import User


async def test_lists_non_experimental_illustrators(client):
    response = await client.get("/v3/illustrators")
    assert response.status_code == 200
    items = response.json()
    names = sorted(i["name"] for i in items)
    # All 5 currently-shipped illustrators are non-experimental
    assert names == [
        "charcoal_abstract",
        "cinematic_motion",
        "cinematic_photo",
        "film_noir",
        "period_photo",
    ]
    by_name = {i["name"]: i for i in items}
    assert by_name["cinematic_motion"]["outputs"] == "video"
    assert by_name["cinematic_photo"]["outputs"] == "image"
    assert all(not i["experimental"] for i in items)


async def test_admin_sees_experimental_illustrators(
    client, db_sessionmaker, monkeypatch, tmp_path
):
    """Drop an experimental illustrator into a tmpdir, repoint the loader,
    flip is_admin, verify behaviour."""
    from calliope2.illustrators import runtime as ill_runtime

    # Build a tmp defs/ with one experimental illustrator alongside the real defs/.
    tmp_defs = tmp_path / "defs"
    tmp_defs.mkdir()
    (tmp_defs / "secret.yaml").write_text(
        """
name: secret
description: An admin-only illustrator
outputs: image
inputs:
  required: [source]
experimental: true
steps:
  - generate_image:
      provider: openai
      model: m
      prompt: "{{ source }}"
      out: r
output: r
"""
    )
    # Copy real illustrators so list_illustrators still finds them.
    for real in (ill_runtime.DEFS_DIR).glob("*.yaml"):
        (tmp_defs / real.name).write_text(real.read_text())

    monkeypatch.setattr(ill_runtime, "DEFS_DIR", tmp_defs)
    from calliope2.illustrators import registry as ill_registry
    monkeypatch.setattr(ill_registry, "DEFS_DIR", tmp_defs)

    # Non-admin: does not see "secret"
    response = await client.get("/v3/illustrators")
    assert response.status_code == 200
    names = {i["name"] for i in response.json()}
    assert "secret" not in names

    # Promote to admin
    await client.get("/v3/storytellers")  # auto-create user
    async with db_sessionmaker() as s:
        await s.execute(
            update(User).where(User.firebase_uid == "test-uid-1").values(is_admin=True)
        )
        await s.commit()

    response = await client.get("/v3/illustrators")
    assert response.status_code == 200
    names = {i["name"] for i in response.json()}
    assert "secret" in names
