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
    return (s[mid - 1] + s[mid]) / 2


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


bars, highs, lows = build_reconstructed_bars()
for name, seq in [('HIGH', highs), ('LOW', lows)]:
    prices = [x['price'] for x in seq]
    starts = []
    candidate = None
    zone_members = None
    for i, p in enumerate(prices):
        if zone_members is None:
            if candidate is None:
                candidate = [p]
                continue
            tol = prior_gap_median(prices, i)
            if tol is not None and abs(p - median(candidate)) <= tol:
                zone_members = candidate + [p]
                starts.append({'start_idx': i, 'members': zone_members[:]})
                candidate = None
            else:
                candidate = [p]
        else:
            tol = prior_gap_median(prices, i)
            if tol is not None and abs(p - median(zone_members)) <= tol:
                zone_members.append(p)

    total_followups = 0
    total_members = 0
    total_non = 0
    total_no_tol = 0
    max_run = 0
    runs = []
    reentries_after_non = 0
    first_nonmember_after_creation = []
    for start in starts:
        zone = start['members'][:]
        start_idx = start['start_idx']
        current_run = 0
        seen_non = False
        for j in range(start_idx + 1, len(prices)):
            total_followups += 1
            tol_j = prior_gap_median(prices, j)
            if tol_j is None:
                total_no_tol += 1
                continue
            if abs(prices[j] - median(zone)) <= tol_j:
                total_members += 1
                zone.append(prices[j])
                if seen_non:
                    reentries_after_non += 1
                current_run = 0
            else:
                total_non += 1
                seen_non = True
                current_run += 1
                if current_run > max_run:
                    max_run = current_run
                runs.append(current_run)
                if len(first_nonmember_after_creation) == 0:
                    first_nonmember_after_creation.append(j)

    print('===', name, '===')
    print('total_swings', len(seq))
    print('valid_zone_starts', len(starts))
    print('subsequent_member_swings', total_members)
    print('subsequent_nonmember_swings', total_non)
    print('subsequent_no_tolerance_events', total_no_tol)
    print('max_nonmember_run', max_run)
    print('average_nonmember_run', (sum(runs) / len(runs)) if runs else 0.0)
    print('reentries_after_nonmember', reentries_after_non)
    if starts:
        print('avg_followups_per_zone', total_followups / len(starts))
    else:
        print('avg_followups_per_zone', 0)
    print('')
