"""Test-only training fixture helpers."""

from core_samples import payloads
from govern_support import frozen_store


def train_store(tmp_path, monkeypatch):
    store = frozen_store(tmp_path, monkeypatch)
    from facktry import types

    store.save_admission_report("objective-valid", types.AdmissionReport.from_dict(payloads()["AdmissionReport"]))
    return store
