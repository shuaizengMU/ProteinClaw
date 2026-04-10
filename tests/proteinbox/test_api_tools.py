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


# ── Protein Atlas ─────────────────────────────────────────────────────────────

from proteinbox.api_tools.protein_atlas import HumanProteinAtlasTool

PA_BASE = "https://www.proteinatlas.org/search/TP53"

MOCK_PA_RESPONSE = [
    {
        "Gene": "TP53",
        "Gene description": "Tumor protein p53",
        "Protein class": ["Cancer-related genes", "Transcription factors"],
        "Subcellular location": ["Nucleus", "Cytoplasm"],
        "RNA tissue specificity": "Low tissue specificity",
        "RNA tissue distribution": "Detected in all",
        "Tissue expression cluster": ["Cluster 1"],
        "RNA cancer specificity": "Not detected",
        "Prognostic - favorable": ["Breast cancer"],
    }
]


@respx.mock
def test_protein_atlas_success():
    respx.get(PA_BASE).mock(return_value=httpx.Response(200, json=MOCK_PA_RESPONSE))
    result = HumanProteinAtlasTool().run(gene="TP53")
    assert result.success is True
    assert result.data["gene"] == "TP53"
    assert result.data["description"] == "Tumor protein p53"
    assert "Nucleus" in result.data["subcellular_localization"]
    assert result.data["cancer_specificity"] == "Not detected"
    assert result.data["prognostic_favorable"] == ["Breast cancer"]


@respx.mock
def test_protein_atlas_no_columns_param():
    """Verify the tool sends format=json and no columns= or search= parameter."""
    called_with = {}

    def capture(request):
        called_with["params"] = dict(request.url.params)
        return httpx.Response(200, json=MOCK_PA_RESPONSE)

    respx.get(PA_BASE).mock(side_effect=capture)
    HumanProteinAtlasTool().run(gene="TP53")
    assert called_with["params"].get("format") == "json"
    assert "search" not in called_with["params"]
    assert "columns" not in called_with["params"]


@respx.mock
def test_protein_atlas_exact_gene_match():
    """Returns the TP53 entry even when the response contains multiple genes."""
    multi = [
        {"Gene": "TP53BP1", "Gene description": "TP53 binding protein 1",
         "Protein class": [], "Subcellular location": [], "RNA tissue specificity": "",
         "RNA tissue distribution": "", "Tissue expression cluster": [],
         "RNA cancer specificity": "", "Prognostic - favorable": []},
        {"Gene": "TP53", "Gene description": "Tumor protein p53",
         "Protein class": ["Cancer-related genes"], "Subcellular location": ["Nucleus"],
         "RNA tissue specificity": "Low tissue specificity",
         "RNA tissue distribution": "Detected in all", "Tissue expression cluster": [],
         "RNA cancer specificity": "", "Prognostic - favorable": []},
    ]
    respx.get(PA_BASE).mock(return_value=httpx.Response(200, json=multi))
    result = HumanProteinAtlasTool().run(gene="TP53")
    assert result.success is True
    assert result.data["gene"] == "TP53"
    assert result.data["description"] == "Tumor protein p53"


@respx.mock
def test_protein_atlas_not_found():
    respx.get("https://www.proteinatlas.org/search/FAKEGENE").mock(
        return_value=httpx.Response(200, json=[])
    )
    result = HumanProteinAtlasTool().run(gene="FAKEGENE")
    assert result.success is False


# ── Ensembl Plants ────────────────────────────────────────────────────────────

from proteinbox.api_tools.ensembl_plants import EnsemblPlantsTool, ENSEMBL_REST


