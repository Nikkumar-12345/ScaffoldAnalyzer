from app.services.descriptor_service import DescriptorService
from app.services.druglikeness_service import DrugLikenessService
from app.services.ranking_service import RankingService

smiles = "CC(=O)NC1=CC=C(C=C1)O"

desc = DescriptorService.calculate(smiles)

drug = DrugLikenessService.evaluate(desc)

rank = RankingService.calculate(

    median_pic50=8.6,

    occurrences=430,

    descriptors=desc,

    druglikeness=drug,

    max_occurrences=600

)

print(rank)