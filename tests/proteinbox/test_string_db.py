import respx
import httpx
from proteinbox.tools.string_db import STRINGTool

MOCK_STRING = [
    {
        "preferredName_A": "TP53",
        "preferredName_B": "MDM2",
        "score": 0.999,
        "nscore": 0, "fscore": 0, "pscore": 0,
        "ascore": 0, "escore": 0.95, "dscore": 0.9, "tscore": 0.95,
    },
    {
        "preferredName_A": "TP53",
        "preferredName_B": "CDKN1A",
        "score": 0.998,
        "nscore": 0, "fscore": 0, "pscore": 0,
        "ascore": 0, "escore": 0.9, "dscore": 0.85, "tscore": 0.9,
    },
]


@respx.mock
def test_string_success():
    respx.get("https://string-db.org/api/json/network").mock(
        return_value=httpx.Response(200, json=MOCK_STRING)
    )
    result = STRINGTool().run(protein_name="TP53")
    assert result.success is True
    assert result.data["partner_count"] == 2
    names = [p["partner"] for p in result.data["partners"]]
    assert "MDM2" in names
    assert "CDKN1A" in names


@respx.mock
def test_string_no_results():
    respx.get("https://string-db.org/api/json/network").mock(
        return_value=httpx.Response(200, json=[])
    )
    result = STRINGTool().run(protein_name="NOTAPROTEIN")
    assert result.success is False
