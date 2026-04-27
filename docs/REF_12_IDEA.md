# Idea Reference — exonware-xwchat

**Company:** eXonware.com  
**Producing guide:** GUIDE_12_IDEA  
**Last Updated:** 26-Feb-2026

---

## Overview

xwchat provides **chat and realtime** capabilities for the eXonware ecosystem, with product direction toward Firebase Realtime DB / presence / chat replacement. This document captures ideas and scope; approved ideas flow to [REF_22_PROJECT.md](REF_22_PROJECT.md) and [REF_13_ARCH.md](REF_13_ARCH.md). It also lists **xwchat** package requirements and **chat bot** requirements for server/client/bot use, **generalized for multiple providers** (Telegram, Discord, WhatsApp, etc.). Capabilities and provider-specific notes are documented so that **if something is missing or differs for a provider, it is stated**; non-chat features (e.g. full server admin, voice, analytics) are omitted or optional.

### Alignment with eXonware 5 Priorities

- **Security:** Auth and input validation when scope is defined.
- **Usability:** Clear API and errors once features are implemented.
- **Maintainability:** Contracts/base/facade, extend tests as scope grows.
- **Performance:** Realtime and presence semantics to be defined.
- **Extensibility:** Provider-based (e.g. Telegram); pluggable backends.

**Related Documents:**
- [REF_22_PROJECT.md](REF_22_PROJECT.md) — Requirements
- [REF_13_ARCH.md](REF_13_ARCH.md) — Architecture
- [REF_35_REVIEW.md](REF_35_REVIEW.md) — Review summary

---

## xwchat Requirements & Chat Bot Requirements

### 1. xwchat Requirements

#### 1.1 Core Dependencies

| Requirement | Source | Notes |
|-------------|--------|--------|
| Python ≥ 3.12 | pyproject.toml | Minimum supported version |
| exonware-xwsystem | requirements.txt, pyproject.toml | Core eXonware dependency |
| pip | pyproject.toml | Package installer |

#### 1.2 Optional Dependencies (Provider / full stack)

Used for provider implementations (e.g. parrot_bot) and full xwchat features:

| Package | Version | Purpose |
|---------|---------|---------|
| python-telegram-bot | ≥ 20.0 | Telegram provider |
| discord.py | ≥ 2.0 | Discord provider (brings aiohttp) |
| aiohttp | ≥ 3.8 | Async HTTP (e.g. webhook server, used by discord.py) |

From `pyproject.toml` optional `full` extra:

| Package | Purpose |
|---------|---------|
| exonware-xwsystem[full] | Full xwsystem features |
| beautifulsoup4 | ≥ 4.9.0 — parsing where needed |
| exonware-xwstorage | Storage integration |
| exonware-xwauth | Auth integration |
| google-cloud-storage | ≥ 2.10.0 |
| google-auth | ≥ 2.23.0 |

#### 1.3 Optional Lazy / Dev

| Extra | Packages |
|-------|----------|
| lazy | exonware-xwlazy, exonware-xwsystem[lazy] |
| Dev/Test | pytest ≥ 7, pytest-cov ≥ 4, pytest-asyncio ≥ 0.20 |
| Code quality | black ≥ 22, isort ≥ 5.10, flake8 ≥ 4 |
| Type checking | mypy ≥ 0.950 |

#### 1.4 Compatibility (from requirements.txt)

- **Platforms:** Windows, Linux, macOS  
- **Python:** 3.12, 3.13 tested  
- **Cloud IDEs:** Replit, GitHub Codespaces, GitPod, Google Colab, Jupyter

---

### 2. Chat Bot Requirements (General)

