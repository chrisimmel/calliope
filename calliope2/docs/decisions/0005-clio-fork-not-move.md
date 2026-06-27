# 0005 — Fork Clio, don't move it

Date: 2026-05-13
Status: Accepted

## Context

The original plan for Phase 7 said `git mv /clio/ → apps/web/clio/` and
repoint the API calls at `/v3`. On reflection, that would have replaced
the production Clio the moment we deployed the new app — and the v3
backend would have started serving users with **zero migrated stories**
until the Phase 9 data migration ran.

Worse, v1 and v3 Clio genuinely cannot share code:

| | v1 Clio | v3 Clio |
|---|---|---|
| Auth | Anonymous Firebase | Google sign-in (real `User` rows) |
| API | `/v1`, `/v2` (Piccolo) | `/v3` (SQLAlchemy) |
| Firestore | 3 collections | One `tasks/{task_id}` mailbox |
| User DB | Existing rows | Empty until Phase 9 migration |

An anonymous v1 session and a Google-signed-in v3 session are not the
same identity. A user who signs in to v3 sees nothing of their v1
content until claim/migration runs. Trying to bridge them in one frontend
adds dead weight without simplifying anything.

## Decision

`/clio/` stays exactly where it is. Phase 7 **forks** it (`cp -R`) into
`apps/web/clio/` and the v3 copy evolves freely against `/v3` and
Google sign-in. From the day the fork lands, the original `/clio/` is
**frozen** — only critical bug fixes touch it.

Cutover happens after Phase 9 data migration via a load-balancer or DNS
switch between the two Cloud Run services, not in-place inside one app.

## Consequences

**Wins:**
- v1 users see no disruption while v3 is built and tested.
- v3 doesn't carry v1 shims (sparrow_id, slug routing, anonymous auth
  fallbacks).
- The dead code from v1 doesn't haunt v3's diffs.
- Phase 9 can be run dry-run, then real, then verified, while the v1
  app keeps serving traffic. Cutover is just a config flip.

**Costs:**
- Two frontends in the repo for the cutover window. Acceptable: v1
  Clio is frozen, so the only maintenance cost is the occasional
  critical bug fix.
- Some legacy components from v1 Clio (frame seed media, swipe
  navigation, bookmarks UI) need to be re-built on top of the minimal
  v3 shell. This is iteration work, not blocking.

## Alternatives considered

- **`git mv` as originally planned.** The "swap users to an empty DB on
  deploy" problem makes this a non-starter.
- **Single Clio with a feature flag.** Would require both auth flows to
  coexist; the identity model is incompatible.
- **Maintain v1 Clio actively in parallel.** "Frozen except for
  critical fixes" is a softer commitment that captures the operational
  reality.

## Related

- [Phase 7 in the plan](../README.md) (linked at the top of the doc set)
- Commit `7c9c07f` (the fork)
