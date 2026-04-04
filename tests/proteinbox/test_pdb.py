import respx
import httpx
from proteinbox.tools.pdb import PDBTool

MOCK_PDB = {
    "struct": {"title": "CRYSTAL STRUCTURE OF P53 CORE DOMAIN"},
    "exptl": [{"method": "X-RAY DIFFRACTION"}],
    "rcsb_entry_info": {
        "resolution_combined": [2.2],
        "polymer_entity_count": 4,
        "nonpolymer_bound_components": ["ZN"],
    },
    "rcsb_accession_info": {"deposit_date": "1994-08-25"},
    "rcsb_entity_source_organism": [
        {"ncbi_scientific_name": "Homo sapiens"}
    ],
}


@respx.mock
def test_pdb_success():
    respx.get("https://data.rcsb.org/rest/v1/core/entry/1TUP").mock(
        return_value=httpx.Response(200, json=MOCK_PDB)
    )
    result = PDBTool().run(pdb_id="1tup")
    assert result.success is True
    assert result.data["pdb_id"] == "1TUP"
    assert result.data["method"] == "X-RAY DIFFRACTION"
    assert result.data["resolution_angstrom"] == 2.2
    assert result.data["organism"] == "Homo sapiens"


@respx.mock
def test_pdb_not_found():
    respx.get("https://data.rcsb.org/rest/v1/core/entry/ZZZZ").mock(
        return_value=httpx.Response(404)
    )
    result = PDBTool().run(pdb_id="ZZZZ")
    assert result.success is False
    assert "404" in result.error
