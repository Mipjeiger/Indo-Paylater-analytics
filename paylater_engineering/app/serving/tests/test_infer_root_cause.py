import pandas as pd
import numpy as np

from app.serving.infer_root_cause import _build_frame
from app.training.flows.task3_root_cause import LGBMRootCausePyfunc

def test_build_frame_preserves_expected_feature_order(monkeypatch):
    monkeypatch.setattr(
        "app.serving.infer_root_cause._resolve_version",
        lambda version=None: "1",
    )
    monkeypatch.setattr(
        "app.serving.infer_root_cause._cat_categories",
        lambda version=None: {"gender": ["Female", "Male"]},
    )

    frame = _build_frame(
        {"age": 28, "gender": "Female", "province": "Bali"},
        ("age", "gender", "province"),
        "1",
    )

    assert list(frame.columns) == ["age", "gender", "province"]
    assert frame.loc[0, "gender"] == "Female"


def test_build_frame_rejects_missing_features():
    try:
        _build_frame({"age": 28}, ("age", "gender"), "1")
    except ValueError as exc:
        assert "gender" in str(exc)
    else:
        raise AssertionError("Missing features must raise ValueError")


class LegacyCategoricalBooster:
    pandas_categorical = [["Female", "Male"]]

    def predict(self, frame):
        assert isinstance(frame["gender"].dtype, pd.CategoricalDtype)
        return np.array([[0.8, 0.2]])


class NumericCategoricalBooster:
    pandas_categorical = None

    def predict(self, frame):
        assert pd.api.types.is_integer_dtype(frame["gender"].dtype)
        assert frame.loc[0, "gender"] == 0
        return np.array([[0.8, 0.2]])


def test_pyfunc_supports_legacy_category_dtype_model():
    model = LGBMRootCausePyfunc(
        LegacyCategoricalBooster(),
        {"gender": ["Female", "Male"]},
        ["A", "B"],
    )

    result = model.predict(None, pd.DataFrame([{"gender": "Female"}]))
    assert result.shape == (1, 2)


def test_pyfunc_supports_retrained_numeric_category_model():
    model = LGBMRootCausePyfunc(
        NumericCategoricalBooster(),
        {"gender": ["Female", "Male"]},
        ["A", "B"],
    )

    result = model.predict(None, pd.DataFrame([{"gender": "Female"}]))
    assert result.shape == (1, 2)
