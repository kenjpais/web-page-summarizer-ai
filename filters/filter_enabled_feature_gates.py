import pandas as pd


def filter_enabled_feature_gates(df: pd.DataFrame) -> list:
    df = df[0]
    feature_gates = df.loc[
        (
            df.drop(columns="FeatureGate")
            .map(lambda x: "enabled" in str(x).lower())
            .all(axis=1)
        ),
        "FeatureGate",
    ].tolist()

    result = [
        feature_gate_txt.split("(")[0].strip() for feature_gate_txt in feature_gates
    ]

    return result
