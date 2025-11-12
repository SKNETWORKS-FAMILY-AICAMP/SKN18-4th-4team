import os
import pandas as pd
from langchain_core.documents import Document
from langchain_community.document_loaders.base import BaseLoader

class CustomCSVLoader(BaseLoader):
    def __init__(self, file_path, content_columns, metadata_columns, sep=",", encoding="utf-8", na_fill=""):
        self.file_path = "rag/data/Data_Final.csv"
        self.content_columns = ["chunk_text"]
        self.metadata_columns = ["c_id"]
        self.sep = sep
        self.encoding = encoding
        self.na_fill = na_fill

    def load(self) -> list[Document]:
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"파일 없음: {self.file_path}")

        df = pd.read_csv(self.file_path, sep=self.sep, encoding=self.encoding).fillna(self.na_fill)
        if df.empty:
            return []

        docs = []
        for _, row in df.iterrows():
            content = " | ".join(str(row[c]) for c in self.content_columns if c in df.columns)
            meta = {c: row[c] for c in self.metadata_columns if c in df.columns}
            docs.append(Document(page_content=str(content), metadata=meta))
        return docs
