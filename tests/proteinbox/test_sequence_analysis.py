from proteinbox.tools.sequence_analysis import SequenceAnalysisTool

# Human insulin B-chain (30 aa)
INSULIN_B = "FVNQHLCGSHLVEALYLVCGERGFFYTPKT"


def test_seq_analysis_basic():
    result = SequenceAnalysisTool().run(sequence=INSULIN_B)
    assert result.success is True
    assert result.data["length"] == 30
    assert 3000 < result.data["molecular_weight_da"] < 4000
    assert 5.0 < result.data["isoelectric_point"] < 8.0
    assert isinstance(result.data["gravy"], float)
    assert "L" in result.data["composition"]


def test_seq_analysis_fasta():
    fasta = ">sp|P01308|INS_HUMAN\nFVNQHLCGSHLVEALYLVCGERGFFYTPKT"
    result = SequenceAnalysisTool().run(sequence=fasta)
    assert result.success is True
    assert result.data["length"] == 30


def test_seq_analysis_empty():
    result = SequenceAnalysisTool().run(sequence="")
    assert result.success is False


def test_seq_analysis_unknown_aa():
    result = SequenceAnalysisTool().run(sequence="MVLXBZ")
    assert result.success is False
    assert "Unknown" in result.error


def test_extinction_coefficients():
    # A sequence with known W, Y, C counts
    seq = "WCYWCC"  # 2W, 1Y, 3C
    result = SequenceAnalysisTool().run(sequence=seq)
    assert result.success is True
    assert result.data["extinction_coefficient_reduced"] == 2 * 5500 + 1 * 1490
    assert result.data["extinction_coefficient_oxidized"] == 2 * 5500 + 1 * 1490 + 1 * 125
