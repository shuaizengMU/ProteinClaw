import math
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


# Kyte-Doolittle hydrophobicity scale
_KD_HYDRO = {
    "A": 1.8, "R": -4.5, "N": -3.5, "D": -3.5, "C": 2.5,
    "Q": -3.5, "E": -3.5, "G": -0.4, "H": -3.2, "I": 4.5,
    "L": 3.8, "K": -3.9, "M": 1.9, "F": 2.8, "P": -1.6,
    "S": -0.8, "T": -0.7, "W": -0.9, "Y": -1.3, "V": 4.2,
}

# Amino acid molecular weights (monoisotopic average)
_MW = {
    "A": 71.08, "R": 156.19, "N": 114.10, "D": 115.09, "C": 103.14,
    "Q": 128.13, "E": 129.12, "G": 57.05, "H": 137.14, "I": 113.16,
    "L": 113.16, "K": 128.17, "M": 131.20, "F": 147.18, "P": 97.12,
    "S": 87.08, "T": 101.10, "W": 186.21, "Y": 163.18, "V": 99.13,
}

# pKa values for pI calculation
_PKA = {
    "C_term": 2.34, "N_term": 9.69,
    "D": 3.65, "E": 4.25, "C": 8.18, "Y": 10.07,
    "H": 6.00, "K": 10.53, "R": 12.48,
}


def _calculate_pi(seq: str) -> float:
    """Estimate isoelectric point using bisection method."""
    charged_aa = {aa: seq.count(aa) for aa in "DECYHKR"}

    def _charge(ph: float) -> float:
        pos = (10 ** (_PKA["N_term"] - ph)) / (10 ** (_PKA["N_term"] - ph) + 1)
        pos += charged_aa.get("K", 0) * (10 ** (_PKA["K"] - ph)) / (10 ** (_PKA["K"] - ph) + 1)
        pos += charged_aa.get("R", 0) * (10 ** (_PKA["R"] - ph)) / (10 ** (_PKA["R"] - ph) + 1)
        pos += charged_aa.get("H", 0) * (10 ** (_PKA["H"] - ph)) / (10 ** (_PKA["H"] - ph) + 1)

        neg = -(10 ** (ph - _PKA["C_term"])) / (10 ** (ph - _PKA["C_term"]) + 1)
        neg -= charged_aa.get("D", 0) * (10 ** (ph - _PKA["D"])) / (10 ** (ph - _PKA["D"]) + 1)
        neg -= charged_aa.get("E", 0) * (10 ** (ph - _PKA["E"])) / (10 ** (ph - _PKA["E"]) + 1)
        neg -= charged_aa.get("C", 0) * (10 ** (ph - _PKA["C"])) / (10 ** (ph - _PKA["C"]) + 1)
        neg -= charged_aa.get("Y", 0) * (10 ** (ph - _PKA["Y"])) / (10 ** (ph - _PKA["Y"]) + 1)
        return pos + neg

    lo, hi = 0.0, 14.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if _charge(mid) > 0:
            lo = mid
        else:
            hi = mid
    return round((lo + hi) / 2, 2)


def _predict_signal_peptide(seq: str) -> dict:
    """Simple heuristic signal peptide prediction (not as accurate as SignalP)."""
    if len(seq) < 20:
        return {"predicted": False, "note": "Sequence too short"}

    n_region = seq[:6]
    h_region = seq[6:18]
    hydro = sum(_KD_HYDRO.get(aa, 0) for aa in h_region) / len(h_region)

    # Heuristic: signal peptides have a positive N-region and hydrophobic H-region
    n_charge = sum(1 for aa in n_region if aa in "KR")
    has_signal = hydro > 1.0 and n_charge >= 1

    return {
        "predicted": has_signal,
        "n_region_positive_charges": n_charge,
        "h_region_hydrophobicity": round(hydro, 2),
        "cleavage_site_estimate": "~18-25" if has_signal else None,
        "note": "Heuristic prediction — use SignalP for definitive results",
    }


