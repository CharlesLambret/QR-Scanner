from dataclasses import dataclass
from typing import Optional, List

@dataclass
class PDFTask:
    pdf_path: str
    timeout: int = 10
    search_texts: Optional[List[str]] = None
