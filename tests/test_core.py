"""Tests that pin down the theory and the two-resolution logic. No SymbTr data needed."""
import pytest

from makam_descriptor import Params, describe_notes, load_theory
from makam_descriptor.consistency import compare, share_on
from makam_descriptor.measure import measure
from makam_descriptor.symbtr import Note
from makam_descriptor.theory import TheoryError

TH = load_theory()
RAST_PC, DUGAH_PC = 31, 40


def scale_notes(makam_key, octave=6, reps=4):
    """A synthetic piece: the makam's scale, repeated, ending on the karar."""
    m = TH.makams[makam_key]
    base = octave * 53 + m.karar_pc
    seq = [base + d for d in sorted(m.degrees)] * reps + [base]
    return [Note(k, 0.25) for k in seq]


def test_all_dizi_span_one_octave():
    for m in TH.makams.values():
        assert sum(m.intervals) == 53
        assert len(m.degrees) == 7


def test_rast_mahur_differ_by_one_comma_in_third_and_seventh():
    r, h = TH.makams["rast"].degrees, TH.makams["mahur"].degrees
    assert sorted(r ^ h) == [17, 18, 48, 49]


@pytest.mark.parametrize("key", list(TH.makams))
def test_each_makam_identifies_itself(key):
    c = compare(measure(scale_notes(key)), TH)
    assert c["ranked_top"] == key and not c["abstain"]


def test_tolerance_erases_rast_mahur_difference():
    m = measure(scale_notes("mahur"))
    r, h = TH.makams["rast"].degrees, TH.makams["mahur"].degrees
    assert share_on(m.pcd, h) == pytest.approx(1.0)
    assert share_on(m.pcd, r) < 1.0
    assert share_on(m.pcd, r, 1) == pytest.approx(share_on(m.pcd, h, 1))


def test_unknown_karar_abstains():
    notes = scale_notes("rast")[:-1] + [Note(6 * 53 + 48, 0.25)]   # ends on segah
    out = describe_notes(notes)
    assert out["abstain"] and out["makam_candidates"] == []
    assert "karar" in out["abstain_reasons"][0]


def test_off_scale_material_abstains():
    notes = scale_notes("rast")
    off = [Note(6 * 53 + RAST_PC + 13, 0.25)] * 10   # nim hisar region, outside rast even with slack
    out = describe_notes(off + notes)
    assert out["abstain"] and out["out_of_theory_share"] > 0.1


def test_leave_one_out_flags_hicaz():
    out = compare(measure(scale_notes("hicaz")), TH.without("hicaz"))
    assert out["abstain"]


def test_bad_theory_rejected(tmp_path):
    bad = tmp_path / "bad.toml"
    bad.write_text('[meta]\nsystem="x"\n[perde]\nrast={pc=31}\nneva={pc=9}\n[cins]\na={intervals=[9,9]}\n'
                   '[makam.x]\nkarar="rast"\ndizi=["a"]\nguclu="neva"\nsource="t"\n')
    with pytest.raises(TheoryError):
        load_theory(bad)


def test_output_is_json_serialisable():
    import json
    json.dumps(describe_notes(scale_notes("hicaz")), ensure_ascii=False)
