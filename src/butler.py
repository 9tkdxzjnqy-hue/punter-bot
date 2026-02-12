"""
The Betting Butler — message formatting module.

All bot responses are formatted through this module to maintain
a consistent butler personality inspired by Stevens from Remains of the Day.
"""


def pick_confirmed(player, description, odds, is_update=False):
    """Confirm a pick has been recorded."""
    action = "Updated" if is_update else "Noted and recorded"
    return (
        f"{action}, {player['formal_name']}. "
        f"{description} @ {odds}."
    )


def picks_status(submitted, missing):
    """Show who has and hasn't submitted picks."""
    if not missing:
        return ""
    missing_names = [p["formal_name"] for p in missing]
    return f"Awaiting selections from {_join_names(missing_names)}."


def all_picks_in(placer):
    """Announce all picks are in and who places the bet."""
    return (
        f"All selections have been received. "
        f"{placer['formal_name']}, you are next in the rotation to place the wager."
    )


def result_announced(player, description, odds, outcome):
    """Announce a result."""
    if outcome == "win":
        verdict = "\u2705 Winner."
        prefix = "I'm pleased to report"
    elif outcome == "loss":
        verdict = "\u274c Lost."
        prefix = "I'm afraid"
    else:
        verdict = "Void."
        prefix = "I must inform you"

    return (
        f"{prefix} \u2014 {player['formal_name']}'s selection: "
        f"{description} @ {odds}. {verdict}"
    )


def penalty_suggested(player, streak_count, penalty_type, amount):
    """Suggest a penalty for Ed to confirm."""
    if penalty_type == "late":
        return (
            f"{player['formal_name']}, your selection was received after the deadline. "
            f"You will place next week's wager. Rotation queue updated."
        )

    if penalty_type == "streak_3":
        return (
            f"I regret to inform you that {player['formal_name']} has incurred "
            f"{streak_count} consecutive losses. The suggested penalty is to pay "
            f"for next week's bet. Mr Edmund, would you kindly confirm: "
            f"!confirm penalty {player['nickname']}"
        )

    return (
        f"I regret to inform you that {player['formal_name']} has incurred "
        f"{streak_count} consecutive losses. The suggested penalty is "
        f"\u20ac{amount:.0f} to the vault. Mr Edmund, would you kindly confirm: "
        f"!confirm penalty {player['nickname']}"
    )


def penalty_confirmed(player, amount, vault_total):
    """Confirm a penalty has been applied."""
    if amount > 0:
        return (
            f"Penalty confirmed. Vault updated: \u20ac{vault_total:.0f} total.\n"
            f"{player['formal_name']}, please send \u20ac{amount:.0f} to Mr Edmund via Revolut."
        )
    return (
        f"Penalty confirmed. {player['formal_name']} will place next week's wager."
    )


def weekend_summary(results, week_number):
    """Post-weekend results summary."""
    winners = [r for r in results if r["outcome"] == "win"]
    losers = [r for r in results if r["outcome"] == "loss"]

    lines = [f"Weekend complete \u2014 Week {week_number}."]

    if winners:
        winner_names = [r["formal_name"] for r in winners]
        lines.append(f"Won: {', '.join(winner_names)}")

    if losers:
        loser_names = [r["formal_name"] for r in losers]
        lines.append(f"Lost: {', '.join(loser_names)}")

    won_count = len(winners)
    total = len(results)
    lines.append(f"Accumulator: {'Won' if won_count == total else 'Lost'} ({won_count} of {total} won)")

    return "\n".join(lines)


def weekly_recap(week_number, leaderboard, rotation_next):
    """Monday morning recap."""
    lines = [
        f"Good morning, gentlemen. Week {week_number} recap:",
        "",
        "\U0001f3c6 LEADERBOARD",
        "\u2501" * 22,
    ]

    medals = ["\U0001f947", "\U0001f948", "\U0001f949"]
    for i, entry in enumerate(leaderboard):
        medal = medals[i] if i < 3 else "  "
        lines.append(
            f"{medal} {entry['formal_name']}: {entry['win_rate']:.1f}% "
            f"({entry['wins']}/{entry['total']})"
        )
        lines.append(f"   Form: {entry['form']}")

    lines.append("")
    lines.append(f"Next to place: {rotation_next['formal_name']}")

    return "\n".join(lines)


def reminder_thursday():
    """Thursday 7PM reminder to all players."""
    return (
        "Good evening, gentlemen. May I remind you that picks are due "
        "by 10 PM Friday."
    )


def reminder_friday(missing):
    """Friday 5PM reminder to missing players."""
    names = [p["formal_name"] for p in missing]
    return (
        f"Pardon the interruption. {_join_names(names)} \u2014 "
        f"5 hours remain to submit your selections."
    )


def reminder_final(missing):
    """Friday 9:30PM final warning."""
    names = [p["formal_name"] for p in missing]
    return (
        f"I do hope you'll forgive the urgency. {_join_names(names)} \u2014 "
        f"30 minutes remain. This is the final reminder."
    )


def rotation_display(next_placer, queue, last_placer=None, last_week=None):
    """Format the rotation queue for display."""
    lines = [
        "\U0001f504 ROTATION STATUS",
        "\u2501" * 22,
    ]

    if last_placer and last_week:
        lines.append(f"Last Placed: {last_placer['formal_name']} (Week {last_week})")

    lines.append(f"Next Up: {next_placer['formal_name']} \U0001f448")
    lines.append("")
    lines.append("Queue:")

    for i, entry in enumerate(queue, 1):
        suffix = f" (penalty \u2014 {entry['reason']})" if entry.get("reason") else ""
        lines.append(f"{i}. {entry['formal_name']}{suffix}")

    return "\n".join(lines)


def stats_display(player, stats):
    """Format player statistics."""
    lines = [
        f"\U0001f4ca {player['formal_name']}'s Statistics",
        "\u2501" * 22,
        f"Win Rate: {stats['win_rate']:.1f}% ({stats['wins']}/{stats['total']})",
        f"Current Streak: {stats['streak']}",
        f"Form: {stats['form']}",
    ]
    return "\n".join(lines)


def leaderboard_display(entries):
    """Format the leaderboard."""
    lines = [
        "\U0001f3c6 LEADERBOARD",
        "\u2501" * 22,
    ]

    medals = ["\U0001f947", "\U0001f948", "\U0001f949"]
    for i, entry in enumerate(entries):
        medal = medals[i] if i < 3 else "  "
        lines.append(
            f"{medal} {entry['formal_name']}: {entry['win_rate']:.1f}% "
            f"({entry['wins']}/{entry['total']})"
        )
        lines.append(f"   Form: {entry['form']}")
        lines.append("")

    return "\n".join(lines).rstrip()


def vault_display(total):
    """Format vault total."""
    return f"Vault balance: \u20ac{total:.0f}"


def help_text():
    """Format the help message."""
    return (
        "At your service. Available commands:\n"
        "!stats — Your personal statistics\n"
        "!stats [player] — Stats for a specific player\n"
        "!leaderboard — Win rate rankings\n"
        "!rotation — Current rotation and queue\n"
        "!vault — Vault total\n"
        "!help — This message\n"
        "\n"
        "Admin (Mr Edmund only):\n"
        "!confirm penalty [player] — Confirm a pending penalty\n"
        "!override [player] [win/loss] — Change a result\n"
        "!resetweek — Reset the current week"
    )


def _join_names(names):
    """Join names with commas and 'and'."""
    if len(names) == 0:
        return ""
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]
