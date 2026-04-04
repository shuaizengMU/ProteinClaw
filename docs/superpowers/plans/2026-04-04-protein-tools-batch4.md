# Protein Tools Batch 4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 8 new protein bioinformatics API tools covering function classification, target validation, expression, interactions, structural classification, population genetics, and sequence motifs.

**Architecture:** Each tool is a single Python file in `proteinbox/api_tools/` using the existing `@register_tool` pattern. Tools use `httpx` for HTTP requests and return `ToolResult`. No new abstractions or base classes.

**Tech Stack:** Python, httpx, pydantic (via ProteinTool base), existing tool registry

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `proteinbox/api_tools/gene_ontology.py` | GO annotations via QuickGO |
| Create | `proteinbox/api_tools/panther.py` | Protein family classification |
| Create | `proteinbox/api_tools/opentargets.py` | Target-disease associations |
| Create | `proteinbox/api_tools/protein_atlas.py` | Tissue expression & localization |
| Create | `proteinbox/api_tools/intact.py` | Curated molecular interactions |
| Create | `proteinbox/api_tools/cath.py` | Structural domain classification |
| Create | `proteinbox/api_tools/gwas_catalog.py` | GWAS trait associations |
| Create | `proteinbox/api_tools/elm.py` | Short linear motif prediction |
| Modify | `cli-tui/src/app.rs:468` | Add demo examples for new tools |

---

### Task 1: Gene Ontology (QuickGO) Tool

**Files:**
- Create: `proteinbox/api_tools/gene_ontology.py`

- [ ] **Step 1: Create gene_ontology.py**

