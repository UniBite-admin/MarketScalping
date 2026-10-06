import sys
sys.path.insert(0, '.')

from tools.research.research_15m_groupb import build_reconstructed_bars


def median(vals):
    s = sorted(vals)
    n = len(s)
    if not s:
        return None
    mid = n // 2
    if n % 2:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2.0


def prior_gap_median(vals, idx):
    if idx < 1:
        return None
    prior = vals[:idx]
    if len(prior) < 2:
        return None
    gaps = [abs(prior[j] - prior[j - 1]) for j in range(1, len(prior))]
    if not gaps:
        return None
    selected = gaps[-5:]
    return median(selected)


def analyze(seq, label):
    prices = [x['price'] for x in seq]
    seed_count = 0
    creation_events = []
    candidate = None
    for i, p in enumerate(prices):
        if candidate is None:
            seed_count += 1
            candidate = [p]
            continue
        tol = prior_gap_median(prices, i)
        if tol is not None and abs(p - median(candidate)) <= tol:
            center = median(candidate + [p])
            creation_events.append({
                'creation_idx': i,
                'seed_idx': i - 1,
                'creation_price': p,
                'center': center,
                'tolerance': tol,
                'member_prices': candidate + [p],
            })
            candidate = None
        else:
            candidate = [p]

    immediate_count = 0
    immediate_member = 0
    immediate_non = 0
    immediate_unclassifiable = 0
    dist_values = []
    tol_values = []
    ratio_values = []

    for ev in creation_events:
        idx = ev['creation_idx']
        next_idx = idx + 1
        if next_idx >= len(prices):
            immediate_unclassifiable += 1
            immediate_count += 1
            continue
        next_p = prices[next_idx]
        next_tol = prior_gap_median(prices, next_idx)
        if next_tol is None:
            immediate_unclassifiable += 1
            immediate_count += 1
            continue
        dist = abs(next_p - ev['center'])
        dist_values.append(dist)
        tol_values.append(next_tol)
        ratio_values.append(dist / next_tol)
        immediate_count += 1
        if dist <= next_tol:
            immediate_member += 1
        else:
            immediate_non += 1

    def pct(xs, p):
        if not xs:
            return None
        xs = sorted(xs)
        ix = max(0, min(len(xs) - 1, int(round((len(xs) - 1) * p))))
        return xs[ix]

    print(label)
    print('eligible_swings', len(prices))
    print('candidate_seed_observations', seed_count)
    print('valid_zone_creation_events', len(creation_events))
    print('immediate_next_observations', immediate_count)
    print('immediate_members', immediate_member)
    print('immediate_non_members', immediate_non)
    print('unclassifiable', immediate_unclassifiable)
    print('unique_duplicate_evaluations', 0)
    print('distance_median', pct(dist_values, 0.5) if dist_values else None)
    print('distance_p75', pct(dist_values, 0.75) if dist_values else None)
    print('distance_p90', pct(dist_values, 0.90) if dist_values else None)
    print('distance_p95', pct(dist_values, 0.95) if dist_values else None)
    print('distance_min', min(dist_values) if dist_values else None)
    print('distance_max', max(dist_values) if dist_values else None)
    print('tolerance_median', pct(tol_values, 0.5) if tol_values else None)
    print('tolerance_p75', pct(tol_values, 0.75) if tol_values else None)
    print('tolerance_p90', pct(tol_values, 0.90) if tol_values else None)
    print('tolerance_p95', pct(tol_values, 0.95) if tol_values else None)
    print('tolerance_min', min(tol_values) if tol_values else None)
    print('tolerance_max', max(tol_values) if tol_values else None)
    print('ratio_median', pct(ratio_values, 0.5) if ratio_values else None)
    print('ratio_p75', pct(ratio_values, 0.75) if ratio_values else None)
    print('ratio_p90', pct(ratio_values, 0.90) if ratio_values else None)
    print('ratio_p95', pct(ratio_values, 0.95) if ratio_values else None)
    print('ratio_min', min(ratio_values) if ratio_values else None)
    print('ratio_max', max(ratio_values) if ratio_values else None)
    print('---')


_, highs, lows = build_reconstructed_bars()
analyze(highs, 'HIGH')
analyze(lows, 'LOW')
