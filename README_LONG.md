# xwchat (long version)

**Multi-network chat agent toolkit** for the eXonware stack.

*Short overview: [README.md](README.md).*

---

**Company:** eXonware.com  
**Author:** eXonware Backend Team  
**Email:** connect@exonware.com

---

## Overview

xwchat gives you one agent object that can attach Telegram, WhatsApp, Instagram, and other providers so you send and receive messages through the same API. It focuses on **chat** behavior; richer bot frameworks live in **xwbots**.

## Features

- **Multi-provider** - Several networks at once
- **Single API** - One surface for send/receive patterns
- **Typed** - Protocols plus type hints
- **Extensible** - Add providers by implementing the interfaces

---

## Installation

```bash
pip install exonware-xwchat
```

For Telegram and other bundled extras:

```bash
pip install exonware-xwchat[full]
```

---

## Quick start

### Basic usage

```python
from exonware.xwchat import XWChatAgent, Telegram

# Create a chat agent
chat_agent = XWChatAgent(
    name="MyAgent",
    title="My Chat Agent",
    description="A helpful chat agent"
)

# Add Telegram provider
chat_agent.providers(Telegram("YOUR_TELEGRAM_API_TOKEN"))

# Send a message
await chat_agent["telegram"].send_message("user_id", "Hi there!")
```

### Fluent interface

```python
chat_agent = (
    XWChatAgent("MyAgent", "My Chat Agent")
    .providers(Telegram("API_TOKEN"))
)

# Access provider
telegram = chat_agent["telegram"]
await telegram.send_message("user_id", "Hello!")
```

### Multiple providers

```python
chat_agent = XWChatAgent("MyAgent", "My Chat Agent")
chat_agent.providers(
    Telegram("TELEGRAM_TOKEN"),
    # WhatsApp("WHATSAPP_TOKEN"),  # Coming soon
    # Instagram("INSTAGRAM_TOKEN"),  # Coming soon
)

# Use specific provider
await chat_agent["telegram"].send_message("user_id", "Hi!")
```

---

## Architecture

### Interfaces

- **IChatAgent** - Agent contract
- **IChatProvider** - Provider contract

Providers implement `IChatProvider`; agents hold many providers and expose them by name (`chat_agent["telegram"]`, etc.).

### Scope

- **xwchat** - Conversations: messaging, presence, sessions
- **xwbots** - Commands, webhooks, heavier automation

---

## Documentation

- [docs/](docs/) - Project docs when published
- [README.md](README.md) - Quick start

---

## Where it fits

**Ecosystem glue**

xwchat standardizes chat access across major consumer networks so services built on eXonware do not fork one adapter per platform.

---

## License

MIT License - see [LICENSE](LICENSE).

---

**Company:** eXonware.com  
**Author:** eXonware Backend Team  
**Email:** connect@exonware.com
