# Authentication

All `/v3/*` endpoints require a Firebase ID token. There's no anonymous
access. Admin routes additionally require `User.is_admin = True`.

## The flow

```
Browser                   FastAPI                              Postgres
───────                   ───────                              ────────
1. signInWithPopup(GoogleAuthProvider)
   → idToken
2. Authorization: Bearer <idToken> ───►
                          3. HTTPBearer dependency extracts the token
                          4. get_firebase_claims:
                             firebase_admin.verify_id_token()
                             → decoded claims {uid, email, name, ...}
                          5. get_current_user(claims, session):
                             SELECT user WHERE firebase_uid = claims.uid
                                                                ◄── row?
                             if not found:
                               INSERT users (firebase_uid, email, display_name)
                                                                ──► new row
                             attach to request.state.user
                          6. route handler runs with `user: CurrentUser`
                ◄── 200 ───
```

Failures map to status codes:
- Missing / malformed `Authorization` header → **401** (HTTPBearer's default)
- Token signature invalid, expired, or wrong audience → **401**
- Valid token but route requires admin → **403**

## Code map

| File | Role |
|---|---|
| [`auth/firebase.py`](../../apps/api/calliope2/auth/firebase.py) | Lazy-init `firebase_admin` App; `verify_id_token(token)` returns claims |
| [`auth/dependencies.py`](../../apps/api/calliope2/auth/dependencies.py) | The FastAPI dependency chain — `HTTPBearer` → `get_firebase_claims` → `get_current_user` (+ `require_admin`); type aliases `CurrentUser`, `SessionDep`, `AdminUser` |
| [`auth/__init__.py`](../../apps/api/calliope2/auth/__init__.py) | Public re-exports |

## Dependency aliases

```python
from calliope2.auth import CurrentUser, AdminUser, SessionDep

@router.get("/v3/stories")
async def list_stories(user: CurrentUser, session: SessionDep):
    ...

@router.get("/v3/admin/stories")
async def admin_list(user: AdminUser, session: SessionDep):
    ...
```

`CurrentUser = Annotated[User, Depends(get_current_user)]` — any
authenticated user. `AdminUser = Annotated[User, Depends(require_admin)]`
— same, but rejects with 403 unless `user.is_admin`. `SessionDep =
Annotated[AsyncSession, Depends(get_session)]` — the per-request DB
session.

These aliases must stay at **module level** (not `TYPE_CHECKING`) —
FastAPI evaluates `Annotated[T, Depends(...)]` at runtime. See
[`ADR 0008`](../decisions/0008-fastapi-runtime-annotations.md).

## User auto-creation

When a Firebase UID hits `/v3/*` for the first time, a `User` row is
created automatically:

```python
user = await session.scalar(select(User).where(User.firebase_uid == uid))
if user is None:
    user = User(
        firebase_uid=uid,
        email=claims.get("email"),
        display_name=claims.get("name") or claims.get("display_name"),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
```

**Existing rows are not overwritten.** If `display_name` or `is_admin`
were edited (e.g., by an admin promoting a user), subsequent sign-ins
won't reset them.

## Admin gating

Setting `is_admin` is a manual database write today — there's no
self-service endpoint. The intended flow:

1. New user signs in normally; their row is created with `is_admin=False`.
2. An existing admin runs:
   ```sql
   UPDATE users SET is_admin = true WHERE email = 'newadmin@example.com';
   ```
   (or eventually, `calliope2-cli users grant-admin <email>` — not built yet.)
3. The promoted user can now access `/v3/admin/*` and the admin SPA.

Admin routes live under `apps/api/calliope2/api/v3/admin/` and all use
`AdminUser`. See [`apps/api/calliope2/api/v3/admin/`](../../apps/api/calliope2/api/v3/admin/).

## Configuration

| Setting | Env var | Default | What it does |
|---|---|---|---|
| `firebase_project_id` | `CALLIOPE2_FIREBASE_PROJECT_ID` | `""` | Firebase project. When empty, `verify_id_token` will still fail any real token; useful only for tests. |

`firebase_admin.initialize_app()` uses `ApplicationDefault()` credentials
— in Cloud Run this picks up the service-account identity automatically;
locally it reads `GOOGLE_APPLICATION_CREDENTIALS`.

## Tests

[`apps/api/tests/test_v3_auth.py`](../../apps/api/tests/test_v3_auth.py) covers:
- Missing bearer header → 401
- Valid bearer → User auto-created
- Existing user → not duplicated, `display_name` / `is_admin` preserved
- Invalid token → 401 with `WWW-Authenticate: Bearer`

Tests override `get_firebase_claims` via `app.dependency_overrides` to
short-circuit the Firebase call with a fixed claims dict — no live
Firebase access needed.

## Related

- [`background-tasks.md`](background-tasks.md) — how `user.id` flows from
  the request into background tasks.
- [`realtime.md`](realtime.md) — how `user_id` appears on each
  `tasks/{task_id}` document so Clio can filter to the current user.
