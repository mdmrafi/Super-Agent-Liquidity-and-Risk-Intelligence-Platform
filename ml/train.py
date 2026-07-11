"""Stage 2b: ML liquidity model, as a comparison layer against Stage 2's EWMA
baseline -- not a replacement. Predicts balance_at_t+{HORIZON_HOURS}h per
(agent, provider), the same quantity the EWMA burn_rate already implies, and
reports MAE for both on the same held-out window.

Modeling choice: the tree regressor is fit on the *residual* over the EWMA
baseline (target - baseline_pred), not the raw balance. Raw balances span a
huge range (~1e5-1e6 BDT) dominated by each agent's opening balance, so a
model fit directly on them spends most of its capacity re-deriving what
last_balance already gives away for free. Fitting the residual points all of
that capacity at the part the baseline actually gets wrong, and floors this
model's worst case at "no better than the baseline" (a predicted residual of
0 reproduces it exactly) instead of letting it do worse.

A small hyperparameter search runs on an inner temporal split carved out of
calibration only (last ~20% of calibration by time as inner validation) --
holdout is never touched until the single final evaluation below.

Boundary: this model's output is a logged comparison figure only. It never
sets severity, never triggers an alert, never changes recommended_owner --
Stage 2's deterministic engine (engine/liquidity.py) stays the one driving
the live system.

Run with: python -m ml.train
"""
import json
import pathlib

import joblib
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from engine import data
from . import features

MODELS_DIR = pathlib.Path("ml/models")
REPORTS_DIR = pathlib.Path("ml/reports")

PARAM_GRID = [
    {"max_depth": 3, "learning_rate": 0.10, "max_iter": 200, "l2_regularization": 0.0},
    {"max_depth": 4, "learning_rate": 0.05, "max_iter": 300, "l2_regularization": 0.0},
    {"max_depth": 6, "learning_rate": 0.05, "max_iter": 300, "l2_regularization": 1.0},
    {"max_depth": 6, "learning_rate": 0.03, "max_iter": 500, "l2_regularization": 1.0},
    {"max_depth": 8, "learning_rate": 0.03, "max_iter": 500, "l2_regularization": 2.0},
]


def build_pipeline(**hgb_params):
    pre = ColumnTransformer(
        [("cat", OneHotEncoder(handle_unknown="ignore"), features.CATEGORICAL_FEATURES)],
        remainder="passthrough",
    )
    model = HistGradientBoostingRegressor(random_state=42, early_stopping=False, **hgb_params)
    return Pipeline([("pre", pre), ("model", model)])


def _reconstructed_mae(pipeline, X, baseline_pred, y_true):
    """MAE of (baseline_pred + predicted_residual) against the real target."""
    residual_pred = pipeline.predict(X)
    final_pred = baseline_pred + residual_pred
    return mean_absolute_error(y_true, final_pred), final_pred


def select_hyperparameters(train_df):
    """Time-ordered inner train/validation carve-out of calibration only, so
    tuning never sees holdout. Picks the config with the lowest reconstructed
    MAE (baseline + predicted residual) on the inner validation tail."""
    cutoff = train_df["hour_slot"].quantile(0.8)
    inner_train = train_df[train_df["hour_slot"] <= cutoff]
    inner_val = train_df[train_df["hour_slot"] > cutoff]

    X_inner_train = inner_train[features.FEATURE_COLUMNS]
    resid_inner_train = inner_train[features.TARGET_COLUMN] - inner_train[features.BASELINE_COLUMN]
    X_inner_val = inner_val[features.FEATURE_COLUMNS]

    best_params, best_mae = None, float("inf")
    print("Hyperparameter search (inner temporal split within calibration):")
    for params in PARAM_GRID:
        pipeline = build_pipeline(**params)
        pipeline.fit(X_inner_train, resid_inner_train)
        mae, _ = _reconstructed_mae(
            pipeline, X_inner_val,
            inner_val[features.BASELINE_COLUMN].to_numpy(),
            inner_val[features.TARGET_COLUMN].to_numpy(),
        )
        print(f"  {params} -> inner-val MAE {mae:,.1f} BDT")
        if mae < best_mae:
            best_mae, best_params = mae, params

    print(f"Selected: {best_params} (inner-val MAE {best_mae:,.1f} BDT)\n")
    return best_params


