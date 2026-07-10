"""
Pure rule-based condition detection off mood/stress data -- no LLM
involved anywhere in this file. Detected conditions are matched against
the curated InsightSuggestion pool. The self-harm check is intentionally
kept completely separate from that pool and from any AI-generated text --
it is a fixed, always-identical message that fires on a plain condition.
"""
from datetime import timedelta
from django.utils import timezone

EPDS_SELF_HARM_ITEM_INDEX = 9  # 0-indexed position of the self-harm item in the EPDS answers list


def detect_conditions(mood_entries, stress_tests):
    """
    mood_entries / stress_tests: iterables within the analysis window,
    oldest first. Returns a list of condition code strings -- multiple can
    be active at once (e.g. mood_dip + stress_test_overdue together).
    """
    today = timezone.localdate()
    conditions = []

    mood_list = list(mood_entries)
    stress_list = list(stress_tests)

    if len(mood_list) >= 3:
        last_7_cutoff = today - timedelta(days=7)
        prev_7_cutoff = today - timedelta(days=14)
        recent = [e.score for e in mood_list if e.logged_at.date() >= last_7_cutoff]
        previous = [e.score for e in mood_list if prev_7_cutoff <= e.logged_at.date() < last_7_cutoff]
        if recent and previous:
            diff = (sum(recent) / len(recent)) - (sum(previous) / len(previous))
            if diff <= -0.5:
                conditions.append("mood_dip")
            elif diff >= 0.5:
                conditions.append("mood_improved")
            else:
                conditions.append("mood_stable")

    if mood_list:
        last_log_date = max(e.logged_at.date() for e in mood_list)
        days_since_log = (today - last_log_date).days
        if days_since_log >= 4:
            conditions.append("no_recent_mood_log")
        elif len(mood_list) >= 10:
            conditions.append("consistent_logging")
    else:
        conditions.append("no_recent_mood_log")

    if not stress_list:
        conditions.append("no_stress_test_taken")
    else:
        latest = stress_list[-1]
        days_since_test = (today - latest.taken_at.date()).days
        if days_since_test >= 21:
            conditions.append("stress_test_overdue")

        if latest.risk_level == "high":
            conditions.append("high_risk_latest")
        elif latest.risk_level == "moderate":
            conditions.append("moderate_risk_latest")

        if len(stress_list) >= 2:
            risk_order = {"low": 0, "moderate": 1, "high": 2}
            if risk_order.get(latest.risk_level, 0) > risk_order.get(stress_list[-2].risk_level, 0):
                conditions.append("worsening_risk_trend")

    if not conditions:
        conditions.append("general")

    return conditions


def check_self_harm_flag(all_stress_tests):
    """
    Looks ONLY at the most recent EPDS test's specific self-harm item,
    independent of the overall risk_level -- a mother could score
    low/moderate overall while still answering non-zero on this one item.
    Checked against her FULL test history, not just the 30-day chart
    window, so a concerning answer doesn't stop being flagged just because
    the window rolled past it.
    """
    epds_tests = [t for t in all_stress_tests if t.test_type == "EPDS"]
    if not epds_tests:
        return False
    latest_epds = max(epds_tests, key=lambda t: t.taken_at)
    answers = latest_epds.answers or []
    if len(answers) > EPDS_SELF_HARM_ITEM_INDEX:
        return answers[EPDS_SELF_HARM_ITEM_INDEX] > 0
    return False