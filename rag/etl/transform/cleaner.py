import pandas as pd
from pathlib import Path
import re

# ===== 1. 경로 설정 =====
BASE_DIR = Path(__file__).resolve().parent.parent.parent
input_path = BASE_DIR / "data" / "merged_KOR.csv"
output_path1 = BASE_DIR / "data" / "T1_column_renewed.csv"
output_path2 = BASE_DIR / "data" / "T2_numspot_renewed.csv"
output_path3 = BASE_DIR / "data" / "T2_reference_dropped.csv"
output_path4 = BASE_DIR / "data" / "T2_cleaned_quot.csv"
output_path5 = BASE_DIR / "data" / "T2_cleaned_cid_year.csv"
output_path6 = BASE_DIR / "data" / "T2_parenthesis_stripped.csv"

def column_renewal(df: pd.DataFrame, output_path1: Path) -> pd.DataFrame:
    df = pd.read_csv(input_path)
    def safe_convert_year(x):
        try:
            if pd.isna(x):
                return None
            return int(float(x))
        except Exception:
            return None

    df['creation_year'] = df['creation_year'].apply(safe_convert_year)

    def make_cid(row):
        base = row['source_spec'].strip() if isinstance(row['source_spec'], str) else "unknown"
        year = f"_{row['creation_year']}" if not pd.isna(row['creation_year']) else ""
        cid = str(row['c_id']).strip()
        return f"{base}{year}_{cid}"

    df['c_id_new'] = df.apply(make_cid, axis=1)

    df_final = df[['c_id_new', 'content']].rename(columns={'c_id_new': 'c_id'})

    df_final.to_csv(output_path1, index=False, encoding='utf-8-sig')

def num_spot_cleaning(output_path1: pd.DataFrame, output_path2: Path) -> pd.DataFrame:
    df = pd.read_csv(output_path1)

    if "content" not in df.columns:
        raise ValueError("'content' 컬럼 없음")

    def clean_num_dot_anywhere(text: str):
        if not isinstance(text, str):
            return text
        cleaned = re.sub(r'(?<!\d)\s*\d+\.\s*', ' ', text)
        return cleaned.strip()

    df["content"] = df["content"].apply(clean_num_dot_anywhere)

    df.to_csv(output_path2, index=False, encoding="utf-8-sig")

def drop_reference(output_path2: pd.DataFrame, output_path3: Path) -> pd.DataFrame:
    df = pd.read_csv(output_path2)

    def is_citation_or_reference(text_in_paren: str) -> bool:

        text = text_in_paren.strip()

        citation_keywords = [
            "그림", "표", "참조", "출처", "연구", "논문", "학회",
            "참고", "Figure", "Table", "et al", "et."
        ]

        if any(k in text for k in citation_keywords):
            return True

        if re.search(r"[A-Za-z가-힣]+,\s*(19|20)\d{2}", text):
            return True

        if re.search(r"(19|20)\d{2}\s*년", text) and any(
            k in text for k in ["연구", "보고", "결과", "가이드라인", "meta", "메타"]
        ):
            return True

        return False

    def remove_unwanted_parentheses(text: str) -> str:
        if not isinstance(text, str):
            text = "" if pd.isna(text) else str(text)

        pattern = r"\(([^()]*)\)"

        def replacer(match):
            inner = match.group(1)
            if is_citation_or_reference(inner):
                return ""
            else:
                return f"({inner})"

        cleaned = re.sub(pattern, replacer, text)

        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
        return cleaned

    text_col = "content" if "content" in df.columns else df.columns[0]
    df[text_col] = df[text_col].fillna("").astype(str).apply(remove_unwanted_parentheses)

    df.to_csv(output_path3, index=False, encoding="utf-8-sig")

def cleaned_double_quotation(output_path3: pd.DataFrame, output_path4: Path) -> pd.DataFrame:
    df = pd.read_csv(output_path3)

    df["content"] = (
        df["content"]
        .astype(str)              
        .str.replace('"', "", regex=False)
        .str.strip()               
    )

    df.to_csv(output_path4, index=False, encoding="utf-8-sig")

def clean_cid_year(output_path4: pd.DataFrame, output_path5: Path) -> pd.DataFrame:
    df = pd.read_csv(output_path4)
    df["c_id"] = (
        df["c_id"].astype(str).str.replace(r"(\d{4})\.0", r"\1", regex=True).str.strip()
    )

    df.to_csv(output_path5, index=False, encoding="utf-8-sig")

def parentheses_strip(output_path5: pd.DataFrame, output_path6: Path) -> pd.DataFrame:
    df = pd.read_csv(output_path5)

    df["content"] = (
        df["content"].astype(str).str.replace(r"\(\s+", "(", regex=True).str.replace(r"\s+\)", ")", regex=True).str.strip()
    )

    df.to_csv(output_path6, index=False, encoding="utf-8-sig")

def main():
    df = pd.read_csv(input_path)

    column_renewal(df, output_path1)
    num_spot_cleaning(output_path1, output_path2)
    drop_reference(output_path2, output_path3)
    cleaned_double_quotation(output_path3, output_path4)
    clean_cid_year(output_path4, output_path5)
    parentheses_strip(output_path5, output_path6)

    

if __name__ == "__main__":
    main()
