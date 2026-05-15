# Architecture Overview

## System Design

The LINE Translation Bot follows a simple webhook-driven architecture with three main components:

### 1. LINE Messaging API (Input/Output)
- Receives messages via webhook POST requests
- Sends private DMs to the bot owner
- Posts translated messages to the target group

### 2. Railway Server (Processing)
- Flask web server receives webhook events
- Validates LINE webhook signatures
- Routes messages based on source (group vs private)
- Manages translation logic and language detection

### 3. Claude Haiku API (AI Engine)
- Language detection (English vs non-English)
- Thai → English translation
- English → Thai translation (natural, casual tone)

---

## Message Flow

### Incoming Group Message
```
LINE Group → Webhook → Flask → Language Check → Claude Haiku → Private DM to Owner
```

### Owner Reply to Group
```
Owner Private DM → Webhook → Flask → Claude Haiku → LINE Group Post
```

### Owner Private Translation
```
Owner Private DM (Thai) → Webhook → Flask → Claude Haiku → Owner Private DM (English)
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `CHANNEL_ACCESS_TOKEN` | ✅ | LINE bot access token for API calls |
| `CHANNEL_SECRET` | ✅ | Used to verify webhook signature |
| `ANTHROPIC_API_KEY` | ✅ | Claude Haiku API authentication |

---

## Translation Prompts

### Thai → English
Simple system prompt instructing Claude to translate only, no explanations.

### English → Thai
Detailed prompt enforcing:
- ผม as first-person pronoun (male speaker)
- ครับ politeness particle at end
- Casual conversational tone
- Meaning-based (not literal) translation

---

## Error Handling

- 3 retry attempts on failed API calls
- Graceful fallback to "Unknown User" if profile fetch fails
- Error message sent to owner if translation completely fails
- Webhook returns 200 OK to LINE even on internal errors (prevents LINE retries)
