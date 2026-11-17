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


def test_output_is_strict_json():
    import json
    json.dumps(describe_notes(scale_notes("hicaz")), ensure_ascii=False, allow_nan=False)


def test_single_pitch_piece_is_still_strict_json():
    # Only the karar sounds: every güçlü ratio is 0/0. That must be null, not Infinity.
    import json
    out = describe_notes([Note(6 * 53 + DUGAH_PC, 1.0)] * 3)
    json.dumps(out, allow_nan=False)
    assert all(f["guclu_emphasis"] is None for f in out["fits"])


def test_guclu_at_the_octave_of_the_karar_is_not_measured():
    # Mâhur's güçlü is gerdaniye; folded to one octave it is the karar itself.
    out = describe_notes(scale_notes("mahur"))
    assert next(f for f in out["fits"] if f["makam"] == "mahur")["guclu_emphasis"] is None


def test_tie_names_no_single_makam():
    # A, C, D, E, G only: uşşak, hüseynî and bûselik fit equally. File order must not pick one.
    notes = [Note(6 * 53 + DUGAH_PC + d, 0.25) for d in (0, 13, 22, 31, 44)] * 3 + [Note(6 * 53 + DUGAH_PC, 0.25)]
    out = describe_notes(notes)
    assert not out["abstain"] and out["top_makam"] is None and out["ambiguous"]
    assert {"ussak", "huseyni", "buselik"} <= set(out["makam_candidates"])


def nihavent_with_leading_tone(share=0.12):
    """Nihâvend scale plus eviç (F#), the leading tone the theory lists as a variant."""
    notes = scale_notes("nihavent", reps=1)
    total = sum(n.duration for n in notes)
    evic = Note(6 * 53 + 26, total * share / (1 - share))
    return [evic] + notes


def test_declared_variant_is_not_outside_the_theory():
    out = describe_notes(nihavent_with_leading_tone())
    assert not out["abstain"] and out["top_makam"] == "nihavent" and out["accepted_via_variants"]
    old_rule = describe_notes(nihavent_with_leading_tone(), params=Params(variants_in_abstention=False))
    assert old_rule["abstain"]


def test_variants_do_not_enter_the_ranking():
    m = measure(nihavent_with_leading_tone())
    a = compare(m, TH)
    b = compare(m, TH, Params(variants_in_abstention=False))
    assert [(f.makam, f.exact) for f in a["fits"]] == [(f.makam, f.exact) for f in b["fits"]]


def test_zero_duration_notes_rejected():
    from makam_descriptor.measure import MeasurementError
    with pytest.raises(MeasurementError):
        measure([Note(349, 0.0), Note(349, 0.25)])


@pytest.mark.parametrize("text", [
    "",                                                              # empty
    '[meta]\nsystem="x"\n',                                          # no perde / cins / makam
    '[meta]\nsystem="x"\n[perde]\nrast={pc=99}\n[cins]\n[makam]\n',    # pc out of range
    '[meta]\nsystem="x"\nsymbtr_column="Hz"\n[perde]\n[cins]\n[makam]\n',
])
def test_malformed_theory_raises_theory_error(tmp_path, text):
    bad = tmp_path / "bad.toml"
    bad.write_text(text)
    with pytest.raises(TheoryError):
        load_theory(bad)


def test_theory_names_its_symbtr_column():
    assert TH.symbtr_column == "KomaAE" and TH.without("rast").symbtr_column == "KomaAE"
