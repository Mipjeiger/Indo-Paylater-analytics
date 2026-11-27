import pytest

from app.feast.redis_insight_mirror import (
    MIRROR_KEY_PREFIX,
    MIRROR_TTL_SECONDS,
    mirror_borrowers,
    readable_fields,
)


def test_readable_fields_converts_online_response_to_text():
    response = {
        "borrower_id": ["ID_DEB_1"],
        "borrower_profile__gender": ["Female"],
        "borrower_profile__age": [28],
        "borrower_profile__province": [None],
        "borrower_profile__is_high_risk": [False],
        "borrower_profile__metadata": [{"source": "paylater"}],
    }

    assert readable_fields(response, "ID_DEB_1") == {
        "borrower_profile__gender": "Female",
        "borrower_profile__age": "28",
        "borrower_profile__province": "null",
        "borrower_profile__is_high_risk": "false",
        "borrower_profile__metadata": '{"source": "paylater"}',
    }


def test_readable_fields_rejects_missing_entity():
    with pytest.raises(ValueError, match="did not contain borrower"):
        readable_fields({"gender": ["Female"]}, "ID_DEB_1")


class FakePipeline:
    def __init__(self, client):
        self.client = client
        self.commands = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def delete(self, key):
        self.commands.append(("delete", key))

    def hset(self, key, mapping):
        self.commands.append(("hset", key, mapping))

    def expire(self, key, ttl):
        self.commands.append(("expire", key, ttl))

    def execute(self):
        for command in self.commands:
            if command[0] == "hset":
                self.client.hashes[command[1]] = command[2]
            elif command[0] == "expire":
                self.client.ttls[command[1]] = command[2]


class FakeRedis:
    def __init__(self):
        self.hashes = {}
        self.ttls = {}

    def pipeline(self, transaction):
        assert transaction is False
        return FakePipeline(self)


class FakeFeatureResponse:
    def __init__(self, values):
        self.values = values

    def to_dict(self):
        return self.values


class FakeFeatureStore:
    def __init__(self):
        self.batches = []

    def get_online_features(self, features, entity_rows, full_feature_names):
        assert features == ["borrower_profile:gender"]
        assert full_feature_names is True
        ids = [row["borrower_id"] for row in entity_rows]
        self.batches.append(ids)
        reversed_ids = list(reversed(ids))
        genders = [
            "Female" if borrower_id != "ID_DEB_2" else "Male"
            for borrower_id in reversed_ids
        ]
        return FakeFeatureResponse(
            {
                "borrower_id": reversed_ids,
                "borrower_profile__gender": genders,
            }
        )


def test_mirror_borrowers_writes_all_ids_in_bounded_batches():
    store = FakeFeatureStore()
    redis_client = FakeRedis()
    borrower_ids = ["ID_DEB_1", "ID_DEB_2", "ID_DEB_3"]

    mirrored = mirror_borrowers(
        store,
        redis_client,
        borrower_ids,
        ["borrower_profile:gender"],
        batch_size=2,
    )

    assert mirrored == 3
    assert store.batches == [["ID_DEB_1", "ID_DEB_2"], ["ID_DEB_3"]]
    assert redis_client.hashes == {
        f"{MIRROR_KEY_PREFIX}ID_DEB_1": {"borrower_profile__gender": "Female"},
        f"{MIRROR_KEY_PREFIX}ID_DEB_2": {"borrower_profile__gender": "Male"},
        f"{MIRROR_KEY_PREFIX}ID_DEB_3": {"borrower_profile__gender": "Female"},
    }
    assert redis_client.ttls == {
        f"{MIRROR_KEY_PREFIX}{borrower_id}": MIRROR_TTL_SECONDS
        for borrower_id in borrower_ids
    }


def test_mirror_borrowers_rejects_mismatched_response_ids():
    class MismatchedFeatureStore(FakeFeatureStore):
        def get_online_features(self, features, entity_rows, full_feature_names):
            return FakeFeatureResponse(
                {
                    "borrower_id": ["ID_DEB_OTHER"],
                    "borrower_profile__gender": ["Female"],
                }
            )

    store = MismatchedFeatureStore()
    redis_client = FakeRedis()

    with pytest.raises(ValueError, match="did not match the request"):
        mirror_borrowers(
            store,
            redis_client,
            ["ID_DEB_1"],
            ["borrower_profile:gender"],
            batch_size=1,
        )
