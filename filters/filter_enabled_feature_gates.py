import pandas as pd


def filter_enabled_feature_gates(df: pd.DataFrame) -> list:
    df = df[0]
    mask = df.iloc[:, 1].str.contains("enabled", case=False, na=False) | df.iloc[
        :, 2
    ].str.contains("enabled", case=False, na=False)
    result = [fg.split("(")[0].strip() for fg in list(df.loc[mask, df.columns[0]])]
    return result