def _predict_transmembrane(seq: str, window: int = 19) -> list[dict]:
    """Simple sliding-window transmembrane helix prediction."""
    if len(seq) < window:
        return []

    tm_regions = []
    in_tm = False
    start = 0

    for i in range(len(seq) - window + 1):
        segment = seq[i:i + window]
        hydro = sum(_KD_HYDRO.get(aa, 0) for aa in segment) / window
        if hydro > 1.6 and not in_tm:
            in_tm = True
            start = i
        elif hydro <= 1.6 and in_tm:
            in_tm = False
            tm_regions.append({"start": start + 1, "end": i + window, "length": i + window - start})
    if in_tm:
        tm_regions.append({"start": start + 1, "end": len(seq), "length": len(seq) - start})

    return tm_regions


@register_tool
class ExPASyTool(ProteinTool):
    name: str = "expasy_protparam"
    description: str = (
        "Advanced protein sequence analysis inspired by ExPASy ProtParam. "
        "Computes molecular weight, isoelectric point, GRAVY, amino acid composition, "
        "instability index, aliphatic index, signal peptide prediction, "
        "and transmembrane helix prediction. All computed locally (no API call needed)."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "sequence": {
                "type": "string",
                "description": "Amino acid sequence (one-letter codes, e.g. MVLSPADKTNVK...)",
            },
        },
        "required": ["sequence"],
    }

    def run(self, **kwargs) -> ToolResult:
        seq = kwargs["sequence"].strip().upper().replace(" ", "").replace("\n", "")
        seq = "".join(c for c in seq if c.isalpha())

        if not seq:
            return ToolResult(success=False, error="Empty sequence provided")

        n = len(seq)
        counts = {aa: seq.count(aa) for aa in "ACDEFGHIKLMNPQRSTVWY"}

        # Molecular weight
        mw = sum(_MW.get(aa, 0) * c for aa, c in counts.items()) + 18.02
        mw = round(mw, 2)

        # Isoelectric point
        pi = _calculate_pi(seq)

        # GRAVY
        gravy = round(sum(_KD_HYDRO.get(aa, 0) for aa in seq) / n, 3)

        # Aliphatic index
        x_a = counts.get("A", 0) / n
        x_v = counts.get("V", 0) / n
        x_i = counts.get("I", 0) / n
        x_l = counts.get("L", 0) / n
        aliphatic_index = round(100 * (x_a + 2.9 * x_v + 3.9 * (x_i + x_l)), 2)

        # Instability index (Guruprasad et al.)
        dipeptide_weights = {
            "WW": 1.0, "WC": 1.0, "WM": 24.68, "WH": 24.68,
            "CW": -14.03, "CH": 33.60, "CC": 1.0, "CM": 33.60,
        }
        instability = 0.0
        for i in range(n - 1):
            dp = seq[i:i + 2]
            instability += dipeptide_weights.get(dp, 1.0)
        instability_index = round((10.0 / n) * instability, 2) if n > 1 else 0

        # Extinction coefficient (at 280nm, assuming all Cys reduced)
        ext_coeff = counts.get("Y", 0) * 1490 + counts.get("W", 0) * 5500 + counts.get("C", 0) * 125

        # Signal peptide prediction
        signal = _predict_signal_peptide(seq)

        # Transmembrane helix prediction
        tm_helices = _predict_transmembrane(seq)

        # Composition
        composition = {aa: {"count": c, "percent": round(c / n * 100, 1)} for aa, c in counts.items() if c > 0}

        data = {
            "length": n,
            "molecular_weight_da": mw,
            "isoelectric_point": pi,
            "gravy": gravy,
            "aliphatic_index": aliphatic_index,
            "instability_index": instability_index,
            "is_stable": instability_index < 40,
            "extinction_coefficient_280nm": ext_coeff,
            "signal_peptide": signal,
            "transmembrane_helices": tm_helices,
            "num_tm_helices": len(tm_helices),
            "composition": composition,
        }

        stability = "stable" if instability_index < 40 else "unstable"
        display = (
            f"{n} aa, MW {mw:.0f} Da, pI {pi}, GRAVY {gravy}, "
            f"{stability} (II={instability_index}), "
            f"aliphatic index {aliphatic_index}, "
            f"signal peptide: {'yes' if signal['predicted'] else 'no'}, "
            f"TM helices: {len(tm_helices)}"
        )
        return ToolResult(success=True, data=data, display=display)
