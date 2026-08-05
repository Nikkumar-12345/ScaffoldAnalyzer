import requests


class UniProtService:

    BASE_URL = "https://rest.uniprot.org/uniprotkb"

    @staticmethod
    def get_protein(uniprot_id: str):

        url = f"{UniProtService.BASE_URL}/{uniprot_id}.json"

        response = requests.get(url)

        if response.status_code != 200:
            raise Exception("Invalid UniProt ID")

        data = response.json()

        protein_name = (
            data["proteinDescription"]
            ["recommendedName"]
            ["fullName"]
            ["value"]
        )

        organism = data["organism"]["scientificName"]

        gene_name = ""

        if "genes" in data and len(data["genes"]) > 0:
            gene_name = data["genes"][0]["geneName"]["value"]

        return {
            "uniprot_id": uniprot_id,
            "protein_name": protein_name,
            "gene_name": gene_name,
            "organism": organism
        }