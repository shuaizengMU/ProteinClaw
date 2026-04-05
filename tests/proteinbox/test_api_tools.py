"""Tests for api_tools batch: chembl, clinvar, disgenet, ensembl, expasy,
ncbi_gene, omim, phosphosite, reactome."""
import respx
import httpx
import pytest

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
CHEMBL_BASE = "https://www.ebi.ac.uk/chembl/api/data"


# ── ChEMBL ────────────────────────────────────────────────────────────────────

from proteinbox.api_tools.chembl import ChEMBLTool


@respx.mock
def test_chembl_success():
    respx.get(f"{CHEMBL_BASE}/target/search.json").mock(
        return_value=httpx.Response(200, json={
            "targets": [{"target_chembl_id": "CHEMBL203", "pref_name": "EGFR", "target_type": "SINGLE PROTEIN"}]
        })
    )
    respx.get(f"{CHEMBL_BASE}/mechanism.json").mock(
        return_value=httpx.Response(200, json={
            "mechanisms": [{"molecule_chembl_id": "CHEMBL1421", "mechanism_of_action": "Inhibitor", "action_type": "INHIBITOR"}]
        })
    )
    respx.get(f"{CHEMBL_BASE}/molecule/CHEMBL1421.json").mock(
        return_value=httpx.Response(200, json={
            "pref_name": "GEFITINIB", "max_phase": 4, "molecule_type": "Small molecule", "first_approval": 2003,
        })
    )
    respx.get(f"{CHEMBL_BASE}/activity.json").mock(
        return_value=httpx.Response(200, json={"page_meta": {"total_count": 5000}})
    )
    result = ChEMBLTool().run(query="EGFR")
    assert result.success is True
    assert result.data["target_chembl_id"] == "CHEMBL203"
    assert len(result.data["drugs"]) == 1
    assert result.data["drugs"][0]["molecule_name"] == "GEFITINIB"
    assert result.data["total_bioactivities"] == 5000


@respx.mock
def test_chembl_no_target():
    respx.get(f"{CHEMBL_BASE}/target/search.json").mock(
        return_value=httpx.Response(200, json={"targets": []})
    )
    result = ChEMBLTool().run(query="NONEXISTENT")
    assert result.success is False


# ── ClinVar ───────────────────────────────────────────────────────────────────

from proteinbox.api_tools.clinvar import ClinVarTool


@respx.mock
def test_clinvar_success():
    respx.get(f"{EUTILS}/esearch.fcgi").mock(
        return_value=httpx.Response(200, json={
            "esearchresult": {"count": "50", "idlist": ["123456", "789012"]}
        })
    )
    respx.get(f"{EUTILS}/esummary.fcgi").mock(
        return_value=httpx.Response(200, json={
            "result": {
                "123456": {
                    "title": "BRCA1 c.5266dupC",
                    "clinical_significance": {"description": "Pathogenic", "review_status": "criteria provided"},
                    "trait_set": [{"trait_name": "Breast cancer"}],
                    "variation_set": [{"variation_type": "Insertion"}],
                },
                "789012": {
                    "title": "BRCA1 c.68_69delAG",
                    "clinical_significance": {"description": "Pathogenic", "review_status": "criteria provided"},
                    "trait_set": [],
                    "variation_set": [],
                },
            }
        })
    )
    result = ClinVarTool().run(gene="BRCA1")
    assert result.success is True
    assert result.data["total"] == 50
    assert len(result.data["variants"]) == 2
    assert result.data["variants"][0]["clinical_significance"] == "Pathogenic"


@respx.mock
def test_clinvar_no_results():
    respx.get(f"{EUTILS}/esearch.fcgi").mock(
        return_value=httpx.Response(200, json={"esearchresult": {"count": "0", "idlist": []}})
    )
    result = ClinVarTool().run(gene="FAKEGENE")
    assert result.success is False


# ── DisGeNET ──────────────────────────────────────────────────────────────────

from proteinbox.api_tools.disgenet import DisGeNETTool

DISGENET_BASE = "https://www.disgenet.org/api"


@respx.mock
def test_disgenet_success():
    respx.get(f"{DISGENET_BASE}/gda/gene/TP53").mock(
        return_value=httpx.Response(200, json=[
            {"gene_symbol": "TP53", "disease_name": "Li-Fraumeni syndrome", "score": 0.9, "ei": 1.0, "el": "high", "pmid_count": 200},
            {"gene_symbol": "TP53", "disease_name": "Breast Neoplasms", "score": 0.8, "ei": 0.9, "el": "high", "pmid_count": 500},
        ])
    )
    result = DisGeNETTool().run(query="TP53")
    assert result.success is True
    assert result.data["total"] == 2
    assert result.data["associations"][0]["disease_name"] == "Li-Fraumeni syndrome"


