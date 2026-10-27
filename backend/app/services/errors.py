import re


class AnalysisError(Exception):
    """
    An error with a user-facing message and an HTTP status code.

    It subclasses Exception, so any existing code that catches
    Exception keeps working exactly as before.
    """

    def __init__(self, code, message, status_code=400):

        super().__init__(message)

        self.code = code
        self.message = message
        self.status_code = status_code

    def to_dict(self):

        return {
            "code": self.code,
            "message": self.message
        }


# UniProt accession format (https://www.uniprot.org/help/accession_numbers)
# with an optional isoform suffix such as P00533-2.
UNIPROT_PATTERN = re.compile(
    r"^(?:[OPQ][0-9][A-Z0-9]{3}[0-9]"
    r"|[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})"
    r"(?:-\d+)?$"
)


def normalize_uniprot_id(uniprot_id):

    if uniprot_id is None:
        return ""

    return str(uniprot_id).strip().upper()


def is_valid_uniprot_format(uniprot_id):

    return bool(UNIPROT_PATTERN.match(uniprot_id))


def invalid_format_error(uniprot_id):

    return AnalysisError(
        "invalid_uniprot_id",
        f"'{uniprot_id}' is not a valid UniProt ID. UniProt IDs look "
        "like P00533 or Q9Y6K9 (6 or 10 letters and digits). Please "
        "check the ID and try again.",
        400
    )


def not_found_error(uniprot_id):

    return AnalysisError(
        "uniprot_id_not_found",
        f"UniProt ID '{uniprot_id}' was not found. It is not in the "
        "local ChEMBL database and ChEMBL has no target for it. Please "
        "check the ID (for example P00533 for EGFR) and try again.",
        404
    )
