from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool

# Monoisotopic residue masses (Da) — standard 20 amino acids
AA_MW: dict[str, float] = {
    "A": 71.03711, "R": 156.10111, "N": 114.04293, "D": 115.02694,
    "C": 103.00919, "E": 129.04259, "Q": 128.05858, "G": 57.02146,
    "H": 137.05891, "I": 113.08406, "L": 113.08406, "K": 128.09496,
    "M": 131.04049, "F": 147.06841, "P": 97.05276, "S": 87.03203,
    "T": 101.04768, "W": 186.07931, "Y": 163.06333, "V": 99.06841,
}
WATER_MW = 18.01056

# pKa values for isoelectric point calculation (EMBOSS scale)
PKA_SIDE: dict[str, float] = {
    "D": 3.65, "E": 4.25, "C": 8.18, "Y": 10.07,
    "H": 6.00, "K": 10.53, "R": 12.48,
}
PKA_N_TERM = 8.60
PKA_C_TERM = 3.60

# Kyte-Doolittle hydropathy scale
KD_HYDROPATHY: dict[str, float] = {
    "A": 1.8, "R": -4.5, "N": -3.5, "D": -3.5, "C": 2.5,
    "E": -3.5, "Q": -3.5, "G": -0.4, "H": -3.2, "I": 4.5,
    "L": 3.8, "K": -3.9, "M": 1.9, "F": 2.8, "P": -1.6,
    "S": -0.8, "T": -0.7, "W": -0.9, "Y": -1.3, "V": 4.2,
}


def _net_charge(seq: str, ph: float) -> float:
    """Net charge at given pH via Henderson-Hasselbalch."""
    charge = 0.0
    # N-terminus (positive)
    charge += 1.0 / (1.0 + 10 ** (ph - PKA_N_TERM))
    # C-terminus (negative)
    charge -= 1.0 / (1.0 + 10 ** (PKA_C_TERM - ph))
    for aa in seq:
        if aa in ("D", "E", "C", "Y"):
            charge -= 1.0 / (1.0 + 10 ** (PKA_SIDE[aa] - ph))
        elif aa in ("H", "K", "R"):
            charge += 1.0 / (1.0 + 10 ** (ph - PKA_SIDE[aa]))
    return charge


def _isoelectric_point(seq: str) -> float:
    """Bisection method to find pH where net charge ≈ 0."""
    lo, hi = 0.0, 14.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if _net_charge(seq, mid) > 0:
            lo = mid
        else:
            hi = mid
    return round((lo + hi) / 2.0, 2)


@register_tool
class SequenceAnalysisTool(ProteinTool):
    name: str = "sequence_analysis"
    description: str = (
        "Analyze a protein sequence locally. Returns molecular weight, "
        "isoelectric point (pI), amino acid composition, GRAVY hydropathy score, "
        "and extinction coefficients. No external API call — instant results."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "sequence": {
                "type": "string",
                "description": "Protein sequence in single-letter amino acid codes (e.g. MVLSPADKTNVKA). FASTA headers are stripped automatically.",
            }
        },
        "required": ["sequence"],
    }

    def run(self, **kwargs) -> ToolResult:
        raw_seq = kwargs["sequence"].strip()
        # Strip FASTA header
        if raw_seq.startswith(">"):
            raw_seq = "\n".join(raw_seq.split("\n")[1:])
        seq = "".join(c.upper() for c in raw_seq if c.isalpha())

        if not seq:
            return ToolResult(success=False, error="Empty sequence provided")

        unknown = set(seq) - set(AA_MW)
        if unknown:
            return ToolResult(
                success=False,
                error=f"Unknown amino acid(s): {', '.join(sorted(unknown))}",
            )

        length = len(seq)

        # Molecular weight
        mw = sum(AA_MW[aa] for aa in seq) + WATER_MW

        # Isoelectric point
        pi = _isoelectric_point(seq)

        # Amino acid composition
        composition = {}
        for aa in sorted(set(seq)):
            count = seq.count(aa)
            composition[aa] = {"count": count, "percent": round(count / length * 100, 1)}

        # GRAVY (grand average of hydropathy)
        gravy = round(sum(KD_HYDROPATHY[aa] for aa in seq) / length, 3)

        # Extinction coefficients (Pace et al.)
        n_w = seq.count("W")
        n_y = seq.count("Y")
        n_c = seq.count("C")
        ext_reduced = n_w * 5500 + n_y * 1490
        ext_oxidized = ext_reduced + (n_c // 2) * 125

        data = {
            "length": length,
            "molecular_weight_da": round(mw, 2),
            "isoelectric_point": pi,
            "gravy": gravy,
            "extinction_coefficient_reduced": ext_reduced,
            "extinction_coefficient_oxidized": ext_oxidized,
            "composition": composition,
        }
        display = (
            f"{length} aa, MW={mw:.0f} Da, pI={pi}, GRAVY={gravy}"
        )
        return ToolResult(success=True, data=data, display=display)
