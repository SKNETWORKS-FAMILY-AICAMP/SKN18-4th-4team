import pandas as pd
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
INPUT_PATH = BASE_DIR / "data" / "T2_parenthesis_stripped.csv"
output_path = BASE_DIR / "data" / "Data_Final.csv"

def chunked2(df: pd.DataFrame, output_path: Path) -> pd.DataFrame:

    df = pd.read_csv(INPUT_PATH)

    def chunk_text(text, sentence_limit=2):
        """'.', '!', '?' 기준으로 문장 분리 후 10문장 단위로 청킹"""
        if pd.isna(text) or not isinstance(text, str):
            return []

        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        chunks, current = [], []

        for i, sent in enumerate(sentences, 1):
            current.append(sent)
            if i % sentence_limit == 0 or i == len(sentences):
                chunks.append(" ".join(current).strip())
                current = []

        return chunks

    chunk_rows = []

    for _, row in df.iterrows():
        chunks = chunk_text(row["content"], sentence_limit=2)
        for chunk in chunks:
            chunk_rows.append({
                "c_id": row["c_id"],  
                "chunk_text": chunk
            })

    chunk_df = pd.DataFrame(chunk_rows)
    chunk_df.to_csv(output_path, index=False, encoding="utf-8-sig")


def main():
    chunked2(INPUT_PATH, output_path)

if __name__ == "__main__":
    main()