from pathlib import Path

import pandas as pd
import yaml
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/adult.csv"
OUT_DIR = ROOT / "data/processed"
# fnlwgt is a census sampling weight (not a property of the person);
# education is the text twin of education.num - both dropped.
DROP = ["fnlwgt", "education"]


def main() -> None:
    params = yaml.safe_load((ROOT / "params.yaml").read_text())["prepare"]
    df = pd.read_csv(RAW, skipinitialspace=True, na_values="?")
    df = df.drop(columns=DROP)
    df["target"] = (df.pop("income").str.strip() == ">50K").astype(int)
    cat_cols = df.select_dtypes("object").columns
    df[cat_cols] = df[cat_cols].fillna("missing")      # '?' in workclass/occupation/native.country

    train, test = train_test_split(
        df, test_size=params["test_size"], random_state=params["seed"], stratify=df["target"]
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    train.to_csv(OUT_DIR / "train.csv", index=False)
    test.to_csv(OUT_DIR / "test.csv", index=False)
    print(f"Train: {len(train)}, Test: {len(test)}, positive rate: {df['target'].mean():.3f}")


if __name__ == "__main__":
    main()
