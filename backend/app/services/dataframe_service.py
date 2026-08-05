import pandas as pd


class DataFrameService:

    @staticmethod
    def clean_activity_dataframe(df: pd.DataFrame):

        if df.empty:
            return df

        columns = [
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

        existing = [c for c in columns if c in df.columns]

        df = df[existing]

        if "canonical_smiles" in df.columns:
            df = df[df["canonical_smiles"].notna()]

        if "standard_value" in df.columns:
            df = df[df["standard_value"].notna()]

        if "standard_relation" in df.columns:
            df = df[df["standard_relation"] == "="]

        df = df.drop_duplicates(
            subset=["molecule_chembl_id"]
        )

        df.reset_index(
            drop=True,
            inplace=True
        )

        return df