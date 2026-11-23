"""Tests for the Elo rating formula (no database needed)."""
from app.elo import expected_score, rating_changes


def test_equal_ratings_have_equal_chances():
    assert expected_score(1000, 1000) == 0.5


def test_win_between_equal_players_gives_16_points():
    assert rating_changes(1000, 1000, 1) == (16, -16)


def test_underdog_win_gives_many_points():
    assert rating_changes(1000, 1400, 1) == (29, -29)


def test_favourite_win_gives_few_points():
    assert rating_changes(1400, 1000, 1) == (3, -3)


def test_draw_between_equal_players_changes_nothing():
    assert rating_changes(1200, 1200, 0.5) == (0, 0)


def test_changes_always_add_up_to_zero():
    for r1 in range(800, 2001, 100):
        for r2 in range(800, 2001, 100):
            for score in (0, 0.5, 1):
                change1, change2 = rating_changes(r1, r2, score)
                assert change1 + change2 == 0