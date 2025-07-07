import pandas as pd


def filter_enabled_feature_gates(df: pd.DataFrame) -> list:
    return df.loc[
        (
            df.drop(columns="FeatureGate")
            .map(lambda x: "enabled" in str(x).lower())
            .all(axis=1)
        ),
        "FeatureGate",
    ].tolist()
