# xwchat

**One agent, many chat networks.** Telegram, WhatsApp, Instagram, and others behind one typed API. Chat UX lives here; heavy bot automation is aimed at xwbots. Docs in `docs/`.

*Details: [README_LONG.md](README_LONG.md).*

**Company:** eXonware.com · **Author:** eXonware Backend Team · **Email:** connect@exonware.com  

[![Status](https://img.shields.io/badge/status-alpha-orange.svg)](https://exonware.com)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

---

## 📦 Install

```bash
pip install exonware-xwchat
pip install exonware-xwchat[lazy]
pip install exonware-xwchat[full]
```

---

## 🚀 Quick start

```python
from exonware.xwchat import XWChatAgent, Telegram

chat_agent = XWChatAgent(name="MyAgent", title="My Chat Agent", description="A helpful chat agent")
chat_agent.providers(Telegram("YOUR_TELEGRAM_API_TOKEN"))
await chat_agent["telegram"].send_message("user_id", "Hi there!")
```

See [docs/](docs/) for the fluent API, multiple providers, and `REF_*` when present.

---

## ✨ What you get

| Area | What's in it |
|------|----------------|
| **Providers** | Telegram, WhatsApp, Instagram (and more); one API. |
| **Interface** | Protocol-based (`IChatAgent`); typed; easy to extend. |
| **Scope** | Chat flows; bot frameworks in xwbots. |

---

## 🌐 Ecosystem functional contributions

`xwchat` provides channel abstraction; sibling libraries handle automation logic, AI generation, persistence, and shared runtime behavior.
You can use `xwchat` standalone for multi-provider chat integration without the full XW stack.
Additional ecosystem modules are optional and most useful for enterprise and mission-critical chat platforms that need fully self-managed automation, identity, and data infrastructure.

| Supporting XW lib | What it provides to xwchat | Functional requirement it satisfies |
|------|----------------|----------------|
| **XWAI** | AI response generation and command interpretation integration for chat flows. | Intelligent conversational behavior across channels. |
| **XWBots / XWAction** | Bot-command and action execution orchestration on incoming chat events. | Structured automation and tool execution from chat interactions. |
| **XWStorage** | Persistent conversation state, session context, and message history backends. | Durable multi-session chat behavior and replayability. |
| **XWEntity** | Domain-aware identity/contact/user profile linkage in chat workflows. | Consistent user/domain mapping across channels and backend services. |
| **XWAuth** | AuthN/AuthZ boundaries for protected chat operations and agent actions. | Secure chat-triggered operations in multi-tenant environments. |
| **XWSystem** | Shared async/runtime/logging/config/security utilities. | Stable cross-provider operations and lower integration overhead. |

Competitive edge: one chat surface can participate in the full action/AI/domain stack instead of being a siloed messaging adapter.

---

## 📖 Docs and tests

- **Start:** [docs/INDEX.md](docs/INDEX.md) or [docs/](docs/).
- **Tests:** From repo root, follow the project's test layout.

---

## 📜 License and links

Apache-2.0 - see [LICENSE](LICENSE). **Homepage:** https://exonware.com · **Repository:** https://github.com/exonware/xwchat  


## ⏱️ Async Support

<!-- async-support:start -->
- xwchat includes asynchronous execution paths in production code.
- Source validation: 219 async def definitions and 295 await usages under src/.
- Use async APIs for I/O-heavy or concurrent workloads to improve throughput and responsiveness.
<!-- async-support:end -->
Version: 0.0.1.7 | Updated: 12-Apr-2026

*Built with ❤️ by eXonware.com - Revolutionizing Python Development Since 2025*
