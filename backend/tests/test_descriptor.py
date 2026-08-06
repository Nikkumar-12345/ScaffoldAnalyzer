from app.services.descriptor_service import DescriptorService

smiles = "CC(=O)NC1=CC=CC=C1"

result = DescriptorService.calculate(smiles)

print(result)