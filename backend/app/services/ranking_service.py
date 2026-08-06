class RankingService:

    @staticmethod
    def calculate(
        median_pic50,
        occurrences,
        descriptors,
        druglikeness,
        max_occurrences
    ):

        if descriptors is None or druglikeness is None:
            return None

        # -----------------------------
        # Potency Score (0-30)
        # -----------------------------

        if median_pic50 is None:
            potency_score = 0
        else:
            potency_score = min((median_pic50 / 10.0) * 30.0, 30.0)

        # -----------------------------
        # Drug-likeness Score (0-30)
        # -----------------------------

        drug_score = min(
            druglikeness["druglikeness_score"] * 0.30,
            30.0
        )

        # -----------------------------
        # Frequency Score (0-20)
        # -----------------------------

        if max_occurrences == 0:
            frequency_score = 0
        else:
            frequency_score = (
                occurrences / max_occurrences
            ) * 20.0

        # -----------------------------
        # Complexity Score (0-20)
        # -----------------------------

        bertz = descriptors["bertz_complexity"]

        if bertz < 200:
            complexity_score = 20

        elif bertz < 400:
            complexity_score = 16

        elif bertz < 600:
            complexity_score = 12

        elif bertz < 800:
            complexity_score = 8

        else:
            complexity_score = 4

        # -----------------------------
        # Overall Score
        # -----------------------------

        overall_score = round(

            potency_score +

            drug_score +

            frequency_score +

            complexity_score,

            2

        )

        # -----------------------------
        # Grade
        # -----------------------------

        if overall_score >= 90:

            grade = "A+"

            label = "Excellent Lead"

        elif overall_score >= 80:

            grade = "A"

            label = "Highly Promising"

        elif overall_score >= 70:

            grade = "B"

            label = "Promising"

        elif overall_score >= 60:

            grade = "C"

            label = "Moderate"

        else:

            grade = "D"

            label = "Weak"

        return {

            "overall_score": overall_score,

            "grade": grade,

            "label": label,

            "potency_score": round(potency_score, 2),

            "druglikeness_score": round(drug_score, 2),

            "frequency_score": round(frequency_score, 2),

            "complexity_score": round(complexity_score, 2)

        }