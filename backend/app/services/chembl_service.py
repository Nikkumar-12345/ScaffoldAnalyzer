import time
import requests
import pandas as pd

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class ChEMBLService:

    BASE_URL = "https://www.ebi.ac.uk/chembl/api/data"

    def __init__(self):

        self.session = requests.Session()

        retry = Retry(
            total=8,
            connect=8,
            read=8,
            status=8,

            backoff_factor=2,

            status_forcelist=[
                429,
                500,
                502,
                503,
                504
            ],

            allowed_methods=["GET"],

            raise_on_status=False
        )

        adapter = HTTPAdapter(
            max_retries=retry
        )

        self.session.mount(
            "https://",
            adapter
        )

        self.session.mount(
            "http://",
            adapter
        )

    # --------------------------------------------------
    # Safe GET request
    # --------------------------------------------------

    def safe_get(self, url, timeout=120):

        try:

            response = self.session.get(
                url,
                timeout=timeout
            )

            if response.status_code >= 500:

                raise Exception(
                    f"ChEMBL server error: "
                    f"{response.status_code}"
                )

            response.raise_for_status()

            return response

        except requests.exceptions.RequestException as e:

            raise Exception(
                "Could not retrieve data from ChEMBL. "
                "The ChEMBL API may be temporarily unavailable. "
                f"Details: {str(e)}"
            )

    # --------------------------------------------------
    # Get Target
    # --------------------------------------------------

    def get_target(self, uniprot_id):

        url = (
            self.BASE_URL
            + "/target.json"
            + "?target_components__accession="
            + uniprot_id
        )

        response = self.safe_get(
            url,
            timeout=60
        )

        data = response.json()

        targets = data.get(
            "targets",
            []
        )

        if len(targets) == 0:

            raise Exception(
                "No target found for this UniProt ID."
            )

        for target in targets:

            if (
                target.get("target_type")
                == "SINGLE PROTEIN"

                and

                target.get("organism")
                == "Homo sapiens"
            ):

                return target

        raise Exception(
            "No Human Single Protein target found."
        )

    # --------------------------------------------------
    # Download Activities
    # --------------------------------------------------

    def download_activities(self, chembl_target):

        url = (
            self.BASE_URL
            + "/activity.json"
            + "?target_chembl_id="
            + chembl_target
            + "&standard_type=IC50"
            + "&limit=500"
        )

        all_rows = []

        page_number = 1

        while url:

            print(
                f"Downloading page {page_number}"
            )

            response = self.safe_get(
                url,
                timeout=120
            )

            data = response.json()

            activities = data.get(
                "activities",
                []
            )

            all_rows.extend(
                activities
            )

            page_meta = data.get(
                "page_meta",
                {}
            )

            next_page = page_meta.get(
                "next"
            )

            if next_page:

                if next_page.startswith("http"):

                    url = next_page

                else:

                    url = (
                        "https://www.ebi.ac.uk"
                        + next_page
                    )

                page_number += 1

                # Small delay between pages.
                # This reduces the chance of repeatedly
                # hitting the ChEMBL server too aggressively.
                time.sleep(0.5)

            else:

                url = None

        if len(all_rows) == 0:

            raise Exception(
                "No IC50 activity records were returned "
                "by ChEMBL."
            )

        return pd.DataFrame(
            all_rows
        )