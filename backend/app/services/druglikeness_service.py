class DrugLikenessService:

    @staticmethod
    def evaluate(descriptors):

        if descriptors is None:
            return None

        mw = descriptors["molecular_weight"]
        logp = descriptors["logp"]
        hba = descriptors["hba"]
        hbd = descriptors["hbd"]
        tpsa = descriptors["tpsa"]
        rot = descriptors["rotatable_bonds"]
        qed = descriptors["qed"]

        # -----------------------------
        # Lipinski Rule of Five
        # -----------------------------

        lipinski = {
            "mw": mw <= 500,
            "logp": logp <= 5,
            "hba": hba <= 10,
            "hbd": hbd <= 5
        }

        lipinski_pass = all(lipinski.values())

        # -----------------------------
        # Veber Rule
        # -----------------------------

        veber = {
            "tpsa": tpsa <= 140,
            "rotatable_bonds": rot <= 10
        }

        veber_pass = all(veber.values())

        # -----------------------------
        # Drug-likeness Score
        # -----------------------------

        score = 0

        if lipinski["mw"]:
            score += 20

        if lipinski["logp"]:
            score += 20

        if lipinski["hba"]:
            score += 15

        if lipinski["hbd"]:
            score += 15

        if veber["tpsa"]:
            score += 15

        if veber["rotatable_bonds"]:
            score += 15

        score = round(score * qed, 2)

        # -----------------------------
        # Rating
        # -----------------------------

        if score >= 80:
            rating = "Excellent"

        elif score >= 60:
            rating = "Good"

        elif score >= 40:
            rating = "Moderate"

        else:
            rating = "Poor"

        return {

            "lipinski_pass": lipinski_pass,

            "veber_pass": veber_pass,

            "lipinski_details": lipinski,

            "veber_details": veber,

            "druglikeness_score": score,

            "rating": rating
        }