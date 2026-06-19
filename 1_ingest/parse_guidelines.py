"""
Stage 1: Ingest
"""

import json
import os
import re
import sys
from pathlib import Path

import pdfplumber
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_PATH = DATA_DIR / "guidelines_rules.json"

SECTION_HEADING_PATTERN = re.compile(r"^Section\s+(\d+):\s*(.+)$", re.MULTILINE)


def extract_raw_text(pdf_path):
    full_text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            full_text.append(text)
    return "\n".join(full_text)


def split_into_sections(full_text):
    matches = list(SECTION_HEADING_PATTERN.finditer(full_text))
    sections = []
    for i, match in enumerate(matches):
        section_number = match.group(1)
        title = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        section_text = full_text[start:end].strip()
        sections.append({
            "section_number": section_number,
            "title": title,
            "reference": f"Section {section_number}: {title}",
            "raw_text": section_text,
        })
    if not sections:
        sections.append({
            "section_number": "0",
            "title": "Unstructured Document",
            "reference": "Unstructured Document (no section headings found)",
            "raw_text": full_text.strip(),
        })
    return sections


def extract_atomic_rules_with_llm(sections):
    api_key = os.getenv("GROQ_API_KEY")
    all_rules = []
    rule_id_counter = 1

    if not api_key:
        print("[WARNING] GROQ_API_KEY not set. Falling back to sentence-splitting.")
        for section in sections:
            sentences = [s.strip() for s in section["raw_text"].split(".") if s.strip()]
            for sentence in sentences:
                all_rules.append({
                    "rule_id": f"R{rule_id_counter:03d}",
                    "guideline_reference": section["reference"],
                    "rule_text": sentence + ".",
                })
                rule_id_counter += 1
        return all_rules

    from groq import Groq
    client = Groq(api_key=api_key)

    for section in sections:
        prompt = f"""Extract checkable compliance rules from this guidelines
                        section. Return a JSON array of atomic, individually checkable statements.
                        Each statement should describe ONE specific, verifiable expectation. Skip
                        purely descriptive sentences. Return ONLY a valid JSON array of strings,
                        no markdown, no explanation.

Section: {section['title']}
Text:
{section['raw_text']}
"""
        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            raw = response.choices[0].message.content.strip()
            raw = re.sub(r"^```json\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
            statements = json.loads(raw)
        except Exception as e:
            print(f"[WARNING] LLM extraction failed for '{section['title']}': {e}")
            statements = [s.strip() + "." for s in section["raw_text"].split(".") if s.strip()]

        for statement in statements:
            all_rules.append({
                "rule_id": f"R{rule_id_counter:03d}",
                "guideline_reference": section["reference"],
                "rule_text": statement,
            })
            rule_id_counter += 1

    return all_rules


def run_ingest(pdf_path):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] Extracting text from {pdf_path}")
    full_text = extract_raw_text(pdf_path)
    print("[INFO] Splitting into sections")
    sections = split_into_sections(full_text)
    print(f"[INFO] Found {len(sections)} sections")
    print("[INFO] Extracting atomic rules")
    rules = extract_atomic_rules_with_llm(sections)
    print(f"[INFO] Extracted {len(rules)} atomic rules")
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump({"source_pdf": str(pdf_path), "sections": sections, "rules": rules}, f, indent=2)
    print(f"[INFO] Saved structured guidelines to {OUTPUT_PATH}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python 1_ingest/parse_guidelines.py <path_to_guidelines.pdf>")
        sys.exit(1)
    run_ingest(sys.argv[1])
