"""Configuration for Social Impact data pipeline."""
import os
import subprocess


def _find_main_repo_root():
    """Find the main git repo root, even when running inside a worktree.

    Git worktrees have a `.git` file (not directory) that points back to
    the main repo. We use `git rev-parse --git-common-dir` to find the
    shared .git directory, then derive the main repo root from it.

    Falls back to PROJECT_ROOT if detection fails (e.g. not a worktree).
    """
    try:
        git_common = subprocess.check_output(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        # git-common-dir returns path to the .git dir of the main repo
        # e.g. /path/to/main-repo/.git
        if git_common.endswith(".git"):
            return os.path.dirname(os.path.abspath(git_common))
        # If it's a bare path or nested, resolve it
        return os.path.dirname(os.path.abspath(git_common))
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKBOOK = os.path.join(PROJECT_ROOT, "jobs-data-v3.xlsx")
DATA_CACHE = os.path.join(PROJECT_ROOT, "social_impact", "data_cache")
MERGED_OUTPUT = os.path.join(PROJECT_ROOT, "social_impact", "merged_social_data.json")

# O*NET data lives in the main repo root (gitignored, not copied to worktrees).
# Use ONET_DIR_OVERRIDE env var to specify a custom path if needed.
_main_root = _find_main_repo_root() or PROJECT_ROOT
ONET_DIR = os.environ.get(
    "ONET_DIR_OVERRIDE",
    os.path.join(_main_root, "onet_data", "db_29_1_text"),
)
ONET_ZIP = os.path.join(_main_root, "onet_db.zip")

# BLS source URLs
SOURCES = {
    "cpsaat11": "https://www.bls.gov/cps/cpsaat11.xlsx",
    "cpsaat11b": "https://www.bls.gov/cps/cpsaat11b.xlsx",
    "edu_attainment": "https://www.bls.gov/emp/ind-occ-matrix/education.xlsx",
    "entry_education": "https://www.bls.gov/emp/ind-occ-matrix/occupation-entry-ed.xlsx",
    "census_soc_crosswalk": "https://www.bls.gov/cps/2018-census-occupation-classification-titles-and-code-list.xlsx",
    "oews_state": "https://www.bls.gov/oes/special-requests/oesm24st.zip",
    "oews_metro": "https://www.bls.gov/oes/special-requests/oesm24ma.zip",
}

# Union data is an HTML table, not a downloadable file
UNION_TABLE_URL = "https://www.bls.gov/news.release/union2.t03.htm"

# Foreign-born by major occupation group (from BLS 2024 report, Table 4)
# https://www.bls.gov/news.release/forbrn.t04.htm
# Values: percent foreign-born in major occupation group
FOREIGN_BORN_BY_MAJOR_GROUP = {
    "11": 12.2,  # Management
    "13": 16.1,  # Business and financial operations
    "15": 26.5,  # Computer and mathematical
    "17": 17.8,  # Architecture and engineering
    "19": 21.3,  # Life, physical, and social science
    "21": 13.1,  # Community and social service
    "23": 8.6,   # Legal
    "25": 10.9,  # Educational instruction and library
    "27": 13.5,  # Arts, design, entertainment, sports, media
    "29": 19.0,  # Healthcare practitioners and technical
    "31": 28.8,  # Healthcare support
    "33": 9.7,   # Protective service
    "35": 28.5,  # Food preparation and serving
    "37": 33.8,  # Building and grounds cleaning and maintenance
    "39": 16.7,  # Personal care and service
    "41": 12.1,  # Sales and related
    "43": 11.2,  # Office and administrative support
    "45": 42.4,  # Farming, fishing, and forestry
    "47": 30.2,  # Construction and extraction
    "49": 15.6,  # Installation, maintenance, and repair
    "51": 21.8,  # Production
    "53": 20.3,  # Transportation and material moving
}

# Education-partisan gradient (Pew Research Center, 2024)
# College grads lean +13 Dem, non-college lean +6 Rep
# We express as D-R margin: positive = Dem lean, negative = Rep lean
EDU_PARTISAN_COLLEGE = 0.13    # +13% Dem margin for bachelor's+
EDU_PARTISAN_NO_COLLEGE = -0.06  # +6% Rep margin for no bachelor's
