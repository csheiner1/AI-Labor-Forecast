"""Flask dashboard for AI Labor Displacement Social Impact analysis.

4 pages:
1. /equity       - Equity Impact (race, gender, age, wage quintile)
2. /geographic   - Geographic Risk (state/metro vulnerability)
3. /political    - Political Landscape (education-partisan proxy, swing states)
4. /transitions  - Transition Pathways (O*NET skill similarity)
"""
import os
import re
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, jsonify, g

_SOC_RE = re.compile(r'^\d{2}-\d{4}$')
from dashboard.data_loader import store

app = Flask(__name__)


@app.before_request
def ensure_data_loaded():
    """Load workbook data on first request and set template globals."""
    store.load()
    g.n_socs = len(store.soc_lookup)
    g.n_sectors = len(store.get_sectors())


@app.route("/")
def index():
    """Landing page with overview."""
    data = store.get_all()
    total_emp = sum(r.get("Employment_2024_K", 0) or 0 for r in data)
    return render_template("index.html",
                           n_socs=len(data),
                           total_emp=total_emp,
                           sectors=store.get_sectors())


@app.route("/equity")
def equity():
    """Equity Impact page."""
    data = sorted(store.get_all(),
                  key=lambda r: r.get("displaced_K_mod_low") or 0,
                  reverse=True)
    return render_template("equity.html", data=data, sectors=store.get_sectors())


@app.route("/geographic")
def geographic():
    """Geographic Risk page."""
    data = sorted(store.get_all(),
                  key=lambda r: r.get("displaced_K_mod_low") or 0,
                  reverse=True)
    # Precompute unique states for the filter dropdown (avoids O(n^2) in template)
    all_states = set()
    for r in data:
        for key in ("Top_State_1", "Top_State_2", "Top_State_3"):
            val = r.get(key)
            if val and isinstance(val, str):
                all_states.add(val)
    return render_template("geographic.html", data=data, all_states=sorted(all_states))


@app.route("/political")
def political():
    """Political Landscape page."""
    data = sorted(store.get_all(),
                  key=lambda r: r.get("displaced_K_mod_low") or 0,
                  reverse=True)
    return render_template("political.html", data=data)


@app.route("/transitions")
def transitions():
    """Transition Pathways page."""
    data = sorted(store.get_all(),
                  key=lambda r: r.get("displaced_K_mod_low") or 0,
                  reverse=True)
    return render_template("transitions.html", data=data)


@app.route("/api/transition/<soc_code>")
def api_transition(soc_code):
    """API endpoint: find transition targets for a SOC code."""
    # Validate SOC format
    if not _SOC_RE.match(soc_code):
        return jsonify({"error": "Invalid SOC format. Expected XX-XXXX."}), 400

    from social_impact.onet_skills import get_cached_vectors, find_transition_targets

    soc_list, elements, matrix, soc_to_idx, norms = get_cached_vectors(
        set(store.soc_lookup.keys()))
    displacement_data = store.get_displacement_data()

    try:
        max_d = float(request.args.get("max_displacement", 0.15))
    except (ValueError, TypeError):
        max_d = 0.15
    max_d = max(0.0, min(1.0, max_d))

    try:
        n = int(request.args.get("n", 10))
    except (ValueError, TypeError):
        n = 10
    n = max(1, min(50, n))
    targets = find_transition_targets(soc_code, soc_list, matrix,
                                       displacement_data, n_candidates=n,
                                       max_displacement=max_d,
                                       soc_to_idx=soc_to_idx, norms=norms)
    source = store.get_soc(soc_code)
    return jsonify({
        "source": {
            "soc": soc_code,
            "title": (source.get("Job_Title") or source.get("Custom_Title", "")) if source else "",
            "d_mod_low": source.get("d_mod_low") if source else None,
        },
        "targets": targets,
    })


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    app.run(debug=debug, port=5001)
