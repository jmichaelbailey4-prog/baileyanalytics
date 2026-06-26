"""Severity band descriptors — the structured, single-source map of how a reading
becomes a badge (score-explain-order follow-up, 2026-06-26).

Dependency-free on purpose: `narrative.py` imports this to attach a `.band_spec` to
every severity rule (factories build the spec from their threshold args; bespoke
rules attach one explicitly), so there is no import cycle. Consumers
(`build.py`, `methodology.py`, the drift-lock test, `staticread.py`) read the spec
off the rule via `getattr(rule, "band_spec", None)`.

The numbers live ONCE: a factory's spec is derived from the same args that drive its
behavior; a bespoke rule's spec is guarded by test_bands.py, which probes the live
rule against the declared edges. Curated 'why these bands' prose lives in
reasons.BAND_WHY (keyed by `band_tag`), reviewed there.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class BandSpec:
    """One rule's decision axis.

    kind     — how to read the decision value from observations:
               'level'         latest value (raw),
               'yoy'           latest value, already a year-over-year %,
               'yoy_computed'  trailing-12-month % the rule computes internally,
               'delta_from_low' points above the trailing-12-month low,
               'custom'        history-dependent; not a static axis (probe=False).
    unit     — axis unit for display ('%', '$', 'σ', 'months', '' …).
    edges    — ascending thresholds.
    segments — status per interval, low->high (len == len(edges)+1).
    cap      — optional status ceiling (e.g. GEPU caps at 'watch').
    probe    — False excludes the rule from the strict edge-flip drift test.
    """
    kind: str
    unit: str
    edges: tuple
    segments: tuple
    value_format: str = "decimal"  # axis formatter: "decimal" | "thousands"
    axis_label: str = ""
    cap: str = ""
    probe: bool = True


def _value_year_ago(obs):
    """Value ~one year before the latest observation, or None if too short.
    Mirrors narrative._value_year_ago (kept local so bands stays dep-free)."""
    last_date = obs[-1][0]
    target = f"{int(last_date[:4]) - 1}{last_date[4:]}"
    result = None
    for d, val in obs:
        if d <= target:
            result = val
        else:
            break
    return result


def synth_obs(kind, value):
    """A minimal observations list whose decision value equals `value`, for the
    drift-lock probes. Each kind builds exactly what its decision_value reads."""
    if kind in ("level", "yoy"):
        # A few year-spaced points all at `value`: rules that read only obs[-1][1]
        # are satisfied, and any _value_year_ago call sees a flat (no-op) prior.
        return [(f"{2018 + i:04d}-01-01", float(value)) for i in range(6)]
    if kind == "yoy_computed":
        base = 100.0
        return [("2023-06-01", base), ("2024-06-01", base * (1 + value / 100.0))]
    if kind == "delta_from_low":
        # 11 points at a flat low, then one `value` above it.
        low = 4.0
        out = [(f"{2023}-{m:02d}-01", low) for m in range(1, 12)]
        out.append((f"{2024}-01-01", low + float(value)))
        return out
    return []


def decision_value(kind, obs):
    """The value the rule's bands are read against, or None when undefined."""
    if not obs:
        return None
    v = obs[-1][1]
    if kind in ("level", "yoy"):
        return v
    if kind == "yoy_computed":
        prior = _value_year_ago(obs)
        if prior is None or prior == 0:
            return None
        return (v - prior) / abs(prior) * 100
    if kind == "delta_from_low":
        window = [val for _, val in obs[-12:]]
        return v - min(window)
    return None  # custom / unknown


def status_at(spec, value):
    """The segment status for `value` under the dominant `>=` convention
    (used for the marker / an invariant check, not boundary-exact grading)."""
    i = sum(1 for e in spec.edges if value >= e)
    return spec.segments[i]


def segment_ranges(spec):
    """[{status, lo, hi}] per segment, low->high; lo None for the first, hi None
    for the last. The methodology page and the strip render from this."""
    out = []
    for i, status in enumerate(spec.segments):
        lo = spec.edges[i - 1] if i > 0 else None
        hi = spec.edges[i] if i < len(spec.edges) else None
        out.append({"status": status, "lo": lo, "hi": hi})
    return out
