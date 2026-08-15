import time
import requests
import pandas as pd

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class ChEMBLService:

    BASE_URL = "https://www.ebi.ac.uk/chembl/api/data"

    # Only keep fields actually needed by the application
    REQUIRED_COLUMNS = [
        "activity_id",
        "molecule_chembl_id",
        "canonical_smiles",
        "standard_value",
        "standard_units",
        "standard_relation",
        "standard_type",
        "pchembl_value",
        "assay_chembl_id",
        "document_chembl_id"
    ]

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
    # SAFE GET REQUEST
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
    # GET TARGET
    # --------------------------------------------------

    def get_target(self, uniprot_id):

        url = (
            self.BASE_URL
            + "/target.json"
            + "?target_components__accession="
            + uniprot_id.strip()
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

        if not targets:

            raise Exception(
                "No target found for this UniProt ID."
            )

        for target in targets:

            if (
                target.get("target_type") == "SINGLE PROTEIN"
                and target.get("organism") == "Homo sapiens"
            ):

                return target

        raise Exception(
            "No Human Single Protein target found."
        )

    # --------------------------------------------------
    # COMPACT ACTIVITY RECORD
    # --------------------------------------------------

    def compact_activity(self, activity):

        return {
            column: activity.get(column)
            for column in self.REQUIRED_COLUMNS
        }

    # --------------------------------------------------
    # DOWNLOAD ACTIVITIES
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

        # Store only compact records instead of complete
        # large ChEMBL activity dictionaries.
        rows = []

        # Keep only one valid record per molecule.
        seen_molecules = set()

        page_number = 1
        total_received = 0
        total_kept = 0

        while url:

            print(
                f"Downloading page {page_number}"
            )

            response = self.safe_get(
                url,
                timeout=120
            )

            # Parse the JSON only once
            data = response.json()

            activities = data.get(
                "activities",
                []
            )

            total_received += len(activities)

            # ------------------------------------------
            # FILTER AND DEDUPLICATE IMMEDIATELY
            # ------------------------------------------

            for activity in activities:

                molecule_id = activity.get(
                    "molecule_chembl_id"
                )

                smiles = activity.get(
                    "canonical_smiles"
                )

                standard_value = activity.get(
                    "standard_value"
                )

                standard_relation = activity.get(
                    "standard_relation"
                )

                # Skip invalid records
                if not molecule_id:
                    continue

                if not smiles:
                    continue

                if standard_value is None:
                    continue

                if standard_relation != "=":
                    continue

                # Keep only one record per molecule
                if molecule_id in seen_molecules:
                    continue

                seen_molecules.add(
                    molecule_id
                )

                # Keep only required columns
                rows.append(
                    self.compact_activity(activity)
                )

                total_kept += 1

            print(
                f"Page {page_number} complete | "
                f"Received: {total_received} | "
                f"Unique molecules kept: {total_kept}"
            )

            # Get next page BEFORE releasing data
            page_meta = data.get(
                "page_meta",
                {}
            )

            next_page = page_meta.get(
                "next"
            )

            # Release references from this page
            activities = None
            page_meta = None
            data = None
            response = None

            # ------------------------------------------
            # MOVE TO NEXT PAGE
            # ------------------------------------------

            if next_page:

                if next_page.startswith("http"):

                    url = next_page

                else:

                    url = (
                        "https://www.ebi.ac.uk"
                        + next_page
                    )

                page_number += 1

                # Small delay between API requests
                time.sleep(0.3)

            else:

                url = None

        # ----------------------------------------------
        # VALIDATE RESULTS
        # ----------------------------------------------

        if not rows:

            raise Exception(
                "No valid IC50 activity records were "
                "returned by ChEMBL."
            )

        print(
            f"Download complete | "
            f"Total API records: {total_received} | "
            f"Unique valid molecules: {total_kept}"
        )

        return pd.DataFrame(
            rows,
            columns=self.REQUIRED_COLUMNS
        )