@respx.mock
def test_ensembl_plants_by_locus():
    gene_payload = {
        "id": "AT1G62630",
        "display_name": "AT1G62630",
        "description": "disease resistance protein (CC-NBS-LRR class)",
        "biotype": "protein_coding",
        "species": "arabidopsis_thaliana",
        "assembly_name": "TAIR10",
        "seq_region_name": "1",
        "start": 23200000,
        "end": 23205000,
        "strand": 1,
        "Transcript": [
            {
                "id": "AT1G62630.1",
                "biotype": "protein_coding",
                "is_canonical": 1,
                "length": 2700,
                "Translation": {"id": "AT1G62630.1.p"},
            },
            {
                "id": "AT1G62630.2",
                "biotype": "protein_coding",
                "is_canonical": 0,
                "length": 2100,
                "Translation": {"id": "AT1G62630.2.p"},
            },
        ],
    }
    seq_payload = {"id": "AT1G62630.1.p", "seq": "MGISFSIPFDPCVNKVSQWLDMKGSYTHNLEKNLVALETT"}

    respx.get(f"{ENSEMBL_REST}/lookup/id/AT1G62630").mock(
        return_value=httpx.Response(200, json=gene_payload)
    )
    respx.get(f"{ENSEMBL_REST}/sequence/id/AT1G62630.1.p").mock(
        return_value=httpx.Response(200, json=seq_payload)
    )

    result = EnsemblPlantsTool().run(locus_id="AT1G62630")
    assert result.success is True
    assert result.data["gene_id"] == "AT1G62630"
    assert result.data["canonical_transcript_id"] == "AT1G62630.1"
    assert result.data["protein_id"] == "AT1G62630.1.p"
    assert result.data["protein_length"] == 40
    assert result.data["protein_sequence"].startswith("MGISFSIPFDPC")
    assert result.data["fasta"].startswith(">")
    assert len(result.data["transcripts"]) == 2


@respx.mock
def test_ensembl_plants_by_symbol():
    gene_payload = {
        "id": "AT3G52430",
        "display_name": "PAD4",
        "species": "arabidopsis_thaliana",
        "assembly_name": "TAIR10",
        "seq_region_name": "3",
        "start": 1,
        "end": 2,
        "strand": 1,
        "Transcript": [
            {
                "id": "AT3G52430.1",
                "is_canonical": 1,
                "Translation": {"id": "AT3G52430.1.p"},
            }
        ],
    }
    respx.get(f"{ENSEMBL_REST}/lookup/symbol/arabidopsis_thaliana/PAD4").mock(
        return_value=httpx.Response(200, json=gene_payload)
    )
    respx.get(f"{ENSEMBL_REST}/sequence/id/AT3G52430.1.p").mock(
        return_value=httpx.Response(200, json={"seq": "MKQVELLA"})
    )
    result = EnsemblPlantsTool().run(symbol="PAD4")
    assert result.success is True
    assert result.data["display_name"] == "PAD4"
    assert result.data["protein_sequence"] == "MKQVELLA"


@respx.mock
def test_ensembl_plants_not_found():
    respx.get(f"{ENSEMBL_REST}/lookup/id/AT9G99999").mock(
        return_value=httpx.Response(404, json={"error": "not found"})
    )
    result = EnsemblPlantsTool().run(locus_id="AT9G99999")
    assert result.success is False


def test_ensembl_plants_requires_input():
    result = EnsemblPlantsTool().run()
    assert result.success is False


# ── EBI BLAST ─────────────────────────────────────────────────────────────────

from proteinbox.api_tools.ebi_blast import EBIBlastTool, EBI_BLAST_BASE


@respx.mock
def test_ebi_blast_success(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)

    respx.post(f"{EBI_BLAST_BASE}/run").mock(
        return_value=httpx.Response(200, text="ncbiblast-R20260410-JOB42")
    )
    respx.get(f"{EBI_BLAST_BASE}/status/ncbiblast-R20260410-JOB42").mock(
        return_value=httpx.Response(200, text="FINISHED")
    )
    respx.get(f"{EBI_BLAST_BASE}/result/ncbiblast-R20260410-JOB42/json").mock(
        return_value=httpx.Response(200, json={
            "hits": [
                {
                    "hit_acc": "P04637",
                    "hit_desc": "Cellular tumor antigen p53 OS=Homo sapiens",
                    "hit_len": 393,
                    "hit_hsps": [
                        {
                            "hsp_align_len": 40,
                            "hsp_identity": 38,
                            "hsp_expect": "1e-20",
                            "hsp_bit_score": 85.2,
                            "hsp_qseq": "MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPS",
                            "hsp_hseq": "MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPS",
                            "hsp_mseq": "|||||||||||||||||||||||||||||||||||||",
                        }
                    ],
                },
                {
                    "hit_acc": "P02340",
                    "hit_desc": "Cellular tumor antigen p53 OS=Mus musculus",
                    "hit_len": 390,
                    "hit_hsps": [
                        {
                            "hsp_align_len": 40,
                            "hsp_identity": 30,
                            "hsp_expect": "1e-15",
                            "hsp_bit_score": 70.1,
                            "hsp_qseq": "MEEPQSDPSVEP",
                            "hsp_hseq": "MEEPPSDPSVEP",
                            "hsp_mseq": "|||| |||||||",
                        }
                    ],
                },
            ]
        })
    )

    result = EBIBlastTool().run(
        sequence="MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPS",
        program="blastp",
        database="uniprotkb",
        max_hits=5,
        poll_interval=0.01,
    )
    assert result.success is True
    assert result.data["job_id"] == "ncbiblast-R20260410-JOB42"
    assert len(result.data["hits"]) == 2
    assert result.data["hits"][0]["hit_id"] == "P04637"
    assert result.data["hits"][0]["identity_pct"] == 95.0
    assert result.data["hits"][0]["hit_seq"].startswith("MEEPQSDPSV")