Applicable to **any** chat bot (server/client/bot) across providers. Each capability is required for basic chat unless marked optional; if a provider does not support a capability or it differs, that is stated in [§3.2 Provider-specific notes](#32-provider-specific-notes).

| Capability | Required for basic chat | Notes |
|------------|-------------------------|--------|
| **Identity & auth** | Yes | Bot/user identity; token or API key; secure storage. |
| **Receive messages** | Yes | Via gateway, webhook, or long poll (provider-dependent). |
| **Send messages** | Yes | Text and, where supported, rich content (embeds, formatting). |
| **Read message history** | Yes | Read recent or listed messages for context/replies. |
| **Attachments** | Yes (for file/link sharing) | Send/receive files or links within platform limits. |
| **Threads** | Optional | Create/send in threads where the platform supports them. |
| **Reactions** | Optional | Add/read reactions for chat UX. |
| **Commands / slash** | Optional | Bot commands or slash commands if the platform has them. |
| **Scopes / permissions** | Yes | Request only what is needed for chat; model varies by provider. |
| **Delivery model** | — | Webhook, long poll, or gateway; see provider notes. |

**Out of scope for this doc (chat-only focus):** Full server/guild admin, voice/video, analytics, Rich Presence. Omit unless the bot needs them.

---

### 3. Multi-Provider Chat Capabilities

#### 3.1 Capability matrix (chat-only)

| Capability | Telegram | Discord | WhatsApp | Other |
|------------|----------|---------|----------|--------|
| Identity & auth | ✅ Token | ✅ Token + OAuth2 | ✅ Token / API | Per provider |
| Receive messages | ✅ Long poll / webhook | ✅ Gateway / webhook | ✅ Webhook | Stated when added |
| Send messages | ✅ | ✅ | ✅ | Stated when added |
| Read history | ✅ | ✅ (with permission) | ⚠️ Limited | Stated when added |
| Attachments | ✅ | ✅ (with permission) | ✅ | Stated when added |
| Threads | ✅ Topics (forums) | ✅ Threads | ❌ Not applicable | Stated when added |
| Reactions | ✅ | ✅ (with permission) | ✅ | Stated when added |
| Commands / slash | ✅ Bot commands | ✅ Slash commands | — | Stated when added |
| Permissions / scopes | ✅ Bot scope | ✅ Intents + permissions | ✅ App permissions | Per provider |

**Legend:** ✅ Supported for chat use; ⚠️ Partial or limited; ❌ Not applicable or not offered; — To be documented when provider is added.

**If something is missing or differs for a provider, it is stated in §3.2.**

#### 3.2 Provider-specific notes

*For each provider: what is supported for chat, what is missing, and what is different. Gaps are explicit.*

**Telegram**

- **Auth:** Bot token from BotFather; no OAuth2 for bot add.
- **Delivery:** Long poll (default) or webhook; no gateway.
- **History:** Full read history via API; no special intents.
- **Threads:** Forum topics (thread-like); not all chats have them.
- **Reactions:** Supported.
- **Missing / different:** No “intents” or guild permissions; scope is bot-level. No slash commands (use bot commands/inline). Voice/video are separate APIs; out of scope for chat-only.

**Discord**

- **Auth:** Bot token; OAuth2 controls who can add the bot (public vs only you; optional Code Grant for multiple scopes).
- **Delivery:** Gateway (WebSocket) and/or webhook; choose per use case.
- **Intents (privileged):** **Message Content Intent** required to receive message content. Presence Intent and Server Members Intent optional (for presence/member list); at 100+ servers these may need verification.
- **Permissions (text/chat):** Minimum: View Channels, Send Messages, Read Message History, Embed Links, Attach Files. Recommended: Add Reactions, Create/Send in Threads, Manage Messages, Pin Messages, Manage Threads, Mention Everyone, Use External Emojis/Stickers, Use Slash Commands, Bypass Slowmode, Send Voice Messages. Omit admin, audit log, server/role/channel management, and voice (Connect/Speak/Video, etc.) for chat-only bots.
- **Assets (reference):** Icon 1024×1024; banner 680×240 (PNG/GIF/JPG/WEBP, max 10 MB).
- **Missing / different:** Threads and many permissions are guild/channel-specific. Webhooks: subscribe only to message-related events if using HTTP.

**WhatsApp**

- **Auth:** Token / API (e.g. Cloud API); setup differs from Telegram/Discord.
- **Delivery:** Webhook-based; no long poll or gateway in the same sense.
- **History:** Limited; typically last message and context, not full channel history like Discord.
- **Threads:** Not applicable (no server threads).
- **Reactions / commands:** Reactions supported; no slash commands; interaction model differs.
- **Missing / different:** No “guild” or “channels”; conversations and contacts. Permissions are app/phone-number level. Document exact scopes when implementing.

**Other providers (Slack, Instagram, custom, etc.)**

- **When a provider is added:** Add a row to the matrix (§3.1) and a subsection here. For each capability, state: supported, partial, missing, or not applicable. Do not leave gaps implicit.

---

### 4. Summary — Chat-Relevant vs Out of Scope (Multi-Provider)

| Area | Chat-relevant (all providers) | Out of scope (for this doc) |
|------|-------------------------------|-----------------------------|
| xwchat | Core + provider libs (Telegram, Discord, aiohttp, etc.) | Full optional stack (e.g. GCS) unless used by chat |
| Capabilities | Identity, receive/send, history, attachments, threads (if any), reactions, permissions | Full server/guild admin, voice/video, analytics, Rich Presence |
| Provider gaps | Documented in §3.2 per provider; **if something is missing or N/A, it is stated** | Assuming parity across providers without checking |

*When adding a new provider, update the capability matrix (§3.1) and add a §3.2 subsection; explicitly state what is supported, partial, missing, or not applicable.*

---

## Product Direction (from REF_22)

### 🔍 [IDEA-001] Firebase Realtime / presence / chat parity

**Status:** 🔍 Exploring  
**Date:** 07-Feb-2026

**Problem:** Ecosystem needs a replacement for Firebase Realtime DB and presence/chat features; scope must be defined before full implementation.

**Proposed Solution:** Define scope (realtime DB semantics, presence, chat) in REF_22; expand implementation and tests as scope is defined. Current surface: minimal (e.g. agent, providers such as Telegram).

**Next Steps:** Document Firebase parity in REF_22; expand FR-001/FR-002; add 4-layer tests per GUIDE_51_TEST.

---

### ✅ [IDEA-002] Provider-based chat backends

**Status:** ✅ Approved → In progress  
**Date:** 07-Feb-2026

**Problem:** Chat and realtime may integrate with multiple backends (Telegram, future Firebase-compatible, custom).

**Proposed Solution:** Provider abstraction (contracts); implementations (e.g. providers/telegram.py) behind facade.

**Outcome:** Minimal structure in place (agent, providers); to expand with scope.

---

## Idea Catalog

| ID       | Title                          | Status   | Links  |
|----------|--------------------------------|----------|--------|
| IDEA-001 | Firebase Realtime/presence/chat| Exploring| REF_22 |
| IDEA-002 | Provider-based chat backends  | Approved | Code   |

---

*See GUIDE_12_IDEA.md for idea process. Requirements: REF_22_PROJECT.md.*
