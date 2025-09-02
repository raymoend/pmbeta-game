# Parallel Kingdom Overhaul Plan

This document defines the end-to-end plan for revamping the game to a Parallel Kingdom-inspired experience, including phases, acceptance criteria, code-level changes, test strategy, migrations/rollout, risks and mitigations, and a timeline estimate.

Status snapshot
- Done/in-progress
  - Phase 0.2: Channels routing fix, legacy removal (archived consumers/models).
  - Phase 0.3: Celery app and beat: tasks for flag income, upkeep, NPC pulse; schedules wired.
  - Phase 1.1: Movement containment to claims/adjacency (ensure_in_territory).
  - Phase 1.2: Stamina regen on ping; stamina costs for movement; groundwork to extend to actions.
  - Phase 1.3: Flag economics tick (accrual/upkeep) + collection (WS action).
  - Phase 1.4: NPC density maintained per-flag with pulse task + respawns.
  - Phase 1.5: Jump to flag mechanic (+cooldown + cost; backend wired).
- Not started or partially complete
  - Phase 2.x: Combat pacing overhaul/polish, logs/UI.
  - Phase 3.x: Social systems MVP/polish.
  - Phase 4.x: Hardening + anti-cheat.
  - Phase 5.x: Ops + Compose + processes.
  - Phase 6: UI polish and mobile-first.
  - Phase 7: Tests and quality gates expansion.
  - Phase 8: Performance profiling.
  - Phase 9: Optional Godot 4 stub client.

Phases and scope
- Phase 0: Baseline, branching, environment alignment
  - 0.1 Dependencies/settings consolidation
  - 0.2 Channels routing fix and legacy removal
  - 0.3 Celery app, tasks, beat schedules
- Phase 1: Territory, movement & stamina
  - 1.1 Movement containment to claims and adjacency
  - 1.2 Stamina integration across actions (move/harvest/combat)
  - 1.3 Flag economics tick + collection
  - 1.4 NPC density inside claims
  - 1.5 Jump to flag travel mechanic
- Phase 2: Combat overhaul
  - 2.0 Near real-time pacing loop server-side
  - 2.1 Combat stamina + defeat flow polish, downed/respawn UX
  - 2.2 Combat UI and concise log
- Phase 3: Social systems MVP
  - 3.0 Alliances (lightweight), local/global chat refinements, basic notifications
  - 3.1 Trading polish and notifications
- Phase 4: Hardening + anti-cheat
  - 4.0 Validation layers, rate limits, logging
  - 4.1 Event model and notifications unification
- Phase 5: Ops & DevX
  - 5.0 Docker Compose for web + worker + beat + redis + db
  - 5.1 Data reset and seeding
  - 5.2 README/docs overhaul
- Phase 6: UI polish and mobile-first responsiveness
- Phase 7: Tests and quality gates
- Phase 8: Performance profiling and tuning
- Phase 9: Optional Godot 4 stub client planning

Acceptance criteria per phase
- Phase 0.1
  - Single source of truth for settings; Celery optional in settings without import errors.
- Phase 0.2
  - ASGI routes use RPGGameConsumer; legacy modules raise ImportError; docs/legacy created.
- Phase 0.3
  - Celery worker and beat start cleanly; beat schedules configured; no missing task import.
- Phase 1.1
  - Movement blocked outside owned + adjacent claim circles; server returns clear errors; tests cover adjacency.
- Phase 1.2
  - Movement, harvest, and combat deduct stamina using shared service; regen on ping; exhausted state blocks actions; tests validate thresholds.
- Phase 1.3
  - income_per_hour accrues per minute; upkeep applied daily; uncollected_balance collectible by owner; HUD updates post-collection.
- Phase 1.4
  - Each owned claim maintains MIN_FLAG_NPCS alive NPCs; respawns occur at respawn_at; pulse task idempotent; API lists flag NPCs.
- Phase 1.5
  - Jump-to-flag enforces cooldown and gold cost; private flags restrict jumps; WS action returns seconds_remaining on cooldown.
- Phase 2.0
  - PvE loop ticks server-side at session interval; client displays concise log updates; victory/defeat events refresh HUD and drop rewards.
- Phase 2.1
  - Downed/respawn timings honored; UI overlay shown; re-entry blocked until respawn_available_at.
- Phase 2.2
  - Combat UI minimal, mobile-friendly; log limited to recent N lines; accessible feedback for hits/misses.
- Phase 3.0
  - Global/local chat tags; alliance creation and membership minimal; basic notification push to HUD.
- Phase 3.1
  - Trading flow robust; notifications on offers/accept; beware dup/ghost trades.
- Phase 4.0
  - Server validates ranges, costs, and ownership for all actions; rate limiting on WS actions; audit logs for critical econ/combat events.
- Phase 4.1
  - Event model consolidates notifications; consistent client payload schema for HUD and toasts.
- Phase 5.0
  - docker-compose up starts web, worker, beat, redis, db; healthcheck passes; dev convenience scripts.
- Phase 5.1
  - One-shot seed command; repeatable data reset for demos/tests.
- Phase 5.2
  - README covers install, run web+worker+beat, WS actions, Celery ops; doc site outlines design and APIs.
- Phase 6
  - Core screens responsive under 360px; controls touch-friendly; no horizontal scroll.
