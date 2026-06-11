"""The plain-English 'why' behind every prediction (spec §4 copy bank).
One sentence, no black box: model-family skeleton + a simple momentum
diagnostic. Skeletons read as complete clauses after a semicolon."""

from .cadence import PERIOD_NOUN

SKELETONS = {
    "naive": "we expect roughly the last value — this series rarely rewards cleverness",
    "seasonal-naive": "we expect roughly what this series did a year ago this {period}",
    "drift": "this projects the series' long-run average step from today's level",
    "ets": "this projects the recent level and trend forward one {period}",
    "ets-seasonal": "this projects the recent trend with the usual seasonal pattern for the {period}",
    "theta": "this blends the series' long-run trend line with its recent level",
    "sarima": "this projects recent momentum, adjusted for the series' typical reversion",
}
MIN_STREAK = 2


def streak(values):
    """('risen'|'fallen', n) for the trailing run of strictly same-sign moves,
    or None when shorter than MIN_STREAK."""
    if len(values) < MIN_STREAK + 1:
        return None
    direction = None
    n = 0
    # walk backwards pairwise: (last-1, last), (last-2, last-1), ...
    for prev, cur in zip(reversed(values[:-1]), reversed(values[1:])):
        step = "risen" if cur > prev else "fallen" if cur < prev else None
        if step is None or (direction and step != direction):
            break
        direction = step
        n += 1
    return (direction, n) if direction and n >= MIN_STREAK else None


def why(model_name, cad, values, short_label):
    period = PERIOD_NOUN.get(cad, "period")
    body = SKELETONS.get(model_name, SKELETONS["naive"]).format(period=period)
    s = streak(values)
    if s:
        verb, n = s
        return f"{short_label} has {verb} {n} straight {period}s; {body}."
    return body[0].upper() + body[1:] + "."
