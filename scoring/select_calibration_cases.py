"""Select 30 boundary-case occupations for Phase 1 calibration."""
import json

with open('scoring/job_profiles.json') as f:
    profiles = json.load(f)

# Build lookup
by_title = {p['custom_title']: p for p in profiles}

# 30 hand-picked boundary cases with reasons
BOUNDARY_PICKS = [
    # --- x_sub ambiguous (human-is-product vs substitutable) ---
    ("School psychologists", "Human IS the product but teletherapy/AI therapy emerging"),
    ("Financial Planner", "Robo-advisors exist but many clients want human relationship"),
    ("Real Estate Agent", "Mixed: some buyers want human, Zillow/Redfin eroding"),
    ("Management Consultant", "Judgment-heavy but AI strategy tools emerging"),
    ("Journalist", "AI writing exists but investigative journalism is human"),
    ("K-12 Teacher", "AI tutoring emerging but classroom presence valued"),
    ("Occupational Therapist", "Human relationship matters but assessment tools scaling"),
    ("Athletic Trainer", "Human motivation/physical assessment but AI coaching growing"),

    # --- workflow_simplicity ambiguous ---
    ("Registered nurses", "Mix of independent tasks and tightly coupled patient care"),
    ("Software Engineer", "Iterative cycles but some tasks quite independent"),
    ("Architect", "Design iteration loops but drafting is independent"),
    ("Emergency medical technicians", "Triage is dynamic, transport is procedural"),
    ("Oral and maxillofacial surgeons", "Tightly coupled intra-op but pre-op is structured"),
    ("Probation officers and correctional treatment specialists", "Dynamic caseloads but structured reporting"),
    ("Physical Therapist", "Physical tasks + judgment, workflow between structured and dynamic"),
    ("Film Editor", "Creative iteration but technical pipeline is linear"),

    # --- x_scale ambiguous ---
    ("Radiologic technologists and technicians", "AI screening scales but physical positioning doesn't"),
    ("Paralegal", "Document review scales enormously, client work doesn't"),
    ("Insurance Underwriter", "Risk assessment scales, complex cases don't"),
    ("Marketing Manager", "Content creation scales, strategy doesn't"),
    ("Tax Advisor", "Simple returns scale, complex advisory doesn't"),
    ("Technical writers", "Documentation scales well with AI"),

    # --- All three ambiguous ---
    ("Child, family, and school social workers", "Human element strong but case management could scale"),
    ("Veterinarians", "Physical + judgment, moderate workflow complexity"),
    ("Court reporters and simultaneous captioners", "Transcription scales but legal accuracy needs human"),
    ("Actuary", "Analysis scales but judgment on novel risks doesn't"),
    ("Urban Planner", "Mix of data analysis and stakeholder judgment"),
    ("Compliance Officer", "Routine checks scale, novel situations need judgment"),
    ("Dental hygienists", "Physical task = 0.00 autonomy but some tasks digital"),
    ("Instructional Designer", "Content creation scales but pedagogy is judgment-heavy"),

    # --- Missing sector coverage ---
    ("Logistics Manager", "Logistics & Distribution: mix of optimization (scales) and physical ops"),
    ("Power Plant Operator", "Energy & Utilities: procedural but safety-critical, dynamic emergencies"),
    ("Retail Store Manager", "Retail Trade: mix of people management and inventory optimization"),
    ("Manufacturing Engineer", "Manufacturing: process optimization scales but physical plant doesn't"),
]

calibration = []
unmatched = []
for title, reason in BOUNDARY_PICKS:
    if title in by_title:
        p = by_title[title].copy()
        p['calibration_reason'] = reason
        calibration.append(p)
    else:
        # Try partial match
        matches = [t for t in by_title if title.lower() in t.lower()]
        if matches:
            p = by_title[matches[0]].copy()
            p['calibration_reason'] = reason
            calibration.append(p)
            print(f"  Fuzzy: '{title}' -> '{matches[0]}'")
        else:
            unmatched.append(title)

print(f"Matched: {len(calibration)}/30")
if unmatched:
    print(f"Unmatched: {unmatched}")

with open('scoring/calibration_cases.json', 'w') as f:
    json.dump(calibration, f, indent=2)

print(f"\nSaved {len(calibration)} calibration cases:")
for c in calibration:
    print(f"  {c['custom_title']:45s} | {c['sector']:35s} | {c['calibration_reason']}")
