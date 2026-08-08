"""Phase 11 red tests: target-only masking, parent preservation, TrainCard."""

from train_samples import train_spec
from train_support import train_store
from core_samples import HASH, payloads


def test_target_only_loss_masks_prompt_tokens_without_torch_requirement():
    from facktry.train.loss import target_only_mask

    assert target_only_mask(prompt_length=3, target_length=2) == [0, 0, 0, 1, 1]


def test_parent_tuple_artifacts_remain_hash_unchanged_after_training(tmp_path, monkeypatch):
    store = train_store(tmp_path, monkeypatch)
    from facktry import train
    from facktry.train.testing import FakeBackend

    parent = payloads()["ReleaseTuple"]
    before = parent["tuple_hash"]
    result = train.run(store, "objective-valid", train_spec(parent_tuple=parent), backend=FakeBackend())
    assert result.train_card.parent_tuple_hash == before
    assert store.load_tuple(parent["tuple_hash"]).tuple_hash == before


def test_train_card_contains_repeat_exposure_teacher_and_recipe_fields(tmp_path, monkeypatch):
    store = train_store(tmp_path, monkeypatch)
    from facktry import train
    from facktry.train.testing import FakeBackend

    result = train.run(store, "objective-valid", train_spec(), backend=FakeBackend())
    card = result.train_card
    assert card.repeated_example_exposure is not None
    assert card.teacher_id
    assert card.recipe_stack_hash
    assert card.interface_hashes
    assert card.admission_report_hash == HASH
