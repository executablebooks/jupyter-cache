import pytest

from jupyter_cache.cache.db import create_db, NbCommitRecord, Setting


def test_setting(tmp_path):
    db = create_db(tmp_path)
    Setting.set_value("a", 1, db)
    assert Setting.get_value("a", db) == 1
    assert Setting.get_dict(db) == {"a": 1}


def test_nb_record(tmp_path):
    db = create_db(tmp_path)
    bundle = NbCommitRecord.create_record("a", "b", db)
    assert bundle.hashkey == "b"
    with pytest.raises(ValueError):
        NbCommitRecord.create_record("a", "b", db)
    NbCommitRecord.create_record("a", "c", db, data="a")
    assert NbCommitRecord.record_from_hashkey("b", db).uri == "a"
    assert {b.hashkey for b in NbCommitRecord.records_from_uri("a", db)} == {"b", "c"}
