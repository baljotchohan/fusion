from core.diligence_engine import parse_arrs_with_timeframes_from_text

text = (
    "--- DOCUMENT: pitch.pdf ---\n"
    "ARR is $12M.\n"
    "Note: Regulatory agency opened an SEC investigation in 2025.\n\n"
    "--- DOCUMENT: financials.xlsx ---\n"
    "ARR is $12.1M."
)

import re
documents = {}
doc_matches = list(re.finditer(r"--- DOCUMENT:\s*(.*?)\s*---", text))
for idx, match in enumerate(doc_matches):
    doc_name = match.group(1).strip()
    start_idx = match.end()
    end_idx = doc_matches[idx+1].start() if idx + 1 < len(doc_matches) else len(text)
    documents[doc_name] = text[start_idx:end_idx].strip()

print("DOCUMENTS:", documents)
for doc, content in documents.items():
    print(f"ARR in {doc}:", parse_arrs_with_timeframes_from_text(content))
