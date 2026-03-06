"""Flask dashboard for AI Labor Displacement Social Impact analysis.

4 pages:
1. /equity       - Equity Impact (race, gender, age, wage quintile)
2. /geographic   - Geographic Risk (state/metro vulnerability)
3. /political    - Political Landscape (education-partisan proxy, swing states)
4. /transitions  - Transition Pathways (O*NET skill similarity)
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, jsonify
from dashboard.data_loader import store

app = Flask(__name__)


@app.before_request
def ensure_data_loaded():
    """Load workbook data on first request."""
    store.load()


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
    return render_template("geographic.html", data=data)


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
    from social_impact.onet_skills import get_cached_vectors, find_transition_targets

    soc_list, elements, matrix = get_cached_vectors(set(store.soc_lookup.keys()))
    displacement_data = {}
    for soc, rec in store.soc_lookup.items():
        displacement_data[soc] = {
            "title": rec.get("Job_Title") or rec.get("Custom_Title", ""),
            "d_mod_low": rec.get("d_mod_low", 0),
            "employment_K": rec.get("Employment_2024_K", 0),
        }

    max_d = float(request.args.get("max_displacement", 0.15))
    n = int(request.args.get("n", 10))
    targets = find_transition_targets(soc_code, soc_list, matrix,
                                       displacement_data, n_candidates=n,
                                       max_displacement=max_d)
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
    app.run(debug=True, port=5001)
