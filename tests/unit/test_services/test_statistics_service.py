#
# tests/unit/test_services/test_statistics_service.py
# Tests for StatisticsService aggregation methods
#

from steam_library_manager.core.game import Game
from steam_library_manager.services.statistics_service import StatisticsService


def _g(aid, name, **kw):
    """Helper to create a Game with defaults."""
    return Game(app_id=str(aid), name=name, **kw)


def test_overview_total():
    svc = StatisticsService([_g(1, "A"), _g(2, "B"), _g(3, "C")])
    assert svc.overview()["total"] == 3


def test_overview_never_played():
    svc = StatisticsService([_g(1, "A", playtime_minutes=0), _g(2, "B", playtime_minutes=100)])
    ov = svc.overview()
    assert ov["never_played"] == 1
    assert ov["never_played_pct"] == 50.0


def test_overview_perfect_games():
    svc = StatisticsService(
        [
            _g(1, "A", achievement_total=10, achievement_perfect=True),
            _g(2, "B", achievement_total=10, achievement_perfect=False),
        ]
    )
    assert svc.overview()["perfect_games"] == 1


def test_genres_by_count():
    svc = StatisticsService(
        [
            _g(1, "A", genres=["Action", "RPG"]),
            _g(2, "B", genres=["Action"]),
        ]
    )
    slices = svc.genres_by_count()
    labels = {s.label: s.value for s in slices}
    assert labels["Action"] == 2
    assert labels["Rpg"] == 1  # capitalize()


def test_genres_by_playtime():
    svc = StatisticsService(
        [
            _g(1, "A", playtime_minutes=6000, genres=["Action"]),
            _g(2, "B", playtime_minutes=60, genres=["RPG"]),
        ]
    )
    slices = svc.genres_by_playtime()
    labels = {s.label: s.value for s in slices}
    assert labels["Action"] == 100.0  # 6000/60
    assert labels["RPG"] == 1.0


def test_genres_playtime_vs_count_killer_test():
    """THE killer insight: 50 RPGs with 1h each vs 5 Shooters with 100h each."""
    rpgs = [_g(i + 1, "RPG%d" % i, playtime_minutes=60, genres=["RPG"]) for i in range(50)]
    shooters = [_g(100 + i, "FPS%d" % i, playtime_minutes=6000, genres=["Shooter"]) for i in range(5)]
    svc = StatisticsService(rpgs + shooters)

    by_count = {s.label: s.value for s in svc.genres_by_count()}
    assert by_count["Rpg"] == 50
    assert by_count["Shooter"] == 5

    by_time = {s.label: s.value for s in svc.genres_by_playtime()}
    assert by_time["Shooter"] > by_time["RPG"]  # Shooter tops playtime!


def test_platforms():
    svc = StatisticsService(
        [
            _g(1, "A", platforms=["windows", "linux"]),
            _g(2, "B", platforms=["windows"]),
        ]
    )
    slices = svc.platforms()
    labels = {s.label: s.value for s in slices}
    assert labels["Windows"] == 2
    assert labels["Linux"] == 1


def test_deck_status():
    svc = StatisticsService(
        [
            _g(1, "A", steam_deck_status="verified"),
            _g(2, "B", steam_deck_status="playable"),
            _g(3, "C", steam_deck_status="verified"),
        ]
    )
    slices = svc.deck_status()
    labels = {s.label: s.value for s in slices}
    assert labels["verified"] == 2
    assert labels["playable"] == 1


def test_achievement_buckets():
    svc = StatisticsService(
        [
            _g(1, "A", achievement_total=50, achievement_perfect=True, achievement_percentage=100.0),
            _g(2, "B", achievement_total=100, achievement_percentage=80.0),
            _g(3, "C", achievement_total=0),
        ]
    )
    slices = svc.achievement_buckets()
    labels = {s.label: s.value for s in slices}
    assert labels["perfect"] == 1
    assert labels["almost"] == 1
    assert labels["none"] == 1


def test_perfect_games_list():
    svc = StatisticsService(
        [
            _g(1, "Zelda", achievement_perfect=True, achievement_total=10),
            _g(2, "Mario", achievement_perfect=True, achievement_total=20),
            _g(3, "Sonic", achievement_perfect=False, achievement_total=10),
        ]
    )
    result = svc.perfect_games()
    assert len(result) == 2
    assert result[0].name == "Mario"  # alphabetical
    assert result[1].name == "Zelda"


