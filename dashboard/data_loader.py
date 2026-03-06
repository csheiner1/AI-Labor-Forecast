"""Load workbook data for the Flask dashboard.

Reads from 4 Results and 6 Social Impact tabs on startup.
Caches in memory for fast page rendering.
"""
import openpyxl
import os

from social_impact.config import WORKBOOK


class DataStore:
    """In-memory cache of workbook data for the dashboard."""

    def __init__(self):
        self.results = []       # 4 Results tab rows
        self.social = []        # 6 Social Impact tab rows
        self.soc_lookup = {}    # SOC -> merged dict of results + social
        self._displacement_data = None  # cached for transition API
        self._loaded = False

    def load(self):
        """Load data from workbook into memory."""
        if self._loaded:
            return

        wb = openpyxl.load_workbook(WORKBOOK, read_only=True, data_only=True)

        # Load 4 Results -- use iter_rows for read_only compatibility
        ws = wb["4 Results"]
        headers = None
        for row_vals in ws.iter_rows(max_col=27, values_only=True):
            if headers is None:
                headers = list(row_vals)
                continue
            soc = row_vals[0]
            if not soc:
                continue
            row = {}
            for c, h in enumerate(headers):
                if h:
                    row[h] = row_vals[c]
            self.results.append(row)

        # Load 6 Social Impact
        try:
            ws2 = wb["6 Social Impact"]
            headers2 = None
            for row_vals in ws2.iter_rows(max_col=19, values_only=True):
                if headers2 is None:
                    headers2 = list(row_vals)
                    continue
                soc = row_vals[0]
                if not soc:
                    continue
                row = {}
                for c, h in enumerate(headers2):
                    if h:
                        row[h] = row_vals[c]
                self.social.append(row)
        except KeyError:
            print("WARNING: '6 Social Impact' tab not found. Run social_impact/run.py first.")

        wb.close()

        # Build merged lookup -- for SOCs with multiple rows in Results,
        # keep the first row (which has the primary sector assignment)
        social_by_soc = {r["SOC_Code"]: r for r in self.social}
        for r in self.results:
            soc = r.get("SOC_Code")
            if not soc or soc in self.soc_lookup:
                continue
            merged = dict(r)
            if soc in social_by_soc:
                merged.update(social_by_soc[soc])
            self.soc_lookup[soc] = merged

        self._loaded = True
        print(f"DataStore loaded: {len(self.results)} results, {len(self.social)} social impact rows, "
              f"{len(self.soc_lookup)} unique SOCs")

    def get_all(self):
        """Return all SOC records as merged dicts."""
        self.load()
        return list(self.soc_lookup.values())

    def get_soc(self, soc_code):
        """Return one SOC record."""
        self.load()
        return self.soc_lookup.get(soc_code)

    def get_sectors(self):
        """Return list of unique sectors."""
        self.load()
        return sorted(set(r.get("Sector", "") for r in self.results if r.get("Sector")))

    def get_displacement_data(self):
        """Return displacement_data dict for transition API, cached after first call."""
        self.load()
        if self._displacement_data is None:
            self._displacement_data = {}
            for soc, rec in self.soc_lookup.items():
                self._displacement_data[soc] = {
                    "title": rec.get("Job_Title") or rec.get("Custom_Title", ""),
                    "d_mod_low": rec.get("d_mod_low", 0),
                    "employment_K": rec.get("Employment_2024_K", 0),
                }
        return self._displacement_data

    def get_wage_quintiles(self):
        """Return SOC codes grouped by wage quintile."""
        self.load()
        wages = [(r["SOC_Code"], r.get("Median_Wage", 0) or 0) for r in self.soc_lookup.values()]
        wages.sort(key=lambda x: x[1])
        n = len(wages)
        quintile_size = n // 5
        quintiles = {}
        labels = ["Q1 (lowest)", "Q2", "Q3", "Q4", "Q5 (highest)"]
        for i, label in enumerate(labels):
            start = i * quintile_size
            end = start + quintile_size if i < 4 else n
            quintiles[label] = [w[0] for w in wages[start:end]]
        return quintiles


# Singleton instance
store = DataStore()
