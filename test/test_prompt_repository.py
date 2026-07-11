"""
PromptRepository tests:
  - seed_defaults: inserts once, idempotent, never overwrites
  - create: new version, duplicate (role, label) -> ValueError
  - get / get_by_role_label: found, missing, inactive handling
  - update_meta: description/is_active only, template untouched
  - list: role filter, active filter, ordering
"""
import pytest

from config import Config
from domain.db.engine import create_db_engine
from domain.db.prompt_repository import PromptRepository
from domain.agent.prompting.catalog import DEFAULT_PROMPT_SEEDS


@pytest.fixture()
def repo(tmp_path):
    config = Config(database_url=f"sqlite:///{(tmp_path / 'test.sqlite').as_posix()}")
    engine = create_db_engine(config)
    return PromptRepository(engine)


@pytest.fixture()
def seeded(repo):
    repo.seed_defaults(DEFAULT_PROMPT_SEEDS)
    return repo


class TestSeedDefaults:

    def test_inserts_all_on_first_run(self, repo):
        assert repo.seed_defaults(DEFAULT_PROMPT_SEEDS) == len(DEFAULT_PROMPT_SEEDS)

    def test_second_run_is_idempotent(self, seeded):
        assert seeded.seed_defaults(DEFAULT_PROMPT_SEEDS) == 0
        assert len(seeded.list(include_inactive=True)) == len(DEFAULT_PROMPT_SEEDS)

    def test_never_overwrites_existing_row(self, seeded):
        original = seeded.get_by_role_label("reviewer", "v1")
        tampered = [("reviewer", "v1", "DIFFERENT TEXT", "tampered")]
        assert seeded.seed_defaults(tampered) == 0
        assert seeded.get_by_role_label("reviewer", "v1").template == original.template

    def test_expected_roles_and_labels(self, seeded):
        pairs = {(v.agent_role, v.version_label) for v in seeded.list()}
        assert pairs == {
            ("reviewer", "v1"), ("reviewer", "v2"), ("meta_reviewer", "v1"),
            ("area_chair", "v1"), ("author_agent", "v1"),
        }


class TestCreate:

    def test_create_returns_row_with_hash_and_timestamp(self, repo):
        row = repo.create("reviewer", "v9", "Custom template", "test")
        assert row.id is not None
        assert len(row.template_hash) == 64
        assert row.created_at
        assert row.is_active is True

    def test_duplicate_role_label_raises(self, seeded):
        with pytest.raises(ValueError, match="already exists"):
            seeded.create("reviewer", "v1", "whatever")

    def test_same_label_different_role_is_allowed(self, repo):
        repo.create("reviewer", "v9", "A")
        row = repo.create("area_chair", "v9", "B")
        assert row.agent_role == "area_chair"


class TestGet:

    def test_get_by_id(self, seeded):
        row = seeded.list()[0]
        assert seeded.get(row.id).id == row.id

    def test_get_missing_raises(self, repo):
        with pytest.raises(ValueError):
            repo.get(99999)

    def test_get_by_role_label_missing_raises(self, seeded):
        with pytest.raises(ValueError):
            seeded.get_by_role_label("reviewer", "v99")

    def test_inactive_version_not_selectable_by_default(self, seeded):
        row = seeded.get_by_role_label("reviewer", "v2")
        seeded.update_meta(row.id, is_active=False)
        with pytest.raises(ValueError):
            seeded.get_by_role_label("reviewer", "v2")
        assert seeded.get_by_role_label("reviewer", "v2", only_active=False).id == row.id


class TestUpdateMeta:

    def test_updates_description_and_active_flag(self, seeded):
        row = seeded.get_by_role_label("reviewer", "v1")
        updated = seeded.update_meta(row.id, description="new desc", is_active=False)
        assert updated.description == "new desc"
        assert updated.is_active is False

    def test_template_is_never_touched(self, seeded):
        row = seeded.get_by_role_label("reviewer", "v1")
        updated = seeded.update_meta(row.id, description="x")
        assert updated.template == row.template
        assert updated.template_hash == row.template_hash

    def test_missing_id_raises(self, repo):
        with pytest.raises(ValueError):
            repo.update_meta(99999, description="x")


class TestList:

    def test_filter_by_role(self, seeded):
        rows = seeded.list(agent_role="reviewer")
        assert {v.version_label for v in rows} == {"v1", "v2"}

    def test_inactive_excluded_by_default(self, seeded):
        row = seeded.get_by_role_label("reviewer", "v2")
        seeded.update_meta(row.id, is_active=False)
        assert {v.version_label for v in seeded.list(agent_role="reviewer")} == {"v1"}
        assert len(seeded.list(agent_role="reviewer", include_inactive=True)) == 2