```python
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class GeneOntologyTool(ProteinTool):
    name: str = "gene_ontology"
    description: str = (
        "Retrieve Gene Ontology (GO) functional annotations for a protein from QuickGO. "
        "Returns GO terms grouped by aspect: molecular function, biological process, "
        "and cellular component. Useful for understanding what a protein does, where it acts, "
        "and which processes it participates in."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "accession": {
                "type": "string",
                "description": "UniProt accession ID (e.g. P04637 for TP53)",
            },
        },
        "required": ["accession"],
    }

    def run(self, **kwargs) -> ToolResult:
        accession = kwargs["accession"].strip().upper()

        try:
            resp = httpx.get(
                "https://www.ebi.ac.uk/QuickGO/services/annotation/search",
                params={
                    "geneProductId": accession,
                    "limit": "100",
                    "geneProductType": "protein",
                },
                headers={"Accept": "application/json"},
                timeout=30,
            )
            if resp.status_code != 200:
                return ToolResult(
                    success=False,
                    error=f"QuickGO returned {resp.status_code} for {accession}",
                )

            data = resp.json()
            results = data.get("results", [])

            if not results:
                return ToolResult(
                    success=True,
                    data={"accession": accession, "annotations": {}, "total": 0},
                    display=f"No GO annotations found for {accession}",
                )

            # Group by aspect
            grouped: dict[str, list[dict]] = {
                "molecular_function": [],
                "biological_process": [],
                "cellular_component": [],
            }
            seen: set[str] = set()

            for r in results:
                go_id = r.get("goId", "")
                aspect = r.get("goAspect", "").lower().replace(" ", "_")
                if aspect not in grouped or go_id in seen:
                    continue
                seen.add(go_id)
                grouped[aspect].append({
                    "go_id": go_id,
                    "term_name": r.get("goName", ""),
                    "evidence_code": r.get("goEvidence", ""),
                    "qualifier": r.get("qualifier", ""),
                    "assigned_by": r.get("assignedBy", ""),
                })

            counts = {k: len(v) for k, v in grouped.items()}
            total = sum(counts.values())

            display = (
                f"{accession}: {counts.get('molecular_function', 0)} molecular_function, "
                f"{counts.get('biological_process', 0)} biological_process, "
                f"{counts.get('cellular_component', 0)} cellular_component GO terms"
            )
            return ToolResult(
                success=True,
                data={
                    "accession": accession,
                    "total": total,
                    "counts": counts,
                    "annotations": grouped,
                },
                display=display,
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

- [ ] **Step 2: Verify import works**

Run: `python -c "from proteinbox.api_tools.gene_ontology import GeneOntologyTool; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add proteinbox/api_tools/gene_ontology.py
git commit -m "feat(tools): add Gene Ontology (QuickGO) tool"
```

---

### Task 2: PANTHER Tool

**Files:**
- Create: `proteinbox/api_tools/panther.py`

- [ ] **Step 1: Create panther.py**

```python
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class PANTHERTool(ProteinTool):
    name: str = "panther"
    description: str = (
        "Classify a protein into PANTHER families and subfamilies. "
        "Returns protein family, subfamily, protein class, and GO slim annotations. "
        "Useful for understanding evolutionary relationships and functional classification."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "gene": {
                "type": "string",
                "description": "Gene symbol (e.g. TP53) or UniProt accession (e.g. P04637)",
            },
            "organism": {
                "type": "string",
                "description": "NCBI taxon ID. Default: 9606 (human)",
                "default": "9606",
            },
        },
        "required": ["gene"],
    }

    def run(self, **kwargs) -> ToolResult:
        gene = kwargs["gene"].strip()
        organism = kwargs.get("organism", "9606").strip()

        try:
            resp = httpx.get(
                "https://pantherdb.org/services/oai/pantherdb/geneinfo",
                params={
                    "geneInputList": gene,
                    "organism": organism,
                },
                headers={"Accept": "application/json"},
                timeout=30,
            )
            if resp.status_code != 200:
                return ToolResult(
                    success=False,
                    error=f"PANTHER returned {resp.status_code} for {gene}",
                )

            data = resp.json()
            mapped = data.get("search", {}).get("mapped_genes", {})
            gene_list = mapped.get("gene", []) if mapped else []
            if isinstance(gene_list, dict):
                gene_list = [gene_list]

            if not gene_list:
                return ToolResult(
                    success=False,
                    error=f"No PANTHER classification found for '{gene}'",
                )

            results = []
            for g in gene_list[:5]:
                ann = g.get("annotation_type_list", {}).get("annotation_data_type", [])
                if isinstance(ann, dict):
                    ann = [ann]
                go_terms = []
                for a in ann:
                    content = a.get("content", "")
                    ann_type = a.get("annotation_type", "")
                    if content:
                        go_terms.append({
                            "type": ann_type,
                            "content": content,
                        })

                panther_family = g.get("persistent_id", "")
                family_name = g.get("family_name", "")
                subfamily_name = g.get("subfamily_name", "")
                protein_class = g.get("protein_class", "")

                results.append({
                    "accession": g.get("accession", ""),
                    "gene_symbol": g.get("gene_symbol", ""),
                    "gene_name": g.get("gene_name", ""),
                    "panther_family_id": panther_family,
                    "family_name": family_name,
                    "subfamily_name": subfamily_name,
                    "protein_class": protein_class,
                    "species": g.get("species", ""),
                    "go_annotations": go_terms[:10],
                })

            top = results[0] if results else {}
            display = (
                f"{top.get('gene_symbol', gene)}: "
                f"{top.get('family_name', 'Unknown family')} ({top.get('panther_family_id', '')})"
            )
            if top.get("protein_class"):
                display += f", class: {top['protein_class']}"

            return ToolResult(success=True, data={"gene": gene, "results": results}, display=display)

        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

- [ ] **Step 2: Verify import works**

Run: `python -c "from proteinbox.api_tools.panther import PANTHERTool; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add proteinbox/api_tools/panther.py
git commit -m "feat(tools): add PANTHER protein classification tool"
```

---

### Task 3: Open Targets Tool

**Files:**
- Create: `proteinbox/api_tools/opentargets.py`

- [ ] **Step 1: Create opentargets.py**

