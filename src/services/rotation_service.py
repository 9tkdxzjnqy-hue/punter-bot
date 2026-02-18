from src.db import get_db
from src.services.player_service import get_all_players, get_player_by_id, get_rotation_order


def get_next_placer():
    """
    Determine who places the bet this week.

    Priority:
    1. First unprocessed entry in the penalty queue
    2. Next player in the standard rotation
    """
    conn = get_db()

    # Check penalty queue first
    penalty_entry = conn.execute(
        "SELECT * FROM rotation_queue WHERE processed = 0 ORDER BY position ASC LIMIT 1"
    ).fetchone()

    if penalty_entry:
        conn.close()
        return get_player_by_id(penalty_entry["player_id"])

    # Standard rotation — find who placed last and get the next person
    last_week = conn.execute(
        "SELECT w.placer_id FROM weeks w "
        "WHERE w.status = 'completed' AND w.placer_id IS NOT NULL "
        "ORDER BY w.id DESC LIMIT 1"
    ).fetchone()

    conn.close()

    players = get_rotation_order()  # uses ROTATION_ORDER config or rotation_position

    if not last_week or not last_week["placer_id"]:
        # No previous placer — start with first in rotation
        return players[0] if players else None

    # Find the next player after the last placer
    last_placer_id = last_week["placer_id"]
    for i, player in enumerate(players):
        if player["id"] == last_placer_id:
            return players[(i + 1) % len(players)]

    return players[0]


def add_to_penalty_queue(player_id, reason, week_id=None):
    """Add a player to the penalty rotation queue."""
    conn = get_db()

    # Get the next position
    max_pos = conn.execute(
        "SELECT COALESCE(MAX(position), 0) FROM rotation_queue WHERE processed = 0"
    ).fetchone()[0]

    conn.execute(
        "INSERT INTO rotation_queue (player_id, reason, position, week_added, processed) "
        "VALUES (?, ?, ?, ?, 0)",
        (player_id, reason, max_pos + 1, week_id),
    )
    conn.commit()
    conn.close()


def advance_rotation(week_id, placer_id):
    """
    After a week completes, record who placed and process penalty queue.

    Sets the placer on the week record and marks any penalty queue entry as processed.
    """
    conn = get_db()

    # Record the placer on the week
    conn.execute(
        "UPDATE weeks SET placer_id = ? WHERE id = ?",
        (placer_id, week_id),
    )

    # Mark any penalty queue entry for this player as processed
    conn.execute(
        "UPDATE rotation_queue SET processed = 1 "
        "WHERE player_id = ? AND processed = 0 "
        "ORDER BY position ASC LIMIT 1",
        (placer_id,),
    )

    conn.commit()
    conn.close()


def get_rotation_display():
    """
    Build the rotation queue display data.

    Returns a dict with next_placer, queue list, and last placer info.
    """
    conn = get_db()

    # Get last completed week's placer
    last_week = conn.execute(
        "SELECT w.*, pl.formal_name as placer_name FROM weeks w "
        "LEFT JOIN players pl ON w.placer_id = pl.id "
        "WHERE w.status = 'completed' AND w.placer_id IS NOT NULL "
        "ORDER BY w.id DESC LIMIT 1"
    ).fetchone()
    conn.close()

    last_placer = None
    last_week_num = None
    if last_week:
        last_placer = get_player_by_id(last_week["placer_id"])
        last_week_num = last_week["week_number"]

    next_placer = get_next_placer()
    queue = _build_queue(next_placer)

    return {
        "next_placer": next_placer,
        "last_placer": last_placer,
        "last_week_number": last_week_num,
        "queue": queue,
    }


def _build_queue(next_placer):
    """Build the full rotation queue starting from the next placer."""
    players = get_rotation_order()
    conn = get_db()

    # Get unprocessed penalty queue entries
    penalty_entries = conn.execute(
        "SELECT rq.*, pl.formal_name FROM rotation_queue rq "
        "JOIN players pl ON rq.player_id = pl.id "
        "WHERE rq.processed = 0 ORDER BY rq.position"
    ).fetchall()
    conn.close()

    queue = []

    # Add penalty queue entries first
    for entry in penalty_entries:
        player = get_player_by_id(entry["player_id"])
        queue.append({
            "formal_name": player["formal_name"],
            "reason": entry["reason"],
        })

    # Add standard rotation (starting from next regular player)
    if not next_placer:
        return queue

    # Find start index in standard rotation
    start_idx = 0
    # If there are penalty entries, standard rotation starts after them
    if penalty_entries:
        # Find where standard rotation picks up
        last_placer_ids = {e["player_id"] for e in penalty_entries}
        for i, p in enumerate(players):
            if p["id"] == next_placer["id"] and p["id"] not in last_placer_ids:
                start_idx = i
                break
    else:
        for i, p in enumerate(players):
            if p["id"] == next_placer["id"]:
                start_idx = i
                break

    # Build standard rotation order
    penalty_player_ids = {e["player_id"] for e in penalty_entries}
    for offset in range(len(players)):
        idx = (start_idx + offset) % len(players)
        player = players[idx]
        if player["id"] not in penalty_player_ids:
            queue.append({
                "formal_name": player["formal_name"],
                "reason": None,
            })

    return queue