@respx.mock
def test_disgenet_api_unavailable_uses_ncbi_fallback():
    """When DisGeNET returns 403, fall back to NCBI."""
    respx.get(f"{DISGENET_BASE}/gda/gene/TP53").mock(
        return_value=httpx.Response(403)
    )
    # Also mock the search endpoint in case DisGeNET tries it
    respx.get(f"{DISGENET_BASE}/gda/search/TP53").mock(
        return_value=httpx.Response(403)
    )
    # NCBI fallback
    respx.get(f"{EUTILS}/esearch.fcgi").mock(
        return_value=httpx.Response(200, json={"esearchresult": {"idlist": ["7157"]}})
    )
    respx.get(f"{EUTILS}/elink.fcgi").mock(
        return_value=httpx.Response(200, json={
            "linksets": [{"linksetdbs": [{"links": [163]}]}]
        })
    )
    respx.get(f"{EUTILS}/esummary.fcgi").mock(
        return_value=httpx.Response(200, json={
            "result": {"163": {"title": "TP53 — Li-Fraumeni syndrome"}}
        })
    )
    result = DisGeNETTool().run(query="TP53")
    assert result.success is True


# ── Ensembl ───────────────────────────────────────────────────────────────────

from proteinbox.api_tools.ensembl import EnsemblTool

ENSEMBL_BASE = "https://rest.ensembl.org"


@respx.mock
def test_ensembl_success():
    respx.get(f"{ENSEMBL_BASE}/lookup/symbol/human/TP53").mock(
        return_value=httpx.Response(200, json={
            "id": "ENSG00000141510",
            "display_name": "TP53",
            "description": "tumor protein p53",
            "biotype": "protein_coding",
            "species": "homo_sapiens",
            "assembly_name": "GRCh38",
            "seq_region_name": "17",
            "start": 7668421,
            "end": 7687550,
            "strand": -1,
            "Transcript": [
                {"id": "ENST00000269305", "display_name": "TP53-201", "biotype": "protein_coding", "is_canonical": 1, "length": 2629}
            ],
        })
    )
    respx.get(f"{ENSEMBL_BASE}/homology/id/ENSG00000141510").mock(
        return_value=httpx.Response(200, json={
            "data": [{"homologies": [
                {"target": {"species": "mus_musculus", "id": "ENSMUSG00000059552", "protein_id": "ENSMUSP00000062716", "perc_id": 77.0}},
            ]}]
        })
    )
    result = EnsemblTool().run(symbol="TP53")
    assert result.success is True
    assert result.data["gene_id"] == "ENSG00000141510"
    assert result.data["chromosome"] == "17"
    assert len(result.data["transcripts"]) == 1
    assert len(result.data["orthologs"]) == 1


@respx.mock
def test_ensembl_not_found():
    respx.get(f"{ENSEMBL_BASE}/lookup/symbol/human/FAKEGENE").mock(
        return_value=httpx.Response(400)
    )
    result = EnsemblTool().run(symbol="FAKEGENE")
    assert result.success is False


# ── ExPASy ProtParam (local, no HTTP) ─────────────────────────────────────────

from proteinbox.api_tools.expasy import ExPASyTool

TP53_SEQ = "MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPSQAMDDLMLSPDDIEQWFTEDPGPDEAPRMPEAAPPVAPAPAAPTPAAPAPAPSWPLSSSVPSQKTYPQGLDERRFLSHLNSTKTPTAKDNLVSSALNKCHFRHFKEPEDLNLPSTDRHTILETPKPVTLKIHKKKKLPFKELTRSQGPVNKTEDKFIMQIPFPDRSQNKGGTLEAFCTGFSAPAKVLQRFQYPVNMTYLPTLRDLAEAKGAQRFVKGAQALVLTSLDKSHGGGEQVTLGHSVAHQREIGVMRGGKIASSGVSEQVKLHRDGTQATQNIYGRKLPFCTAQVTHSHHLSAIRLPPFQHKTQCSIKSCTSLGGVEAAAVNSLTASPHHQLDSEQEVHRVHHPTLGSIIRDEQEKERLCRQGSQVSVKERLSPNIVHHLKHQAAEALQELRPASRQVPDPMSPQDPYLQAGQGGADYALQEGQEEERRLQEQRQRKGQGAQATQQGGRPGPSSVQLR"


def test_expasy_basic():
    result = ExPASyTool().run(sequence="MKTIIALSYIFCLVFA")
    assert result.success is True
    data = result.data
    assert data["length"] == 16
    assert isinstance(data["molecular_weight_da"], float)
    assert isinstance(data["isoelectric_point"], float)
    assert isinstance(data["gravy"], float)
    assert "signal_peptide" in data
    assert "composition" in data


