from app.services.descriptor_service import DescriptorService
from app.services.druglikeness_service import DrugLikenessService

smiles = "CC(=O)NC1=CC=C(C=C1)O"

desc = DescriptorService.calculate(smiles)

drug = DrugLikenessService.evaluate(desc)

print(desc)

print()

print(drug)