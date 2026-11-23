"""Elo rating calculation (same idea as chess ratings)."""

K_FACTOR = 32  # maximum points a single match can move a rating


def expected_score(rating: int, opponent_rating: int) -> float:
    """Probability (0..1) that a player with `rating` beats `opponent_rating`."""
    return 1 / (1 + 10 ** ((opponent_rating - rating) / 400))


def rating_changes(rating1: int, rating2: int, score1: float) -> tuple[int, int]:
    """Return (change for player 1, change for player 2).

    score1 is player 1's result: 1 = win, 0.5 = draw, 0 = loss.
    The two changes always add up to zero.
    """
    change1 = round(K_FACTOR * (score1 - expected_score(rating1, rating2)))
    return change1, -change1