@respx.mock
def test_ebi_blast_status_error(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    respx.post(f"{EBI_BLAST_BASE}/run").mock(
        return_value=httpx.Response(200, text="ncbiblast-JOB99")
    )
    respx.get(f"{EBI_BLAST_BASE}/status/ncbiblast-JOB99").mock(
        return_value=httpx.Response(200, text="ERROR")
    )
    result = EBIBlastTool().run(sequence="MEEPQ", poll_interval=0.01)
    assert result.success is False
    assert "ERROR" in (result.error or "")


def test_ebi_blast_unknown_program():
    result = EBIBlastTool().run(sequence="MEEPQ", program="blastz")
    assert result.success is False


# ── Clustal Omega ─────────────────────────────────────────────────────────────

from proteinbox.api_tools.clustal_omega import ClustalOmegaTool, CLUSTALO_BASE


_CLUSTAL_RESULT = """CLUSTAL O(1.2.4) multiple sequence alignment


Col0            MGISFSIPFDPCVNKVSQWLDMKGSYTHNLEKNLVALETT     40
Rld2            MGISFSIPFDPCVNKVSQWLDMKGSYTHNLEKNLVALETT     40
                ****************************************

Col0            MEELKAKRDDLLRRLKRE     58
Rld2            MEELKAKRDDLLRRLKRE     58
                ******************
"""


@respx.mock
def test_clustal_omega_success(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    respx.post(f"{CLUSTALO_BASE}/run").mock(
        return_value=httpx.Response(200, text="clustalo-R20260410-JOB7")
    )
    respx.get(f"{CLUSTALO_BASE}/status/clustalo-R20260410-JOB7").mock(
        return_value=httpx.Response(200, text="FINISHED")
    )
    respx.get(f"{CLUSTALO_BASE}/result/clustalo-R20260410-JOB7/aln-clustal_num").mock(
        return_value=httpx.Response(200, text=_CLUSTAL_RESULT)
    )
    fasta = ">Col0\nMGISFSIPFDPCVNKVSQWLDMKGSYTHNLEKNLVALETTMEELKAKRDDLLRRLKRE\n>Rld2\nMGISFSIPFDPCVNKVSQWLDMKGSYTHNLEKNLVALETTMEELKAKRDDLLRRLKRE\n"
    result = ClustalOmegaTool().run(sequences=fasta, poll_interval=0.01)
    assert result.success is True
    assert result.data["num_sequences"] == 2
    assert result.data["alignment_length"] == 58
    assert result.data["conserved_columns"] == 58
    assert result.data["aligned"]["Col0"].startswith("MGISFSIPFDPC")
    assert "Rld2" in result.data["aligned"]


def test_clustal_omega_requires_multi_fasta():
    result = ClustalOmegaTool().run(sequences=">only_one\nMEEPQ")
    assert result.success is False


@respx.mock
def test_clustal_omega_timeout(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_: None)
    respx.post(f"{CLUSTALO_BASE}/run").mock(
        return_value=httpx.Response(200, text="clustalo-JOB8")
    )
    respx.get(f"{CLUSTALO_BASE}/status/clustalo-JOB8").mock(
        return_value=httpx.Response(200, text="RUNNING")
    )
    fasta = ">a\nMEEPQ\n>b\nMEEPQ\n"
    result = ClustalOmegaTool().run(sequences=fasta, timeout=0, poll_interval=0.01)
    assert result.success is False
