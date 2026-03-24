# tests/proteinbox/test_blast.py
import pytest
import respx
import httpx
from proteinbox.tools.blast import BLASTTool

SUBMIT_RESPONSE = "    RID = ABC123\n    RTOE = 10\n"
READY_RESPONSE = "Status=READY\n"
RESULTS_XML = """<?xml version="1.0"?>
<!DOCTYPE BlastOutput PUBLIC "-//NCBI//NCBI BlastOutput/EN" "">
<BlastOutput>
  <BlastOutput_iterations>
    <Iteration>
      <Iteration_hits>
        <Hit>
          <Hit_def>Tumor suppressor p53 [Homo sapiens]</Hit_def>
          <Hit_accession>NP_000537</Hit_accession>
          <Hit_hsps>
            <Hsp>
              <Hsp_evalue>1e-150</Hsp_evalue>
              <Hsp_identity>393</Hsp_identity>
              <Hsp_align-len>393</Hsp_align-len>
            </Hsp>
          </Hit_hsps>
        </Hit>
      </Iteration_hits>
    </Iteration>
  </BlastOutput_iterations>
</BlastOutput>"""

@respx.mock
def test_blast_tool_success():
    respx.post("https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi").mock(
        return_value=httpx.Response(200, text=SUBMIT_RESPONSE)
    )
    respx.get("https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi", params__contains={"RID": "ABC123", "FORMAT_OBJECT": "SearchInfo"}).mock(
        return_value=httpx.Response(200, text=READY_RESPONSE)
    )
    respx.get("https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi", params__contains={"RID": "ABC123", "FORMAT_TYPE": "XML"}).mock(
        return_value=httpx.Response(200, text=RESULTS_XML)
    )
    tool = BLASTTool()
    result = tool.run(sequence="MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPSQAMDDLMLSPDDIEQWFTEDP")
    assert result.success is True
    assert len(result.data["hits"]) >= 1
    assert result.data["hits"][0]["accession"] == "NP_000537"

@respx.mock
def test_blast_tool_timeout():
    respx.post("https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi").mock(
        return_value=httpx.Response(200, text=SUBMIT_RESPONSE)
    )
    respx.get("https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi").mock(
        return_value=httpx.Response(200, text="Status=WAITING\n")
    )
    tool = BLASTTool()
    result = tool.run(
        sequence="MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPSQAMDDLMLSPDDIEQWFTEDP",
        timeout=1,
        poll_interval=0.1,
    )
    assert result.success is False
    assert "timed out" in result.error.lower()
