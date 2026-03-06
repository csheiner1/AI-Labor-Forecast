"""
SOC → Occupation Group mapping for Core/Common classification.

Each (Sector, SOC) pair in the staffing patterns is classified as either
"Core" (industry-defining role) or one of 9 Common groups.

Common Groups:
  G1_Exec_Management    - C-suite, general/ops managers, PMs, consultants
  G2_HR_People          - HR managers/specialists, training, comp/benefits
  G3_Finance_Accounting - Financial managers, accountants, bookkeepers, clerks
  G4_IT_Digital         - IT managers, all computer/math occupations
  G5_Marketing_Creative - Marketing managers, PR, market research, designers, writers
  G6_Sales_BizDev       - Sales managers, sales reps, account executives
  G7_Legal_Compliance   - Lawyers, paralegals, compliance officers
  G8_Procurement_Supply - Purchasing, logistics, supply chain, production planning
  G9_Admin_Office       - Admin managers, secretaries, customer service, data entry
"""

# ── SOC → Functional Group (based on SOC code alone) ──────────────────────

def get_functional_group(soc: str) -> str:
    """Map a SOC code to its functional group. Domain-specific SOCs return
    their domain name (Healthcare, Education, etc.) — these become Core
    candidates when concentrated in their home sector."""

    major = soc[:2]
    detailed = soc[:7]

    # ── G2: HR & People Ops ──
    if detailed in ('11-3111', '11-3121', '11-3131',
                    '13-1071', '13-1075', '13-1141', '13-1151',
                    '43-4161'):
        return 'G2_HR_People'

    # ── G3: Finance & Accounting ──
    if detailed == '11-3031':
        return 'G3_Finance_Accounting'
    if major == '13' and soc[:5] == '13-20':  # all financial specialists
        return 'G3_Finance_Accounting'
    if detailed in ('43-3011', '43-3021', '43-3031', '43-3051',
                    '43-3061', '43-3071', '43-3099',
                    '43-4011', '43-4041', '43-4131', '43-4141',
                    '43-9111'):
        return 'G3_Finance_Accounting'

    # ── G4: IT & Digital Systems ──
    if detailed == '11-3021':
        return 'G4_IT_Digital'
    if major == '15':
        return 'G4_IT_Digital'

    # ── G5: Marketing, Creative & Communications ──
    if detailed in ('11-2021', '11-2032', '11-2011'):
        return 'G5_Marketing_Creative'
    if detailed == '13-1161':
        return 'G5_Marketing_Creative'
    if major == '27':
        return 'G5_Marketing_Creative'

    # ── G6: Sales & Business Development ──
    if detailed == '11-2022':
        return 'G6_Sales_BizDev'
    if major == '41':
        return 'G6_Sales_BizDev'

    # ── G7: Legal & Compliance ──
    if major == '23':
        return 'G7_Legal_Compliance'
    if detailed == '13-1041':
        return 'G7_Legal_Compliance'

    # ── G8: Procurement & Supply Chain ──
    if detailed in ('11-3061', '11-3071', '13-1020', '13-1081',
                    '43-5061', '43-5032'):
        return 'G8_Procurement_Supply'

    # ── G9: Admin & Office Support ──
    if detailed in ('11-3012', '11-3013'):
        return 'G9_Admin_Office'
    if major == '43':  # remaining office/admin
        return 'G9_Admin_Office'

    # ── G1: Executive & General Management ──
    if detailed in ('11-1011', '11-1021', '11-9199'):
        return 'G1_Exec_Management'
    if detailed in ('13-1082', '13-1111', '13-1199', '13-1121'):
        return 'G1_Exec_Management'
    if major == '11':  # remaining management
        return 'G1_Exec_Management'
    if major == '13':  # remaining business operations
        return 'G1_Exec_Management'

    # ── Domain-specific (Core candidates) ──
    if major == '17':
        return 'Domain_Engineering'
    if major == '19':
        return 'Domain_Science'
    if major == '25':
        return 'Domain_Education'
    if major == '29':
        return 'Domain_Healthcare'
    if major == '21':
        return 'Domain_SocialService'
    if major == '33':
        return 'Domain_ProtectiveService'
    if major == '51':
        return 'Domain_Production'

    return 'G1_Exec_Management'  # fallback


# ── Sector-specific Core overrides ────────────────────────────────────────
# SOCs that are functionally Core for a sector even if concentration < 40%

CORE_OVERRIDES = {
    # Sector 1: Finance — securities agents are the revenue producers
    1:  {'41-3031'},
    # Sector 2: Insurance — claims adjusters + insurance sales define the sector
    2:  {'13-1031', '41-3021'},
    # Sector 6: Management Consulting — consultants are the product
    6:  {'13-1111'},
    # Sector 7: Accounting — accountants/auditors are the product
    7:  {'13-2011', '13-2082'},
    # Sector 8: Advertising/PR — key creative/strategic roles
    8:  {'27-3031', '13-1161', '27-1011', '27-3043'},
    # Sector 9: Staffing — recruiters are the product
    9:  {'13-1071'},
    # Sector 10: Real Estate — property managers + agents define the sector
    10: {'11-9141', '41-9021', '41-9022'},
    # Sector 12: Government — tax examiners + compliance officers
    12: {'13-2081', '13-1041'},
    # Sector 16: Manufacturing — production managers define the floor
    16: {'11-3051'},
    # Sector 17: Retail — pharmacists/techs/opticians are major retail functions
    17: {'29-1051', '29-2052', '29-2081'},
    # Sector 18: Construction — construction managers + estimators
    18: {'11-9021', '13-1051'},
}

