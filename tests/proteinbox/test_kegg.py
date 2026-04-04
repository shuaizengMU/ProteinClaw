import respx
import httpx
from proteinbox.tools.kegg import KEGGTool, KEGG_BASE


@respx.mock
def test_kegg_direct_id():
    respx.get(f"{KEGG_BASE}/link/pathway/hsa:7157").mock(
        return_value=httpx.Response(
            200,
            text="hsa:7157\tpath:hsa04115\nhsa:7157\tpath:hsa05200\n",
        )
    )
    respx.get(f"{KEGG_BASE}/get/hsa04115").mock(
        return_value=httpx.Response(200, text="NAME        p53 signaling pathway\nDESCRIPTION ...\n")
    )
    respx.get(f"{KEGG_BASE}/get/hsa05200").mock(
        return_value=httpx.Response(200, text="NAME        Pathways in cancer\nDESCRIPTION ...\n")
    )
    result = KEGGTool().run(query="hsa:7157")
    assert result.success is True
    assert result.data["pathway_count"] == 2
    assert any("p53" in p["name"].lower() for p in result.data["pathways"])


@respx.mock
def test_kegg_search():
    respx.get(f"{KEGG_BASE}/find/genes/TP53 human").mock(
        return_value=httpx.Response(200, text="hsa:7157\tTP53; tumor protein p53\n")
    )
    respx.get(f"{KEGG_BASE}/link/pathway/hsa:7157").mock(
        return_value=httpx.Response(200, text="hsa:7157\tpath:hsa04115\n")
    )
    respx.get(f"{KEGG_BASE}/get/hsa04115").mock(
        return_value=httpx.Response(200, text="NAME        p53 signaling pathway\n")
    )
    result = KEGGTool().run(query="TP53 human")
    assert result.success is True
    assert result.data["gene_id"] == "hsa:7157"


@respx.mock
def test_kegg_not_found():
    respx.get(f"{KEGG_BASE}/find/genes/NOTAREALGENE").mock(
        return_value=httpx.Response(200, text="")
    )
    result = KEGGTool().run(query="NOTAREALGENE")
    assert result.success is False
