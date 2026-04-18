# Bet Slip Detection — Design Spec
_2026-04-18_

## Problem

Two failure modes in the current bet slip detection:

1. **Auto-detection fires for any known player** — any group member sending an image can trigger confirmation, even if they're not the designated placer. Intended for delegation, but too broad: a non-placer sending a Bet365 browse screenshot triggered a false confirmation (week 10).

2. **LLM guard is too loose** — the guard accepts any image where the LLM finds legs, total_odds, or stake. A "Add to Your Bet Slip" browse screenshot contains enough odds-like data to pass.

## Design

### Split detection into two paths

**Automatic (placer only)**
When an image arrives and the sender IS the designated placer, run the existing LLM guard. If the LLM extracts slip data, confirm automatically. Unchanged behaviour for the placer; completely silent for everyone else.

**Explicit command (anyone → `!slip`)**
Any known group member can reply to an image with `!slip`. The bot fetches the quoted image, runs LLM extraction best-effort, and confirms regardless of LLM output (human confirmed it). This is the delegation path.

---

## Changes

### 1. `app.py` — restrict auto-detection to designated placer

In the `has_media` block (currently line 133), check whether the sender is the designated placer before calling `_handle_placer_bet_confirmation`. If not, skip silently.

```python
# Before (fires for any known player):
if not reply and has_media:
    reply = _handle_placer_bet_confirmation(...)

# After (fires only for designated placer):
if not reply and has_media:
    next_placer = get_next_placer()
    sender_player = lookup_player(sender_phone=sender_phone, sender_name=sender)
    if next_placer and sender_player and sender_player["id"] == next_placer["id"]:
        reply = _handle_placer_bet_confirmation(...)
```

### 2. `bridge/index.js` — pass quoted message ID + cache quoted media

When processing any message that is a reply, resolve the quoted message and:
- Add `quoted_message_id` to the webhook payload
- If the quoted message has media, cache it in `recentMessages` under its own ID

```javascript
if (message.hasQuotedMsg) {
    const quoted = await message.getQuotedMessage();
    payload.quoted_message_id = quoted.id._serialized;
    if (quoted.hasMedia) {
        recentMessages.set(quoted.id._serialized, quoted);
    }
}
```

This ensures the image is fetchable via the existing `/media` endpoint even if the original message was evicted from the cache.

### 3. `app.py` — pass `quoted_message_id` through to command dispatch

Add `quoted_message_id` from the webhook payload to the `parsed` dict before `handle_command` is called.

### 4. `app.py` — `_cmd_slip` command handler

New handler for `!slip`. Guards:
- Week exists and is open/closed (picks collected)
- All picks are in
- No placer already recorded (`week.placer_id` is null)
- Sender is a known player
- `quoted_message_id` present in the parsed dict

On success:
1. Fetch image via `/media` using `quoted_message_id`
2. Run `llm_client.read_bet_slip()` for extraction (best-effort — does not gate confirmation)
3. `advance_rotation`, `record_bet_slip`, `match_legs_to_picks`, `update_confirmed_odds`
4. Return `butler.bet_slip_received(next_placer)`

On failure (missing quoted image, week not ready, etc.): return a short user-visible error string.

---

## Error messages

| Condition | Reply |
|---|---|
| No quoted message | "Reply to the bet slip image with !slip" |
| Quoted message has no media | "The message you replied to doesn't contain an image" |
| Picks not all in | "Still waiting for picks before recording the slip" |
| Placer already recorded | "Bet slip already confirmed for this week" |
| Sender not recognised | _(silent — consistent with other command guards)_ |

---

## Testing

- Auto-detection: non-placer sends image → silent. Placer sends non-slip image → silent (LLM guard). Placer sends real slip → confirmed.
- `!slip`: any known player replies to image → confirmed. No quoted message → error. Already confirmed → error. Picks not in → error.
- Existing text-based confirmation (`!placed`, "bet placed" keywords) unchanged.
