"""Reader, tool envelope and command line, on a synthetic score. No SymbTr data needed."""
import json

import pytest

from makam_descriptor import call_tool, describe
from makam_descriptor.__main__ import main
from makam_descriptor.symbtr import SymbTrFormatError, read_symbtr_txt

HEADER = "Sira\tKod\tNota53\tNotaAE\tKoma53\tKomaAE\tPay\tPayda\tMs\tLNS\tBas\tSoz1\tOffset"


def row(i, kod, k53, kae, pay, payda, soz=""):
    return f"{i}\t{kod}\tX\tX\t{k53}\t{kae}\t{pay}\t{payda}\t500\t95\t96\t{soz}\t0.5"


# An uşşak-like fragment on dügâh (A4 = 305). Segâh is 312 in the 53-TET column
# and 313 in the AEU column, as in SymbTr.
ROWS = [
    row(1, 51, -1, -1, 0, 0, "Sofyan"),          # usul: control row
    row(2, 9, 305, 305, 1, 4, "A"),
    row(3, 9, 312, 313, 1, 4, 'say "quoted'),    # a stray quote in the lyrics
    row(4, 8, 318, 318, 0, 0),                   # grace note: no time of its own
    row(5, 9, 318, 318, 1, 4),
    row(6, 12, 327, 327, 1, 4),                  # trill: an ordinary sounding note
    row(7, 9, -1, -1, 1, 4),                     # rest
    row(8, 9, 318, 318, 1, 8),
    row(9, 9, 312, 313, 1, 8),
    row(10, 7, 305, 305, 1, 2),                  # tremolo on the final: this is the karar
    row(11, 53, -1, -1, 0, 0),                   # phrase boundary
]


@pytest.fixture
def score(tmp_path):
    p = tmp_path / "ussak--sarki--sofyan--deneme--.txt"
    p.write_text("\n".join([HEADER, *ROWS]) + "\n", encoding="utf-8")
    return p


def test_reader_counts_sounding_notes_only(score):
    s = read_symbtr_txt(score)
    assert s.makam_label == "ussak" and s.skipped_rows == 0
    assert len(s.notes) == 7                     # rows 2, 3, 5, 6, 8, 9, 10
    assert sum(n.duration for n in s.notes) == pytest.approx(1.75)


def test_ornamented_final_note_is_the_karar(score):
    assert read_symbtr_txt(score).notes[-1].koma53 == 305
    assert describe(score)["karar"] == "dügâh"


def test_quote_in_lyrics_does_not_swallow_rows(score):
    assert [n.koma53 for n in read_symbtr_txt(score).notes][1:3] == [313, 318]


def test_pitch_column_is_selectable_and_recorded(score):
    assert read_symbtr_txt(score, "KomaAE").notes[1].koma53 == 313
    assert read_symbtr_txt(score, "Koma53").notes[1].koma53 == 312
    with pytest.raises(ValueError):
        read_symbtr_txt(score, "Ms")
    assert describe(score)["provenance"]["pitch_column"] == "KomaAE"
    assert describe(score, pitch_column="Koma53")["provenance"]["pitch_column"] == "Koma53"


def test_bom_is_tolerated(tmp_path):
    p = tmp_path / "rast--x.txt"
    p.write_bytes(("\ufeff" + "\n".join([HEADER, row(1, 9, 296, 296, 1, 4)]) + "\n").encode("utf-8"))
    assert len(read_symbtr_txt(p).notes) == 1


def test_unparsable_note_rows_are_counted_not_hidden(tmp_path):
    p = tmp_path / "rast--x.txt"
    p.write_text("\n".join([HEADER, row(1, 9, 296, 296, 1, 4), row(2, 9, "G4", "G4", 1, 4)]) + "\n", encoding="utf-8")
    s = read_symbtr_txt(p)
    assert len(s.notes) == 1 and s.skipped_rows == 1
    assert describe(p)["provenance"]["unparsed_rows"] == 1


def test_wrong_file_type_is_reported_as_such(tmp_path):
    p = tmp_path / "notes.txt"
    p.write_text("this is not a score\n", encoding="utf-8")
    with pytest.raises(SymbTrFormatError):
        read_symbtr_txt(p)


def test_call_tool_never_raises(tmp_path, score):
    assert call_tool({"path": str(score)})["karar"] == "dügâh"
    assert call_tool({"path": str(tmp_path / "missing.txt")})["error"]["type"] == "file_not_found"
    assert call_tool({})["error"]["type"] == "bad_arguments"
    assert call_tool({"path": str(score), "pitch_column": "Ms"})["error"]["type"] == "bad_arguments"
    assert call_tool({"path": 3})["error"]["type"] == "bad_arguments"
    bad = tmp_path / "bad.txt"
    bad.write_text("nope\n", encoding="utf-8")
    assert call_tool({"path": str(bad)})["error"]["type"] == "bad_format"
    rests = tmp_path / "rests.txt"
    rests.write_text("\n".join([HEADER, row(1, 9, -1, -1, 1, 4)]) + "\n", encoding="utf-8")
    assert call_tool({"path": str(rests)})["error"]["type"] == "no_notes"


def test_cli_one_score_prints_one_object(score, capsys):
    assert main([str(score)]) == 0
    assert json.loads(capsys.readouterr().out)["input"]["name"] == score.stem


def test_cli_several_scores_print_one_valid_document(score, tmp_path, capsys):
    assert main([str(score), str(tmp_path / "missing.txt")]) == 1
    doc = json.loads(capsys.readouterr().out)
    assert isinstance(doc, list) and len(doc) == 2 and "error" in doc[1]
