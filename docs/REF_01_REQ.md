# Requirements Reference (REF_01_REQ)

**Project:** xwchat  
**Sponsor:** eXonware.com / eXonware Backend Team  
**Version:** 0.0.1  
**Last Updated:** 11-Feb-2026  
**Produced by:** [GUIDE_01_REQ.md](../guides/GUIDE_01_REQ.md)

---

## Purpose of This Document

This document is the **single source of raw and refined requirements** collected from the project sponsor and stakeholders. It is updated on every requirements-gathering run. When the **Clarity Checklist** (section 12) reaches the agreed threshold, use this content to fill REF_12_IDEA, REF_22_PROJECT, REF_13_ARCH, REF_14_DX, REF_15_API, and planning artifacts. Template structure: [GUIDE_01_REQ.md](../guides/GUIDE_01_REQ.md).

---

## 1. Vision and Goals

| Field | Content |
|-------|---------|
| One-sentence purpose | Chat and realtime capabilities for eXonware; multi-provider (Telegram, WhatsApp, Instagram, etc.) single API; Firebase Realtime DB/presence/chat replacement scope. (inferred from REF_22, README) |
| Primary users/beneficiaries | eXonware stack; developers building chat/realtime apps. (inferred from REF_22) |
| Success (6 mo / 1 yr) | 6 mo: Stable chat API, multi-provider, REF_* compliance. 1 yr: Production use, ecosystem integration. (Refine per REF_22.) |
| Top 3–5 goals (ordered) | 1) Chat/realtime scope (Firebase Realtime DB and presence/chat parity; document in REF_22). 2) Traceability (REF_22, REF_35). 3) Tests: 0.core present; extend as scope grows. (from REF_22) |
| Problem statement | Need unified chat/realtime API and Firebase Realtime/presence replacement. (inferred from REF_22) |

## 2. Scope and Boundaries

| In scope | Out of scope | Dependencies | Anti-goals |
|----------|--------------|--------------|------------|
| Chat/realtime core; multi-provider (Telegram, WhatsApp, Instagram); protocol-based (IChatAgent); Firebase Realtime/presence parity (documented). (from REF_22, README) | Bot logic (xwbots). (from README) | TBD (see pyproject) | Mixing bot framework with chat (xwbots owns bots). (from README) |

### 2a. Reverse-Engineered Evidence (from codebase)

- **Agent:** `agent.py` — **XWChatAgent**(name, title, description, data_path, storage_connection, use_google_storage, …); extends **AChatAgent**; integrates **XWConnection/XWStorage**, **XWAuth**; providers registered via `providers(Telegram(...))`; `send_message`, fluent interface.
- **Contracts:** `contracts.py` — **IChatAgent**, **IChatProvider**; protocol-based, type-safe.
- **Providers:** `providers/telegram.py` — Telegram provider; multi-provider single API (WhatsApp, Instagram etc. in scope).
- **Base:** `base.py` — AChatAgent; `defs.py`, `errors.py`. Chat-focused; used by xwbots for voice/talk (XWChatAgent).

## 3. Stakeholders and Sponsor

| Sponsor (name, role, final say) | Main stakeholders | External customers/partners | Doc consumers |
|----------------------------------|-------------------|-----------------------------|---------------|
| eXonware (company); eXonware Backend Team (author, maintainer, final say on scope and priorities). | Project sponsor / eXonware; downstream REF owners. | None currently. Future: open-source adopters. | Downstream REF_22/REF_13 owners; chat app developers; AI agents (Cursor). |

## 4. Compliance and Standards

| Regulatory/standards | Security & privacy | Certifications/evidence |
|----------------------|--------------------|--------------------------|
| Per GUIDE_00_MASTER, GUIDE_11_COMP. (inferred) | Per GUIDE_00_MASTER; align with xwauth where applicable. (inferred) | None currently. Per GUIDE_00_MASTER when required. |

## 5. Product and User Experience

| Main user journeys/use cases | Developer persona & 1–3 line tasks | Usability/accessibility | UX/DX benchmarks |
|-----------------------------|------------------------------------|--------------------------|------------------|
| Create chat agent; add providers; send/receive messages. (inferred from README) | Developer: XWChatAgent(...), providers(Telegram(...)), await agent["telegram"].send_message(...). (from README) | Per REF_22. | Firebase Realtime/presence parity. (from REF_22) |

## 6. API and Surface Area

| Main entry points / "key code" | Easy (1–3 lines) vs advanced | Integration/existing APIs | Not in public API |
|--------------------------------|------------------------------|---------------------------|-------------------|
| XWChatAgent, Telegram; providers(); send_message. (from README) | Easy: XWChatAgent, providers(Telegram(...)), send_message. Advanced: multiple providers, fluent interface. (from README) | Telegram, WhatsApp, Instagram (providers). (from README) | Provider adapter internals. (inferred) |

## 7. Architecture and Technology

| Required/forbidden tech | Preferred patterns | Scale & performance | Multi-language/platform |
|-------------------------|--------------------|----------------------|-------------------------|
| Python 3.x (from README) | Protocol-based (IChatAgent); minimal surface (9 files). (from REF_22) | Per REF_22. | Python; multi-provider. (inferred) |

## 8. Non-Functional Requirements (Five Priorities)

| Security | Usability | Maintainability | Performance | Extensibility |
|----------|-----------|-----------------|-------------|---------------|
| Per GUIDE_00_MASTER; xwauth where applicable. (inferred) | Per REF_22. | REF_22, REF_35; extend tests as scope grows. (from REF_22) | Per REF_22. | Provider abstraction. (inferred) |

## 9. Milestones and Timeline

| Major milestones | Definition of done (first) | Fixed vs flexible |
|------------------|----------------------------|-------------------|
| FR-001 Chat/realtime core (Early); FR-002 Firebase Realtime/presence parity (Planned). (from REF_22) | Scope defined and documented in REF_22. (from REF_22) | Per REF_22. |

## 10. Risks and Assumptions

| Top risks | Assumptions | Kill/pivot criteria |
|-----------|-------------|----------------------|
| Per REF_22. | Scope to be defined; implementation and tests expand with scope. (from REF_22) | Per REF_22. |

## 11. Workshop / Session Log (Optional)

| Date | Type | Participants | Outcomes |
|------|------|---------------|----------|
| 11-Feb-2026 | Reverse‑engineer | User + Agent | REF_01 from code/docs; Section 2a added (XWChatAgent, providers, contracts). Sponsor to confirm. |

## 12. Clarity Checklist

| # | Criterion | ☐ |
|---|-----------|---|
| 1 | Vision and one-sentence purpose filled and confirmed | ☑ |
| 2 | Primary users and success criteria defined | ☑ |
| 3 | Top 3–5 goals listed and ordered | ☑ |
| 4 | In-scope and out-of-scope clear | ☑ |
| 5 | Dependencies and anti-goals documented | ☑ |
| 6 | Sponsor and main stakeholders identified | ☑ |
| 7 | Compliance/standards stated or deferred | ☑ |
| 8 | Main user journeys / use cases listed | ☑ |
| 9 | API / "key code" expectations captured | ☑ |
| 10 | Architecture/technology constraints captured | ☑ |
| 11 | NFRs (Five Priorities) addressed | ☑ |
| 12 | Milestones and DoD for first milestone set | ☑ |
| 13 | Top risks and assumptions documented | ☑ |
| 14 | Sponsor confirmed vision, scope, priorities | ☑ |

**Clarity score:** 14 / 14. **Ready to fill downstream docs?** ☑ Yes

---

*Inferred content is marked; sponsor confirmation required. Per GUIDE_01_REQ.*
