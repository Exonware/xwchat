# Architecture Reference — exonware-xwchat

**Library:** exonware-xwchat  
**Producing guide:** GUIDE_13_ARCH  
**Last Updated:** 07-Feb-2026

---

## Overview

xwchat provides **chat and realtime** capabilities for the eXonware ecosystem. Architecture follows eXonware contracts/base/facade patterns; scope is early—Firebase Realtime DB / presence / chat parity to be documented in REF_22 and implemented incrementally.

**Design Philosophy:** Provider-based backends; minimal surface until scope is defined; extend with realtime/presence/chat semantics.

---

## High-Level Structure

```
xwchat/
+-- contracts.py      # Interfaces (IClass)
+-- base.py           # Abstract bases (AClass)
+-- errors.py         # Exceptions
+-- defs.py           # Constants, enums
+-- version.py
+-- agent.py          # Chat/realtime agent entry
+-- providers/        # Backend providers
    +-- __init__.py
    +-- telegram.py   # Telegram provider
```

---

## Boundaries

- **Public API:** Agent and provider interfaces; chat/realtime operations (scope TBD in REF_22).
- **Providers:** Each provider (e.g. Telegram) implements contracts; facade or agent routes to active provider.
- **Realtime/presence:** To be designed when Firebase parity scope is fixed; likely delegation to xwstorage or dedicated realtime layer.

---

## Design Patterns

- **Strategy:** Provider selection (Telegram, future backends).
- **Facade:** Single entry (agent) over providers.
- **Contract/base:** Interfaces in `contracts.py`, abstract bases in `base.py`.

---

## Delegation

- **xwauth (future):** Authentication for chat/realtime when scope includes secured channels.
- **xwstorage (future):** Persistence or realtime sync when scope is defined.
- **Firebase parity:** Document in REF_22; implement once scope is agreed.

---

## Layering

1. **Contracts:** Provider and agent interfaces.
2. **Base:** Abstract provider/agent logic.
3. **Agent / Facade:** Public entry; routes to providers.
4. **Providers:** Per-backend implementations (e.g. Telegram).

---

## Scope and Next Steps

- **Current:** Minimal surface (9 Python files); 0.core tests; REF_22 defines vision.
- **Next:** Define Firebase Realtime/presence/chat scope in REF_22; add REF_12_IDEA entries; expand to 4-layer tests (GUIDE_51_TEST); implement realtime/presence when scope is clear.

---

## Traceability

- **Requirements:** [REF_22_PROJECT.md](REF_22_PROJECT.md)
- **Ideas:** [REF_12_IDEA.md](REF_12_IDEA.md)
- **API:** [REF_15_API.md](REF_15_API.md)

---

*See GUIDE_13_ARCH.md for architecture process.*
