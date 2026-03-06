"""
Classify staffing pattern rows into occupation groups and produce
an aggregated summary. Run with sector range arguments.

Usage: python3 scoring/classify_staffing.py <start_sector> <end_sector>

Outputs JSON to scoring/classified_sectors_{start}_{end}.json
"""
import sys, json, openpyxl
from collections import defaultdict

sys.path.insert(0, 'scoring')
from occupation_groups import classify, get_functional_group

def run(start_sector: int, end_sector: int):
    wb = openpyxl.load_workbook('jobs-data-v3.xlsx', data_only=True)
    ws = wb['2 Staffing Patterns']

    rows = []
    flags = []

    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row[0] or not row[2]:
            continue
        sid = int(row[0])
        if sid < start_sector or sid > end_sector:
            continue

        soc = row[2]
        title = row[3]
        emp = float(row[4]) if row[4] else 0
        occ_ind_share = float(row[6]) if row[6] else 0

        group = classify(soc, sid, occ_ind_share)
        func_group = get_functional_group(soc)

        rows.append({
            'sector_id': sid,
            'sector': row[1],
            'soc': soc,
            'title': title,
            'emp': emp,
            'occ_ind_share': occ_ind_share,
            'group': group,
            'func_group': func_group,
        })

        # Flag ambiguous cases
        if func_group.startswith('Domain_') and group != 'Core' and occ_ind_share >= 15:
            flags.append({
                'soc': soc, 'title': title, 'sector_id': sid,
                'sector': row[1], 'share': occ_ind_share,
                'assigned': group, 'reason': 'Domain SOC not Core but share >= 15%'
            })
        if group == 'Core' and occ_ind_share < 30:
            flags.append({
                'soc': soc, 'title': title, 'sector_id': sid,
                'sector': row[1], 'share': occ_ind_share,
                'assigned': group, 'reason': 'Core with low concentration'
            })

    # Aggregate by (sector, group)
    agg = defaultdict(lambda: {'emp': 0, 'soc_count': 0, 'socs': []})
    for r in rows:
        key = (r['sector_id'], r['sector'], r['group'])
        agg[key]['emp'] += r['emp']
        agg[key]['soc_count'] += 1
        agg[key]['socs'].append(f"{r['soc']} {r['title']} ({r['emp']:.1f}K)")

    summary = []
    for (sid, sector, group), data in sorted(agg.items()):
        # Compute group's share of sector total
        sector_total = sum(a['emp'] for (s, _, _), a in agg.items() if s == sid)
        share = data['emp'] / sector_total * 100 if sector_total > 0 else 0
        summary.append({
            'sector_id': sid,
            'sector': sector,
            'group': group,
            'emp_k': round(data['emp'], 1),
            'share_pct': round(share, 1),
            'soc_count': data['soc_count'],
            'top_socs': sorted(data['socs'], key=lambda s: float(s.split('(')[1].rstrip('K)')), reverse=True)[:5]
        })

    result = {
        'sectors': list(range(start_sector, end_sector + 1)),
        'row_classifications': [{
            'sector_id': r['sector_id'],
            'soc': r['soc'],
            'group': r['group']
        } for r in rows],
        'summary': summary,
        'flags': flags,
    }

    outfile = f'scoring/classified_sectors_{start_sector}_{end_sector}.json'
    with open(outfile, 'w') as f:
        json.dump(result, f, indent=2)

    # Print summary
    print(f"Sectors {start_sector}-{end_sector}: {len(rows)} rows classified")
    print(f"Flags: {len(flags)}")
    for s in summary:
        if s['emp_k'] > 0:
            print(f"  {s['sector_id']:2d} {s['sector'][:30]:30s} {s['group']:25s} {s['emp_k']:8.1f}K ({s['share_pct']:5.1f}%)  [{s['soc_count']} SOCs]")

    if flags:
        print(f"\nFlagged items:")
        for f in flags:
            t = f['title'][:40]
            s = f['sector'][:25]
            print(f"  {f['soc']} {t:40s} in {s:25s} share={f['share']:.1f}%  -> {f['assigned']}  ({f['reason']})")

    return result


if __name__ == '__main__':
    start = int(sys.argv[1])
    end = int(sys.argv[2])
    run(start, end)