# Domain SOCs that should be Core when in their "home" sectors.
# Maps functional group → set of home sector IDs.
DOMAIN_HOME_SECTORS = {
    'Domain_Engineering':       {3, 4, 14, 15, 16, 18},  # Tech, Healthcare, Energy, Arch/Eng, Mfg, Construction
    'Domain_Science':           {4, 12, 14, 15, 16},   # Healthcare, Government, Energy, Arch/Eng, Mfg
    'Domain_Education':         {11, 12},              # Education, Government (curators/archivists)
    'Domain_Healthcare':        {4},                   # Healthcare
    'Domain_SocialService':     {4, 11, 12},           # Healthcare, Education, Government
    'Domain_ProtectiveService': {12},                  # Government
    'Domain_Production':        {14, 16},              # Energy, Manufacturing
}


def classify(soc: str, sector_id: int, occ_ind_share: float) -> str:
    """Classify a (sector, SOC) pair as Core or Common group.

    Returns the occupation group label.
    """
    func_group = get_functional_group(soc)

    # Check sector-specific Core overrides
    if sector_id in CORE_OVERRIDES and soc[:7] in CORE_OVERRIDES[sector_id]:
        return 'Core'

    # Domain SOCs → Core if in a home sector (no concentration threshold —
    # a nurse in Healthcare or an engineer in Arch/Eng is Core by definition)
    if func_group.startswith('Domain_'):
        home_sectors = DOMAIN_HOME_SECTORS.get(func_group, set())
        if sector_id in home_sectors:
            return 'Core'
        # Domain SOC outside home sector → assign to nearest Common group
        domain_to_common = {
            'Domain_Engineering':       'G4_IT_Digital',
            'Domain_Science':           'G4_IT_Digital',
            'Domain_Education':         'G9_Admin_Office',
            'Domain_Healthcare':        'G9_Admin_Office',
            'Domain_SocialService':     'G9_Admin_Office',
            'Domain_ProtectiveService': 'G1_Exec_Management',
            'Domain_Production':        'G8_Procurement_Supply',
        }
        return domain_to_common.get(func_group, 'G1_Exec_Management')

    # Common group SOCs → Core if highly concentrated (>= 40%) in this sector
    # AND the functional group matches the sector's identity
    # (e.g., financial specialists Core in Finance, IT roles Core in Tech)
    FUNC_HOME_SECTORS = {
        'G3_Finance_Accounting': {1, 2, 7},    # Finance, Insurance, Accounting
        'G4_IT_Digital':         {3},           # Technology
        'G5_Marketing_Creative': {8, 13},       # Advertising, Media
        'G6_Sales_BizDev':       {17, 20},      # Retail, Wholesale
        'G7_Legal_Compliance':   {5, 12},       # Law, Government
        'G9_Admin_Office':       set(),         # never Core
        'G2_HR_People':          {9},           # Staffing
        'G8_Procurement_Supply': {19},          # Transportation
        'G1_Exec_Management':    set(),         # never Core
    }

    home = FUNC_HOME_SECTORS.get(func_group, set())
    if sector_id in home and occ_ind_share >= 40:
        return 'Core'

    return func_group


if __name__ == '__main__':
    # Quick self-test
    tests = [
        ('29-1141', 4, 88.1, 'Core'),           # Nurses in Healthcare
        ('29-2052', 4, 22.5, 'Core'),           # Pharmacy techs in Healthcare (no threshold)
        ('29-1131', 4, 5.0,  'Core'),           # Vets in Healthcare (no threshold)
        ('15-1252', 3, 55.8, 'Core'),           # Software devs in Tech
        ('15-1252', 1, 6.6,  'G4_IT_Digital'),  # Software devs in Finance
        ('43-4051', 1, 10.0, 'G9_Admin_Office'),# CSRs in Finance
        ('13-1111', 6, 28.0, 'Core'),           # Mgmt analysts in Consulting (override)
        ('17-2071', 3, 8.3,  'Core'),           # Electrical engineers in Tech (home sector)
        ('17-2071', 15, 41.9,'Core'),           # Electrical engineers in Arch/Eng
        ('17-2171', 14, 69.5,'Core'),           # Petroleum engineers in Energy
        ('25-2021', 11, 100, 'Core'),           # Teachers in Education
        ('11-1011', 3, 13.3, 'G1_Exec_Management'),  # CEOs in Tech
        ('13-2011', 7, 31.7, 'Core'),           # Accountants in Accounting (override)
        ('41-3031', 1, 95.4, 'Core'),           # Securities agents in Finance (override)
        ('13-1031', 2, 71.9, 'Core'),           # Claims adjusters in Insurance (override)
        ('11-9021', 18, 84.9,'Core'),           # Construction mgrs in Construction (override)
        ('11-3051', 16, 68.8,'Core'),           # Production mgrs in Manufacturing (override)
        ('11-9141', 10, 90.6,'Core'),           # Property mgrs in Real Estate (override)
        ('29-1051', 17, 51.8,'Core'),           # Pharmacists in Retail (override)
        ('13-2081', 12, 100, 'Core'),           # Tax examiners in Government (override)
        ('29-1141', 1, 0.1,  'G9_Admin_Office'),# Nurses in Finance (not home sector)
        ('17-2071', 20, 2.8, 'G4_IT_Digital'),  # Electrical engineers in Wholesale (not home)
    ]
    passed = 0
    for soc, sid, share, expected in tests:
        result = classify(soc, sid, share)
        status = '✓' if result == expected else '✗'
        if result != expected:
            print(f"  {status} classify({soc}, sector={sid}, share={share}) = {result}, expected {expected}")
        else:
            passed += 1
    print(f"Self-test: {passed}/{len(tests)} passed")
