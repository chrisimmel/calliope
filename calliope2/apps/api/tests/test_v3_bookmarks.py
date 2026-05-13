from __future__ import annotations

from sqlalchemy import select

from calliope2.db.models import Bookmark, Story, StoryFrame, User


async def _make_story(db_sessionmaker, owner_id: int) -> int:
    async with db_sessionmaker() as setup:
        story = Story(owner_id=owner_id, storyteller_name="literal", title="T")
        setup.add(story)
        await setup.commit()
        return story.id


async def _get_test_user_id(session) -> int:
    return (await session.scalar(select(User.id).where(User.firebase_uid == "test-uid-1")))


async def test_create_bookmark_persists_and_returns_row(client, session, db_sessionmaker):
    # First call any authenticated route to auto-create the User
    await client.get("/v3/storytellers")
    user_id = await _get_test_user_id(session)
    story_id = await _make_story(db_sessionmaker, owner_id=user_id)

    response = await client.post(
        "/v3/bookmarks",
        json={"story_id": story_id, "list_name": "favorites", "is_public": False},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["story_id"] == story_id
    assert body["list_name"] == "favorites"
    assert body["is_public"] is False
    assert body["frame_id"] is None

    rows = (await session.execute(select(Bookmark))).scalars().all()
    assert len(rows) == 1


async def test_create_bookmark_404_when_story_not_owned(client, db_sessionmaker):
    async with db_sessionmaker() as setup:
        other = User(firebase_uid="someone-else")
        setup.add(other)
        await setup.flush()
        s = Story(owner_id=other.id, storyteller_name="literal")
        setup.add(s)
        await setup.commit()
        other_story_id = s.id

    response = await client.post(
        "/v3/bookmarks",
        json={"story_id": other_story_id},
    )
    assert response.status_code == 404


async def test_create_bookmark_404_when_frame_belongs_to_different_story(
    client, session, db_sessionmaker
):
    await client.get("/v3/storytellers")
    user_id = await _get_test_user_id(session)
    mine = await _make_story(db_sessionmaker, owner_id=user_id)
    theirs = await _make_story(db_sessionmaker, owner_id=user_id)
    async with db_sessionmaker() as setup:
        frame = StoryFrame(story_id=theirs, number=1, text="x")
        setup.add(frame)
        await setup.commit()
        frame_id = frame.id

    response = await client.post(
        "/v3/bookmarks",
        json={"story_id": mine, "frame_id": frame_id},
    )
    assert response.status_code == 404


async def test_list_bookmarks_returns_only_own(client, session, db_sessionmaker):
    await client.get("/v3/storytellers")
    user_id = await _get_test_user_id(session)
    mine = await _make_story(db_sessionmaker, owner_id=user_id)

    async with db_sessionmaker() as setup:
        other = User(firebase_uid="other")
        setup.add(other)
        await setup.flush()
        their_story = Story(owner_id=other.id, storyteller_name="literal")
        setup.add(their_story)
        await setup.flush()
        setup.add_all([
            Bookmark(owner_id=user_id, story_id=mine, list_name="A"),
            Bookmark(owner_id=other.id, story_id=their_story.id, list_name="B"),
        ])
        await setup.commit()

    response = await client.get("/v3/bookmarks")
    assert response.status_code == 200
    names = [b["list_name"] for b in response.json()]
    assert names == ["A"]


async def test_delete_bookmark_succeeds(client, session, db_sessionmaker):
    await client.get("/v3/storytellers")
    user_id = await _get_test_user_id(session)
    story_id = await _make_story(db_sessionmaker, owner_id=user_id)

    async with db_sessionmaker() as setup:
        bm = Bookmark(owner_id=user_id, story_id=story_id, list_name="x")
        setup.add(bm)
        await setup.commit()
        bm_id = bm.id

    response = await client.delete(f"/v3/bookmarks/{bm_id}")
    assert response.status_code == 204
    remaining = (await session.execute(select(Bookmark))).scalars().all()
    assert remaining == []


async def test_delete_bookmark_404_when_not_owned(client, db_sessionmaker):
    async with db_sessionmaker() as setup:
        other = User(firebase_uid="other")
        setup.add(other)
        await setup.flush()
        s = Story(owner_id=other.id, storyteller_name="literal")
        setup.add(s)
        await setup.flush()
        bm = Bookmark(owner_id=other.id, story_id=s.id)
        setup.add(bm)
        await setup.commit()
        bm_id = bm.id

    response = await client.delete(f"/v3/bookmarks/{bm_id}")
    assert response.status_code == 404
