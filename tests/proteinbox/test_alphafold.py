import respx
import httpx
from proteinbox.tools.alphafold import AlphaFoldTool

MOCK_AF = [
    {
        "pdbUrl": "https://alphafold.ebi.ac.uk/files/AF-P04637-F1-model_v4.pdb",
        "cifUrl": "https://alphafold.ebi.ac.uk/files/AF-P04637-F1-model_v4.cif",
        "globalMetricValue": 75.5,
        "uniprotStart": 1,
        "uniprotEnd": 393,
        "latestVersion": 4,
        "gene": "TP53",
        "organismScientificName": "Homo sapiens",
    }
]


@respx.mock
def test_alphafold_success():
    respx.get("https://alphafold.ebi.ac.uk/api/prediction/P04637").mock(
        return_value=httpx.Response(200, json=MOCK_AF)
    )
    result = AlphaFoldTool().run(uniprot_id="P04637")
    assert result.success is True
    assert result.data["uniprot_id"] == "P04637"
    assert result.data["mean_plddt"] == 75.5
    assert result.data["sequence_length"] == 393
    assert "High" in result.display


@respx.mock
def test_alphafold_not_found():
    respx.get("https://alphafold.ebi.ac.uk/api/prediction/XXXXXX").mock(
        return_value=httpx.Response(404)
    )
    result = AlphaFoldTool().run(uniprot_id="XXXXXX")
    assert result.success is False
    assert "no alphafold prediction found" in result.error.lower()
