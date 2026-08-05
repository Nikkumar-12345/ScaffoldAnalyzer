import requests
import pandas as pd
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class ChEMBLService:

    BASE_URL = "https://www.ebi.ac.uk/chembl/api/data"

    def __init__(self):

        self.session = requests.Session()

        retry = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )

        adapter = HTTPAdapter(max_retries=retry)

        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def get_target(self, uniprot_id):

        url = (
            self.BASE_URL
            + "/target.json"
            + "?target_components__accession="
            + uniprot_id
        )

        response = self.session.get(url, timeout=60)

        response.raise_for_status()

        data = response.json()

        targets = data.get("targets", [])

        if len(targets) == 0:
            raise Exception("No target found.")

        for target in targets:

            if (
                target["target_type"] == "SINGLE PROTEIN"
                and target["organism"] == "Homo sapiens"
            ):

                return target

        raise Exception("No Human Single Protein target found.")

    def download_activities(self, chembl_target):

        url = (
            self.BASE_URL
            + "/activity.json"
            + "?target_chembl_id="
            + chembl_target
            + "&standard_type=IC50"
            + "&limit=1000"
        )

        all_rows = []

        while url:

            print("Downloading:", url)

            response = self.session.get(
                url,
                timeout=120
            )

            response.raise_for_status()

            data = response.json()

            all_rows.extend(
                data["activities"]
            )

            next_page = data["page_meta"]["next"]

            if next_page:

                if next_page.startswith("http"):

                    url = next_page

                else:

                    url = "https://www.ebi.ac.uk" + next_page

            else:

                url = None

        return pd.DataFrame(all_rows)