def test_expasy_empty_sequence():
    result = ExPASyTool().run(sequence="")
    assert result.success is False


def test_expasy_tp53_stable():
    result = ExPASyTool().run(sequence=TP53_SEQ)
    assert result.success is True
    assert result.data["length"] == len(TP53_SEQ)


# ── NCBI Gene ─────────────────────────────────────────────────────────────────

from proteinbox.api_tools.ncbi_gene import NCBIGeneTool


@respx.mock
def test_ncbi_gene_success():
    respx.get(f"{EUTILS}/esearch.fcgi").mock(
        return_value=httpx.Response(200, json={
            "esearchresult": {"idlist": ["7157"]}
        })
    )
    respx.get(f"{EUTILS}/esummary.fcgi").mock(
        return_value=httpx.Response(200, json={
            "result": {
                "7157": {
                    "name": "TP53",
                    "description": "tumor protein p53",
                    "organism": {"scientificname": "Homo sapiens"},
                    "otheraliases": "LFS1, P53",
                    "summary": "This gene encodes a tumor suppressor protein.",
                    "chromosome": "17",
                    "maplocation": "17p13.1",
                }
            }
        })
    )
    result = NCBIGeneTool().run(query="TP53")
    assert result.success is True
    assert result.data[0]["symbol"] == "TP53"
    assert result.data[0]["chromosome"] == "17"


@respx.mock
def test_ncbi_gene_not_found():
    respx.get(f"{EUTILS}/esearch.fcgi").mock(
        return_value=httpx.Response(200, json={"esearchresult": {"idlist": []}})
    )
    result = NCBIGeneTool().run(query="FAKEGENE99")
    assert result.success is False


# ── OMIM ──────────────────────────────────────────────────────────────────────

from proteinbox.api_tools.omim import OMIMTool


@respx.mock
def test_omim_success():
    # Step 1: gene search
    respx.get(f"{EUTILS}/esearch.fcgi").mock(
        return_value=httpx.Response(200, json={"esearchresult": {"idlist": ["672"]}})
    )
    # Step 2: elink gene -> omim
    respx.get(f"{EUTILS}/elink.fcgi").mock(
        return_value=httpx.Response(200, json={
            "linksets": [{"linksetdbs": [{"links": [113705, 604370]}]}]
        })
    )
    # Step 3: omim summary
    respx.get(f"{EUTILS}/esummary.fcgi").mock(
        return_value=httpx.Response(200, json={
            "result": {
                "113705": {"title": "BRCA1, BREAST CANCER 1"},
                "604370": {"title": "BREAST-OVARIAN CANCER SUSCEPTIBILITY"},
            }
        })
    )
    result = OMIMTool().run(gene="BRCA1")
    assert result.success is True
    assert len(result.data["diseases"]) == 2
    assert result.data["diseases"][0]["omim_id"] == "113705"


@respx.mock
def test_omim_no_gene():
    respx.get(f"{EUTILS}/esearch.fcgi").mock(
        return_value=httpx.Response(200, json={"esearchresult": {"idlist": []}})
    )
    result = OMIMTool().run(gene="FAKEGENE")
    assert result.success is False


# ── PhosphoSite (UniProt PTMs) ────────────────────────────────────────────────

from proteinbox.api_tools.phosphosite import PhosphoSiteTool

UNIPROT_P04637 = {
    "proteinDescription": {
        "recommendedName": {"fullName": {"value": "Cellular tumor antigen p53"}}
    },
    "features": [
        {
            "type": "Modified residue",
            "location": {"start": {"value": 6}, "end": {"value": 6}},
            "description": "Phosphoserine",
            "evidences": [{"code": "ECO:0000269"}],
        },
        {
            "type": "Modified residue",
            "location": {"start": {"value": 15}, "end": {"value": 15}},
            "description": "Phosphoserine; by ATM",
            "evidences": [{"code": "ECO:0000269"}],
        },
    ],
    "comments": [
        {
            "commentType": "PTM",
            "texts": [{"value": "Phosphorylated by multiple kinases including ATM, ATR, CHEK1, CHEK2."}],
        }
    ],
}


@respx.mock
def test_phosphosite_success():
    respx.get("https://rest.uniprot.org/uniprotkb/P04637.json").mock(
        return_value=httpx.Response(200, json=UNIPROT_P04637)
    )
    result = PhosphoSiteTool().run(accession_id="P04637")
    assert result.success is True
    assert result.data["total_ptms"] == 2
    assert "Modified residue" in result.data["type_summary"]
    assert len(result.data["ptm_comments"]) == 1


@respx.mock
def test_phosphosite_not_found():
    respx.get("https://rest.uniprot.org/uniprotkb/XXXXX.json").mock(
        return_value=httpx.Response(404)
    )
    result = PhosphoSiteTool().run(accession_id="XXXXX")
    assert result.success is False