```python
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class OpenTargetsTool(ProteinTool):
    name: str = "opentargets"
    description: str = (
        "Query Open Targets Platform for target-disease associations. "
        "Given a gene symbol, returns top disease associations with evidence scores, "
        "known drugs, and tractability assessments. Aggregates evidence from genetics, "
        "somatic mutations, drugs, literature, and more."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "gene": {
                "type": "string",
                "description": "Gene symbol (e.g. EGFR, TP53, BRCA1)",
            },
        },
        "required": ["gene"],
    }

    def run(self, **kwargs) -> ToolResult:
        gene = kwargs["gene"].strip().upper()
        api = "https://api.platform.opentargets.org/api/v4/graphql"

        try:
            # Step 1: Resolve gene symbol to Ensembl ID
            search_query = {
                "query": """
                query SearchTarget($q: String!) {
                    search(queryString: $q, entityNames: ["target"], page: {size: 1, index: 0}) {
                        hits { id name }
                    }
                }
                """,
                "variables": {"q": gene},
            }
            resp = httpx.post(api, json=search_query, timeout=30)
            resp.raise_for_status()
            hits = resp.json().get("data", {}).get("search", {}).get("hits", [])

            if not hits:
                return ToolResult(success=False, error=f"No Open Targets target found for '{gene}'")

            ensembl_id = hits[0]["id"]
            target_name = hits[0].get("name", gene)

            # Step 2: Get disease associations + known drugs
            assoc_query = {
                "query": """
                query TargetAssoc($id: String!) {
                    target(ensemblId: $id) {
                        approvedName
                        approvedSymbol
                        knownDrugs(size: 10) {
                            rows {
                                drug { name }
                                phase
                                mechanismOfAction
                                disease { name }
                            }
                        }
                        associatedDiseases(page: {size: 15, index: 0}) {
                            rows {
                                disease { id name }
                                score
                                datasourceScores {
                                    componentId: id
                                    score
                                }
                            }
                        }
                    }
                }
                """,
                "variables": {"id": ensembl_id},
            }
            resp = httpx.post(api, json=assoc_query, timeout=30)
            resp.raise_for_status()
            target = resp.json().get("data", {}).get("target", {})

            if not target:
                return ToolResult(success=False, error=f"No data returned for {ensembl_id}")

            # Parse associations
            assoc_rows = target.get("associatedDiseases", {}).get("rows", [])
            associations = []
            for row in assoc_rows:
                disease = row.get("disease", {})
                ds_scores = {
                    s.get("componentId", ""): round(s.get("score", 0), 3)
                    for s in row.get("datasourceScores", [])
                }
                associations.append({
                    "disease_id": disease.get("id", ""),
                    "disease_name": disease.get("name", ""),
                    "overall_score": round(row.get("score", 0), 3),
                    "datatype_scores": ds_scores,
                })

            # Parse drugs
            drug_rows = target.get("knownDrugs", {}).get("rows", [])
            drugs = []
            for d in drug_rows:
                drugs.append({
                    "drug_name": d.get("drug", {}).get("name", ""),
                    "phase": d.get("phase", ""),
                    "mechanism": d.get("mechanismOfAction", ""),
                    "indication": d.get("disease", {}).get("name", ""),
                })

            data = {
                "gene": gene,
                "ensembl_id": ensembl_id,
                "approved_name": target.get("approvedName", ""),
                "associations": associations,
                "drugs": drugs,
                "total_associations": len(assoc_rows),
            }

            top_disease = associations[0]["disease_name"] if associations else "none"
            top_score = associations[0]["overall_score"] if associations else 0
            display = (
                f"{gene} ({ensembl_id}): {len(associations)} disease associations, "
                f"top: {top_disease} ({top_score}), {len(drugs)} known drugs"
            )
            return ToolResult(success=True, data=data, display=display)

        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

- [ ] **Step 2: Verify import works**

Run: `python -c "from proteinbox.api_tools.opentargets import OpenTargetsTool; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add proteinbox/api_tools/opentargets.py
git commit -m "feat(tools): add Open Targets disease association tool"
```

---

### Task 4: Human Protein Atlas Tool

**Files:**
- Create: `proteinbox/api_tools/protein_atlas.py`

- [ ] **Step 1: Create protein_atlas.py**

```python
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class HumanProteinAtlasTool(ProteinTool):
    name: str = "protein_atlas"
    description: str = (
        "Query the Human Protein Atlas for tissue and cell expression, "
        "subcellular localization, and protein classification. "
        "Returns RNA expression across tissues, protein detection via IHC, "
        "and where in the cell the protein is found."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "gene": {
                "type": "string",
                "description": "Gene symbol (e.g. TP53, EGFR, BRCA1)",
            },
        },
        "required": ["gene"],
    }

    def run(self, **kwargs) -> ToolResult:
        gene = kwargs["gene"].strip().upper()

        try:
            resp = httpx.get(
                f"https://www.proteinatlas.org/{gene}.json",
                timeout=30,
                follow_redirects=True,
            )
            if resp.status_code != 200:
                return ToolResult(
                    success=False,
                    error=f"Human Protein Atlas returned {resp.status_code} for {gene}",
                )

            raw = resp.json()
            if isinstance(raw, list):
                raw = raw[0] if raw else {}

            gene_name = raw.get("Gene", gene)
            gene_desc = raw.get("Gene description", "")
            protein_class = raw.get("Protein class", [])
            if isinstance(protein_class, str):
                protein_class = [protein_class]

            # Subcellular localization
            subcellular = raw.get("Subcellular location", [])
            if isinstance(subcellular, str):
                subcellular = [subcellular]

            # RNA tissue expression — extract top tissues
            rna_tissue = raw.get("RNA tissue specificity", "")
            rna_data = raw.get("RNA tissue distribution", "")

            # Tissue expression summary
            tissue_expr = raw.get("Tissue expression cluster", [])
            if isinstance(tissue_expr, str):
                tissue_expr = [tissue_expr]

            # Cancer info
            cancer_specificity = raw.get("RNA cancer specificity", "")
            prognostic = raw.get("Prognostic - favorable", [])
            if isinstance(prognostic, str):
                prognostic = [prognostic]

            data = {
                "gene": gene_name,
                "description": gene_desc,
                "protein_class": protein_class,
                "subcellular_localization": subcellular,
                "rna_tissue_specificity": rna_tissue,
                "rna_tissue_distribution": rna_data,
                "tissue_expression_cluster": tissue_expr,
                "cancer_specificity": cancer_specificity,
                "prognostic_favorable": prognostic,
                "url": f"https://www.proteinatlas.org/{gene}",
            }

            loc_str = ", ".join(subcellular[:5]) if subcellular else "unknown"
            class_str = ", ".join(protein_class[:3]) if protein_class else "unclassified"
            display = (
                f"{gene_name}: localization: {loc_str}, "
                f"class: {class_str}"
            )
            if cancer_specificity:
                display += f", cancer specificity: {cancer_specificity}"

            return ToolResult(success=True, data=data, display=display)

        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