def test_almost_done():
    svc = StatisticsService(
        [
            _g(1, "A", achievement_total=100, achievement_percentage=90.0),
            _g(2, "B", achievement_total=100, achievement_percentage=50.0),
            _g(3, "C", achievement_total=100, achievement_percentage=100.0, achievement_perfect=True),
        ]
    )
    result = svc.almost_done(threshold=80.0)
    assert len(result) == 1
    assert result[0].name == "A"


def test_rare_achievements_no_db():
    svc = StatisticsService([_g(1, "A")])
    result = svc.rare_achievements()
    assert result == {"rare_count": 0, "ultra_rare_count": 0, "total_unlocked": 0}


def test_top_played():
    svc = StatisticsService(
        [
            _g(1, "A", playtime_minutes=100),
            _g(2, "B", playtime_minutes=500),
            _g(3, "C", playtime_minutes=300),
        ]
    )
    top = svc.top_played(n=2)
    assert len(top) == 2
    assert top[0].label == "B"
    assert top[0].value == round(500 / 60, 1)


def test_shame_pile():
    svc = StatisticsService(
        [
            _g(1, "A", playtime_minutes=0, installed=True),
            _g(2, "B", playtime_minutes=0, installed=False),
            _g(3, "C", playtime_minutes=120),
        ]
    )
    sp = svc.shame_pile()
    assert sp["total"] == 2
    assert sp["installed"] == 1
    assert sp["not_installed"] == 1


def test_playtime_buckets():
    svc = StatisticsService(
        [
            _g(1, "A", playtime_minutes=0),
            _g(2, "B", playtime_minutes=30),
            _g(3, "C", playtime_minutes=120),
            _g(4, "D", playtime_minutes=7200),
        ]
    )
    slices = svc.playtime_buckets()
    labels = {s.label: s.value for s in slices}
    assert labels["0h"] == 1
    assert labels["lt_1h"] == 1
    assert labels["1_5h"] == 1
    assert labels["100h_plus"] == 1


def test_pegi_distribution():
    svc = StatisticsService(
        [
            _g(1, "A", pegi_rating="18"),
            _g(2, "B", pegi_rating="12"),
            _g(3, "C", pegi_rating="18"),
        ]
    )
    slices = svc.pegi_distribution()
    labels = {s.label: s.value for s in slices}
    assert labels["18"] == 2
    assert labels["12"] == 1


def test_review_buckets_keys():
    svc = StatisticsService(
        [
            _g(1, "A", review_percentage=97, review_count=5000),
            _g(2, "B", review_percentage=85, review_count=1000),
            _g(3, "C", review_percentage=0, review_count=0),
        ]
    )
    slices = svc.review_buckets()
    labels = {s.label for s in slices}
    assert "op_95" in labels
    assert "vp_80" in labels
    assert "no_reviews" in labels


def test_top_developers():
    svc = StatisticsService(
        [
            _g(1, "A", developer="Valve"),
            _g(2, "B", developer="Valve, Hidden Path"),
            _g(3, "C", developer="CD Projekt"),
        ]
    )
    slices = svc.top_developers()
    labels = {s.label: s.value for s in slices}
    assert labels["Valve"] == 2
    assert labels["Hidden Path"] == 1


def test_hltb_buckets():
    svc = StatisticsService(
        [
            _g(1, "A", hltb_main_story=3.0),
            _g(2, "B", hltb_main_story=15.0),
            _g(3, "C", hltb_main_story=0.0),
        ]
    )
    slices = svc.hltb_buckets()
    labels = {s.label: s.value for s in slices}
    assert labels["lt_5h"] == 1
    assert labels["10_20h"] == 1
    assert labels["no_data"] == 1


def test_empty_games_list():
    svc = StatisticsService([])
    ov = svc.overview()
    assert ov["total"] == 0
    assert ov["never_played_pct"] == 0
    assert svc.genres_by_count() == []
    assert svc.shame_pile()["total"] == 0


def test_count_list_field_only_lists():
    """String fields should not be counted."""
    svc = StatisticsService([_g(1, "A", developer="Valve")])
    # developer is a string, not a list - _count_list_field should ignore it
    cnt = svc._count_list_field("developer")
    assert len(cnt) == 0  # string "Valve" is not iterated as list
