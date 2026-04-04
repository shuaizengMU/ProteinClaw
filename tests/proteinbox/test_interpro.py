import respx
import httpx
from proteinbox.tools.interpro import InterProTool

MOCK_INTERPRO = {
    "results": [
        {
            "metadata": {
                "accession": "IPR011615",
                "name": "p53-like transcription factor",
                "type": "domain",
                "source_database": "interpro",
            },
            "proteins": [
                {
                    "entry_protein_locations": [
                        {"fragments": [{"start": 94, "end": 292}]}
                    ]
                }
            ],
        }
    ]
}


@respx.mock
def test_interpro_success():
    respx.get(
        "https://www.ebi.ac.uk/interpro/api/entry/interpro/protein/UniProt/P04637"
    ).mock(return_value=httpx.Response(200, json=MOCK_INTERPRO))
    result = InterProTool().run(uniprot_id="P04637")
    assert result.success is True
    assert result.data["domain_count"] == 1
    assert result.data["domains"][0]["name"] == "p53-like transcription factor"
    assert result.data["domains"][0]["locations"][0]["start"] == 94


@respx.mock
def test_interpro_not_found():
    respx.get(
        "https://www.ebi.ac.uk/interpro/api/entry/interpro/protein/UniProt/XXXXXX"
    ).mock(return_value=httpx.Response(404))
    result = InterProTool().run(uniprot_id="XXXXXX")
    assert result.success is False
