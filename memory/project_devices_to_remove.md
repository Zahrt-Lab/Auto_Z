---
name: project-devices-to-remove
description: Device files marked for future removal — skip type hint work on these
metadata:
  type: project
---

The following device implementations are planned for removal from the codebase. Do not add type hints or invest refactoring effort in them.

- `devices/industry_components/peristaltic_pumps/regio_icc_isametic_pumps/regio_icc_isametic_pumps.py` — Regio ICC Isametic Pump, never fully tested/validated
- `devices/industry_components/liquid_handlers/ender3_liquid_handler/ender3_liquid_handler.py` — Ender3 liquid handler, being removed

**Why:** User confirmed these during a type-hint pass (2026-06-01) — both are being phased out of the lab automation platform.

**How to apply:** When doing any codebase-wide work (type hints, refactoring, testing), skip these two files entirely.