- [ ] **Step 2: Verify import works**

Run: `python -c "from proteinbox.api_tools.protein_atlas import HumanProteinAtlasTool; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add proteinbox/api_tools/protein_atlas.py
git commit -m "feat(tools): add Human Protein Atlas expression tool"
```

---

### Task 5: IntAct Tool

**Files:**
- Create: `proteinbox/api_tools/intact.py`

- [ ] **Step 1: Create intact.py**

```python
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class IntActTool(ProteinTool):
    name: str = "intact"
    description: str = (
        "Query IntAct for curated molecular interactions. "
        "Given a UniProt accession, returns binary protein interactions with "
        "experimental detection methods, interaction types, and confidence scores. "
        "Complements STRING with curated, experimentally validated interactions."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "accession": {
                "type": "string",
                "description": "UniProt accession ID (e.g. P04637 for TP53)",
            },
        },
        "required": ["accession"],
    }

    def run(self, **kwargs) -> ToolResult:
        accession = kwargs["accession"].strip().upper()

        try:
            # Use the IntAct PSICQUIC-style REST API
            resp = httpx.get(
                f"https://www.ebi.ac.uk/intact/ws/interaction/findInteractor/{accession}",
                params={"pageSize": "25"},
                headers={"Accept": "application/json"},
                timeout=30,
            )

            if resp.status_code == 404:
                return ToolResult(
                    success=True,
                    data={"accession": accession, "interactions": [], "total": 0},
                    display=f"No IntAct interactions found for {accession}",
                )

            if resp.status_code != 200:
                # Fallback: try the search endpoint
                resp = httpx.get(
                    "https://www.ebi.ac.uk/intact/ws/interaction/list",
                    params={"query": accession, "pageSize": "25"},
                    headers={"Accept": "application/json"},
                    timeout=30,
                )
                if resp.status_code != 200:
                    return ToolResult(
                        success=False,
                        error=f"IntAct returned {resp.status_code} for {accession}",
                    )

            data = resp.json()
            content = data.get("content", data) if isinstance(data, dict) else data
            if isinstance(content, dict):
                content = content.get("data", [content])

            interactions = []
            for item in (content if isinstance(content, list) else [])[:20]:
                partners = []
                for p in item.get("participants", item.get("interactors", [])):
                    acc = p.get("interactorRef", p.get("accession", ""))
                    name = p.get("preferredName", p.get("name", ""))
                    if acc != accession:
                        partners.append({"accession": acc, "name": name})

                interactions.append({
                    "interaction_id": item.get("ac", item.get("interactionAc", "")),
                    "partners": partners,
                    "interaction_type": item.get("interactionType", {}).get("shortName", ""),
                    "detection_method": item.get("detectionMethod", {}).get("shortName", ""),
                    "publication_count": item.get("publicationCount", 0),
                    "mi_score": item.get("miScore", item.get("intactMiscore", 0)),
                })

            total = data.get("totalElements", len(interactions)) if isinstance(data, dict) else len(interactions)

            top_partners = []
            for i in interactions[:5]:
                for p in i.get("partners", []):
                    if p.get("name"):
                        top_partners.append(p["name"])

            display = (
                f"{accession}: {total} interactions"
            )
            if top_partners:
                display += f", top partners: {', '.join(top_partners[:5])}"

            return ToolResult(
                success=True,
                data={"accession": accession, "total": total, "interactions": interactions},
                display=display,
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

- [ ] **Step 2: Verify import works**

Run: `python -c "from proteinbox.api_tools.intact import IntActTool; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add proteinbox/api_tools/intact.py
git commit -m "feat(tools): add IntAct molecular interaction tool"
```

---

### Task 6: CATH Tool

**Files:**
- Create: `proteinbox/api_tools/cath.py`

- [ ] **Step 1: Create cath.py**

```python
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class CATHTool(ProteinTool):
    name: str = "cath"
    description: str = (
        "Query the CATH database for structural domain classification. "
        "Given a UniProt accession, returns CATH domain assignments with "
        "Class, Architecture, Topology, and Homologous superfamily hierarchy. "
        "Useful for understanding protein structural organization and fold families."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "accession": {
                "type": "string",
                "description": "UniProt accession ID (e.g. P04637 for TP53)",
            },
        },
        "required": ["accession"],
    }

    def run(self, **kwargs) -> ToolResult:
        accession = kwargs["accession"].strip().upper()

        try:
            resp = httpx.get(
                f"https://www.cathdb.info/version/current/api/rest/uniprot/{accession}",
                headers={"Accept": "application/json"},
                timeout=30,
            )

            if resp.status_code == 404:
                return ToolResult(
                    success=True,
                    data={"accession": accession, "domains": []},
                    display=f"No CATH structural domains found for {accession}",
                )

            if resp.status_code != 200:
                return ToolResult(
                    success=False,
                    error=f"CATH returned {resp.status_code} for {accession}",
                )

            raw = resp.json()
            domain_list = raw if isinstance(raw, list) else raw.get("data", [raw])

            domains = []
            for d in domain_list[:10]:
                cath_id = d.get("cath_id", d.get("superfamily_id", ""))
                domains.append({
                    "domain_id": d.get("domain_id", d.get("name", "")),
                    "cath_id": cath_id,
                    "class": d.get("class_name", ""),
                    "architecture": d.get("architecture_name", ""),
                    "topology": d.get("topology_name", ""),
                    "superfamily": d.get("superfamily_name", d.get("homology_name", "")),
                    "start": d.get("start", ""),
                    "end": d.get("end", ""),
                    "resolution": d.get("resolution", ""),
                })

            if not domains:
                return ToolResult(
                    success=True,
                    data={"accession": accession, "domains": []},
                    display=f"No CATH structural domains found for {accession}",
                )

            domain_strs = [
                f"{d['cath_id']} ({d['class']}, {d['architecture']})"
                if d.get("class") else d.get("cath_id", "unknown")
                for d in domains[:3]
            ]
            display = f"{accession}: {len(domains)} CATH domains — {', '.join(domain_strs)}"

            return ToolResult(
                success=True,
                data={"accession": accession, "domains": domains},
                display=display,
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

- [ ] **Step 2: Verify import works**

Run: `python -c "from proteinbox.api_tools.cath import CATHTool; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add proteinbox/api_tools/cath.py
git commit -m "feat(tools): add CATH structural domain classification tool"
```

---

### Task 7: GWAS Catalog Tool

**Files:**
- Create: `proteinbox/api_tools/gwas_catalog.py`

- [ ] **Step 1: Create gwas_catalog.py**

```python
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class GWASCatalogTool(ProteinTool):
    name: str = "gwas_catalog"
    description: str = (
        "Search the NHGRI-EBI GWAS Catalog for genome-wide association study results. "
        "Given a gene symbol, returns associated traits/diseases with SNP rsIDs, "
        "p-values, risk alleles, and study references. "
        "Useful for understanding population-level genetic associations."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "gene": {
                "type": "string",
                "description": "Gene symbol (e.g. BRCA1, TP53, APOE)",
            },
        },
        "required": ["gene"],
    }

    def run(self, **kwargs) -> ToolResult:
        gene = kwargs["gene"].strip().upper()

        try:
            # Search for associations by gene
            resp = httpx.get(
                "https://www.ebi.ac.uk/gwas/rest/api/associations/search/findByGene",
                params={"geneName": gene},
                headers={"Accept": "application/json"},
                timeout=30,
            )

            if resp.status_code != 200:
                return ToolResult(
                    success=False,
                    error=f"GWAS Catalog returned {resp.status_code} for {gene}",
                )

            data = resp.json()
            associations_raw = (
                data.get("_embedded", {}).get("associations", [])
            )

            if not associations_raw:
                return ToolResult(
                    success=True,
                    data={"gene": gene, "associations": [], "total": 0},
                    display=f"No GWAS associations found for {gene}",
                )

            associations = []
            for a in associations_raw[:20]:
                # Extract trait names
                traits = [
                    t.get("trait", "")
                    for t in a.get("efoTraits", a.get("traits", []))
                ]
                if not traits:
                    traits = [a.get("diseaseTrait", {}).get("trait", "")]

                # Extract SNPs
                snps = []
                for locus in a.get("loci", []):
                    for sra in locus.get("strongestRiskAlleles", []):
                        snps.append(sra.get("riskAlleleName", ""))

                p_value = a.get("pvalue", 0)
                p_mantissa = a.get("pvalueMantissa", 0)
                p_exponent = a.get("pvalueExponent", 0)
                if p_mantissa and p_exponent:
                    p_str = f"{p_mantissa}e{p_exponent}"
                else:
                    p_str = str(p_value)

                associations.append({
                    "traits": traits,
                    "snps": snps,
                    "p_value": p_str,
                    "risk_frequency": a.get("riskFrequency", ""),
                    "or_beta": a.get("orPerCopyNum", a.get("betaNum", "")),
                    "study_accession": a.get("studyAccession", ""),
                })

            # Collect unique traits for display
            all_traits: list[str] = []
            for a in associations:
                for t in a["traits"]:
                    if t and t not in all_traits:
                        all_traits.append(t)

            display = (
                f"{gene}: {len(associations_raw)} GWAS associations — "
                + ", ".join(all_traits[:5])
            )

            return ToolResult(
                success=True,
                data={
                    "gene": gene,
                    "total": len(associations_raw),
                    "associations": associations,
                    "unique_traits": all_traits,
                },
                display=display,
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

- [ ] **Step 2: Verify import works**

Run: `python -c "from proteinbox.api_tools.gwas_catalog import GWASCatalogTool; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add proteinbox/api_tools/gwas_catalog.py
git commit -m "feat(tools): add GWAS Catalog association tool"
```

---

### Task 8: ELM Tool

**Files:**
- Create: `proteinbox/api_tools/elm.py`

- [ ] **Step 1: Create elm.py**

```python
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class ELMTool(ProteinTool):
    name: str = "elm"
    description: str = (
        "Search the Eukaryotic Linear Motif (ELM) resource for short linear motifs (SLiMs) "
        "in a protein sequence. Returns predicted functional motifs — binding sites, "
        "modification sites, docking motifs, and degradation signals. "
        "Especially useful for disordered protein regions."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "sequence": {
                "type": "string",
                "description": "Protein sequence (amino acid one-letter codes) or UniProt accession (e.g. P04637)",
            },
        },
        "required": ["sequence"],
    }

    def run(self, **kwargs) -> ToolResult:
        seq_input = kwargs["sequence"].strip()

        try:
            # Determine if input is accession or sequence
            is_accession = len(seq_input) <= 20 and seq_input.replace("_", "").isalnum()

            if is_accession:
                url = f"http://elm.eu.org/api/search/{seq_input}.json"
            else:
                # Clean sequence
                seq = "".join(c for c in seq_input.upper() if c.isalpha())
                url = f"http://elm.eu.org/api/search/{seq}.json"

            resp = httpx.get(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "ProteinClaw/1.0 (bioinformatics tool)",
                },
                timeout=30,
                follow_redirects=True,
            )

            if resp.status_code != 200:
                # ELM API may be unavailable; provide a helpful fallback message
                return ToolResult(
                    success=False,
                    error=(
                        f"ELM returned {resp.status_code}. "
                        "The ELM server may be temporarily unavailable. "
                        "Try the web interface at http://elm.eu.org"
                    ),
                )

            data = resp.json()
            instances = data if isinstance(data, list) else data.get("instances", data.get("matches", []))

            motifs = []
            class_counts: dict[str, int] = {}
            for inst in (instances if isinstance(instances, list) else [])[:30]:
                elm_id = inst.get("elm_identifier", inst.get("motif_name", ""))
                motif_class = elm_id.split("_")[0] if "_" in elm_id else elm_id[:3]
                class_counts[motif_class] = class_counts.get(motif_class, 0) + 1

                motifs.append({
                    "elm_identifier": elm_id,
                    "motif_class": motif_class,
                    "start": inst.get("start", inst.get("start_position", "")),
                    "end": inst.get("end", inst.get("end_position", "")),
                    "sequence_match": inst.get("sequence", inst.get("match", "")),
                    "description": inst.get("description", inst.get("functional_site_description", "")),
                    "regex": inst.get("regex", inst.get("pattern", "")),
                })

            class_labels = {
                "LIG": "ligand binding",
                "MOD": "modification",
                "DOC": "docking",
                "DEG": "degradation",
                "CLV": "cleavage",
                "TRG": "targeting",
            }
            class_strs = [
                f"{count} {class_labels.get(cls, cls)}"
                for cls, count in sorted(class_counts.items(), key=lambda x: -x[1])
            ]

            display = f"Found {len(motifs)} ELM motifs"
            if class_strs:
                display += ": " + ", ".join(class_strs[:6])

            return ToolResult(
                success=True,
                data={
                    "input": seq_input[:50],
                    "total_motifs": len(motifs),
                    "class_summary": class_counts,
                    "motifs": motifs,
                },
                display=display,
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

- [ ] **Step 2: Verify import works**

Run: `python -c "from proteinbox.api_tools.elm import ELMTool; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add proteinbox/api_tools/elm.py
git commit -m "feat(tools): add ELM short linear motif tool"
```

---

### Task 9: Update /demo Command

**Files:**
- Modify: `cli-tui/src/app.rs:468` (the `Action::CommandDemo` handler)

- [ ] **Step 1: Add new demo categories to the CommandDemo handler**

In `cli-tui/src/app.rs`, find the `Action::CommandDemo` block (around line 468) and add these sections after the existing `**Post-Translational Modifications**` section and before the `**Literature Search**` section:

```
                         **Function Classification**\n\
                         • `What are the GO annotations for P04637? (Gene Ontology)`\n\
                         • `Classify TP53 into PANTHER protein families`\n\n\
                         **Target Validation & Population Genetics**\n\
                         • `What diseases are associated with EGFR? (Open Targets)`\n\
                         • `Find GWAS associations for BRCA1`\n\n\
                         **Expression & Localization**\n\
                         • `Where is TP53 expressed in human tissues? (Human Protein Atlas)`\n\n\
                         **Curated Interactions**\n\
                         • `Find curated molecular interactions for P04637 (IntAct)`\n\n\
                         **Structural Classification**\n\
                         • `What CATH structural domains does P04637 have?`\n\n\
                         **Sequence Motifs**\n\
                         • `Predict short linear motifs in P04637 (ELM)`\n\n\
```

- [ ] **Step 2: Verify Rust compiles**

Run: `cd cli-tui && cargo check`
Expected: compiles with no errors

- [ ] **Step 3: Commit**

```bash
git add cli-tui/src/app.rs
git commit -m "feat(tui): add demo examples for batch 4 protein tools"
```

---

### Task 10: Verify All Tools Discovered

- [ ] **Step 1: Run discovery check**

Run:
```bash
python -c "
from proteinbox.tools.registry import discover_tools
tools = discover_tools()
print(f'Total tools: {len(tools)}')
expected = ['gene_ontology','panther','opentargets','protein_atlas','intact','cath','gwas_catalog','elm']
for name in expected:
    status = 'OK' if name in tools else 'MISSING'
    print(f'  {name}: {status}')
"
```

Expected: Total tools: 26, all 8 show `OK`.

- [ ] **Step 2: Final commit**

```bash
git add -A
git commit -m "feat(tools): add 8 new protein bioinformatics tools (Batch 4)

Gene Ontology, PANTHER, Open Targets, Human Protein Atlas,
IntAct, CATH, GWAS Catalog, ELM."
```