- Phase 7
  - CI runs unit + WS + integration tests; coverage threshold (e.g., 70%+) for core modules.
- Phase 8
  - P95 WS handler latencies acceptable (<100ms server-time for most actions); DB queries reduced with select_related/prefetch;
- Phase 9
  - Godot 4 stub client connects, renders map, basic movement + chat; build scripts documented.

Code-level changes checklist (cumulative)
- Models
  - Character: last_jump_at (done), derived stats clamp, gold BigInteger (done), downed/respawn fields (done).
  - TerritoryFlag: hex_q/hex_r indexed + unique_together (done); econ fields (done).
  - FlagLedger for auditable econ (done).
- Services
  - movement.ensure_in_territory (done), stamina cost helpers (done), travel.jump_to_flag (done), flags.collect_revenue (done), territory.ensure_flag_monsters (done).
- Consumers
  - consumers_rpg: jump_to_flag (done), collect_flag_revenue (done), character_update group handler + HUD snapshot (done), start/stop combat loop (done), ping->regen (done).
- Tasks (Celery)
  - npc_pulse_task (ensure min NPCs, respawns) (done)
  - accrue_flag_income (done)
  - deduct_flag_upkeep (done)
- Settings
  - CELERY_* config + optional schedules (done), GAME_SETTINGS and PK_SETTINGS aligned (done).
- Frontend
  - HUD listens to character_update and updates gold/stats (present); add Flags panel actions (jump, collect) later.
- Docs
  - README updated with Celery worker/beat and WS actions (done);
  - This plan document (done).

Testing plan details
- Unit tests
  - Movement gating: ensure_in_territory across edge and adjacency cases.
  - Stamina: movement_stamina_cost; consume/regenerate; action blocks on exhausted.
  - Econ: accrue_flag_income minute math; daily upkeep; ledger entries, collect_revenue ownership checks.
  - Territory NPCs: ensure_flag_monsters spawns inside radius; respawn schedules.
  - Travel: jump_to_flag cost, cooldown math, privacy constraints.
- WebSocket tests (channels testing)
  - Connect, ping->regen updates; player_movement within territory; jump_to_flag request/response, character_update pushed; collect_flag_revenue request/response.
  - PvE loop tick: start_combat, receive combat updates until victory/defeat.
- Integration tests
  - Celery: set CELERY_TASK_ALWAYS_EAGER=true; run npc_pulse_task/accrue/deduct; verify DB changes consistent and idempotent.
  - End-to-end: place_flag -> accrue -> collect -> gold increases; npc density maintained after pulse.
- Property-based/edge tests
  - Random movement sequences near borders; econ accrual under delayed beats; respawn timings jitter.

Migration and rollout plan
- Branching
  - Continue on pk-territory-overhaul; PRs per phase.
- Database migrations
  - Ensure migrations for Character.last_jump_at, TerritoryFlag hex_q/hex_r + unique_together are applied (already generated/applied).
  - Backfill strategy: allow existing flags with null hex columns; compute later via management command if needed.
- Deploy sequence
  1) Apply migrations.
  2) Ensure Redis available and CELERY_* configured.
  3) Start Celery worker then Celery beat.
  4) Roll out web (ASGI). Validate health, WebSocket, and beats.
- Feature flags and fallbacks
  - Keep legacy endpoints disabled to avoid conflict; can re-enable p2k if needed behind a debug flag.
- Monitoring/observability
  - Add logs around tasks (already present); optional: Sentry or basic logging to file.
- Backups
  - Perform DB backup pre-deploy in production. Validate rollback strategy.

Risk register and mitigations
- Concurrency/race conditions on econ collection
  - Mitigation: select_for_update on flag; ledger entries; atomic transactions.
- Task schedule drift / duplicate execution (multi-beat)
  - Mitigation: Single-beat deployment; idempotent tasks; store last tick time; use DB locks if scaling beats.
- NPC over-spawn in dense regions
  - Mitigation: cap per-flag and global counts; throttle in pulse task; monitor spawn rates.
- Movement exploits via client
  - Mitigation: server-side ensure_in_territory; enforce interaction ranges; rate limit WS movement frequency.
- Combat desync
  - Mitigation: authoritative server loop; ignore client timestamps; small fixed tick intervals with throttling.
- Cost/cooldown bypass attempts
  - Mitigation: validate server-side on every action; centralize cost checks in services.
- Performance bottlenecks
  - Mitigation: indexes on hot fields (lat/lon, hex_q/r); select_related; clamp broadcast group sizes.
- Redis/channel outages
  - Mitigation: fallback to in-memory in dev; health checks; reconnect logic on client.

Timeline estimate (business days)
- Phase 0.1–0.3: 2–3 days (complete)
- Phase 1.1–1.5: 4–6 days (back-end core complete; UI polish 1–2 days remains)
- Phase 2.0–2.2: 5–8 days
- Phase 3.0–3.1: 3–5 days
- Phase 4.0–4.1: 3–5 days
- Phase 5.0–5.2: 3–4 days
- Phase 6: 3–5 days
- Phase 7: 3–5 days (parallelizable)
- Phase 8: 3–4 days (after load testing)
- Phase 9: 2–3 days (planning + stub)

Total: Approximately 30–44 business days depending on scope of UI polish and test coverage targets. Some phases can overlap (e.g., tests while implementing features; UI alongside back-end stabilization).