# ── Reactome ──────────────────────────────────────────────────────────────────

from proteinbox.api_tools.reactome import ReactomeTool

REACTOME_BASE = "https://reactome.org/ContentService"

MOCK_PATHWAYS = [
    {
        "stId": "R-HSA-5633007",
        "displayName": "Regulation of TP53 Degradation",
        "species": [{"displayName": "Homo sapiens"}],
        "hasDiagram": True,
    },
    {
        "stId": "R-HSA-3700989",
        "displayName": "Transcriptional Regulation by Small Molecules",
        "species": [{"displayName": "Homo sapiens"}],
        "hasDiagram": False,
    },
]


@respx.mock
def test_reactome_uniprot_success():
    respx.get(f"{REACTOME_BASE}/data/pathways/low/entity/UniProt:P04637").mock(
        return_value=httpx.Response(200, json=MOCK_PATHWAYS)
    )
    result = ReactomeTool().run(query="P04637")
    assert result.success is True
    assert result.data["total"] == 2
    assert result.data["pathways"][0]["stable_id"] == "R-HSA-5633007"
    assert result.data["pathways"][0]["has_diagram"] is True


@respx.mock
def test_reactome_gene_symbol_fallback():
    """UniProt path fails; falls back to search endpoint."""
    respx.get(f"{REACTOME_BASE}/data/pathways/low/entity/UniProt:TP53").mock(
        return_value=httpx.Response(404)
    )
    respx.get(f"{REACTOME_BASE}/search/query").mock(
        return_value=httpx.Response(200, json={
            "results": [{"entries": [{"stId": "R-HSA-3700989"}]}]
        })
    )
    respx.get(f"{REACTOME_BASE}/data/pathways/low/entity/R-HSA-3700989").mock(
        return_value=httpx.Response(200, json=MOCK_PATHWAYS)
    )
    result = ReactomeTool().run(query="TP53")
    assert result.success is True
    assert result.data["total"] == 2


@respx.mock
def test_reactome_not_found():
    respx.get(f"{REACTOME_BASE}/data/pathways/low/entity/UniProt:XXXX").mock(
        return_value=httpx.Response(404)
    )
    respx.get(f"{REACTOME_BASE}/search/query").mock(
        return_value=httpx.Response(200, json={"results": [{"entries": []}]})
    )
    result = ReactomeTool().run(query="XXXX")
    assert result.success is False


# ── GWAS Catalog ──────────────────────────────────────────────────────────────

from proteinbox.api_tools.gwas_catalog import GWASCatalogTool

GWAS_BASE = "https://www.ebi.ac.uk/gwas/rest/api"

MOCK_GWAS_RESPONSE = {
    "_embedded": {
        "associations": [
            {
                "efoTraits": [{"trait": "Breast cancer"}],
                "loci": [{"strongestRiskAlleles": [{"riskAlleleName": "rs12345-A"}]}],
                "pvalueMantissa": 1,
                "pvalueExponent": -10,
                "riskFrequency": "0.25",
                "orPerCopyNum": 1.3,
                "studyAccession": "GCST000123",
            }
        ]
    }
}


@respx.mock
def test_gwas_catalog_success():
    respx.get(f"{GWAS_BASE}/associations/search/findByGene").mock(
        return_value=httpx.Response(200, json=MOCK_GWAS_RESPONSE)
    )
    result = GWASCatalogTool().run(gene="BRCA1")
    assert result.success is True
    assert result.data["total"] == 1
    assert result.data["associations"][0]["traits"] == ["Breast cancer"]
    assert result.data["associations"][0]["snps"] == ["rs12345-A"]
    assert result.data["associations"][0]["p_value"] == "1e-10"


@respx.mock
def test_gwas_catalog_no_results():
    respx.get(f"{GWAS_BASE}/associations/search/findByGene").mock(
        return_value=httpx.Response(200, json={"_embedded": {"associations": []}})
    )
    result = GWASCatalogTool().run(gene="FAKEGENE")
    assert result.success is True
    assert result.data["total"] == 0
    assert result.data["associations"] == []


@respx.mock
def test_gwas_catalog_uses_geneName_param():
    """Verify the tool sends geneName=, not gene=, so the endpoint actually filters."""
    called_with = {}

    def capture(request):
        called_with["params"] = dict(request.url.params)
        return httpx.Response(200, json={"_embedded": {"associations": []}})

    respx.get(f"{GWAS_BASE}/associations/search/findByGene").mock(side_effect=capture)
    GWASCatalogTool().run(gene="TP53")
    assert called_with["params"].get("geneName") == "TP53"
    assert "gene" not in called_with["params"]