def _per_provider_breakdown(test_df, y_test, ml_pred, baseline_pred):
    rows = []
    for prov in sorted(test_df["provider"].unique()):
        mask = (test_df["provider"] == prov).to_numpy()
        rows.append({
            "provider": prov,
            "n": int(mask.sum()),
            "ml_mae": float(mean_absolute_error(y_test[mask], ml_pred[mask])),
            "baseline_mae": float(mean_absolute_error(y_test[mask], baseline_pred[mask])),
        })
    return rows


def main():
    calibration_raw = data.load_split("calibration")
    holdout_raw = data.load_split("holdout")

    # Train on calibration, evaluate on holdout -- the same split convention
    # Stage 2/3 already use, and it's chronological (calibration = days 1-21,
    # holdout = days 22-30), so this is already a temporal, non-shuffled split.
    train_df = features.build_training_frame(calibration_raw)
    test_df = features.build_training_frame(holdout_raw)
    print(f"Training rows: {len(train_df)}  |  Holdout eval rows: {len(test_df)}\n")

    best_params = select_hyperparameters(train_df)

    X_train = train_df[features.FEATURE_COLUMNS]
    resid_train = train_df[features.TARGET_COLUMN] - train_df[features.BASELINE_COLUMN]
    X_test, y_test = test_df[features.FEATURE_COLUMNS], test_df[features.TARGET_COLUMN]
    baseline_pred = test_df[features.BASELINE_COLUMN].to_numpy()

    pipeline = build_pipeline(**best_params)
    pipeline.fit(X_train, resid_train)

    ml_mae, ml_pred = _reconstructed_mae(pipeline, X_test, baseline_pred, y_test)
    baseline_mae = mean_absolute_error(y_test, baseline_pred)
    ml_r2 = r2_score(y_test, ml_pred)
    baseline_r2 = r2_score(y_test, baseline_pred)
    improvement_pct = (baseline_mae - ml_mae) / baseline_mae * 100

    print(f"=== Stage 2b: balance_at_t+{features.HORIZON_HOURS}h forecast, holdout comparison ===")
    print(f"{'model':<26}{'MAE (BDT)':>15}{'R2':>10}")
    print(f"{'EWMA baseline':<26}{baseline_mae:>15.1f}{baseline_r2:>10.3f}")
    print(f"{'ML (baseline + HGB resid)':<26}{ml_mae:>15.1f}{ml_r2:>10.3f}")
    print(f"\nMAE improvement over EWMA baseline: {improvement_pct:+.1f}%")

    per_provider = _per_provider_breakdown(test_df, y_test.to_numpy(), ml_pred, baseline_pred)
    for row in per_provider:
        print(f"  {row['provider']:<8} n={row['n']:<5} ml_mae={row['ml_mae']:>10,.1f}  baseline_mae={row['baseline_mae']:>10,.1f}")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODELS_DIR / "liquidity_balance_regressor.joblib")

    report = {
        "horizon_hours": features.HORIZON_HOURS,
        "modeling_target": "residual over EWMA baseline (target - baseline_pred)",
        "selected_hyperparameters": best_params,
        "train_rows": int(len(train_df)),
        "eval_rows": int(len(test_df)),
        "holdout": {
            "ewma_baseline": {"mae_bdt": float(baseline_mae), "r2": float(baseline_r2)},
            "ml_model": {"mae_bdt": float(ml_mae), "r2": float(ml_r2)},
            "mae_improvement_pct": float(improvement_pct),
        },
        "per_provider": per_provider,
        "boundary_note": (
            "Comparison figure only. Does not set severity, trigger alerts, "
            "or change recommended_owner -- engine/liquidity.py remains the "
            "engine driving the live system."
        ),
    }
    with open(REPORTS_DIR / "liquidity_balance_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nSaved model  -> {MODELS_DIR / 'liquidity_balance_regressor.joblib'}")
    print(f"Saved report -> {REPORTS_DIR / 'liquidity_balance_report.json'}")


if __name__ == "__main__":
    main()
