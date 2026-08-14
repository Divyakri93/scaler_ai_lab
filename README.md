# PII Redaction Tool

A production-grade, local, offline Python command-line utility that automatically detects personally identifiable information (PII) inside Microsoft Word (`.docx`) documents, replaces them with consistent and realistic synthetic alternatives, and evaluates its own detection performance against a manually annotated ground-truth benchmark.

---

## 1. Overview
Redacting corporate documents (such as prospectus files, employee databases, or legal contracts) is critical for compliance (GDPR, HIPAA, CCPA). Simple blacking out of text or replacing names with labels like `[REDACTED_NAME]` degrades document utility, makes testing hard, and ruins readability.

This tool solves these issues by:
*   **Preserving Visual Layout**: Splicing modifications directly into Word's underlying XML runs, retaining original fonts, sizes, colors, and styles (like bolding and italics).
*   **Generating Realistic Synthetic Data**: Utilizing the `Faker` library to generate realistic names, addresses, emails, credit cards, dates, and IP addresses.
*   **Guaranteeing Cross-Document Consistency**: Using a stateful `MappingStore` to ensure the same PII (e.g. "Alice Smith") gets replaced by the same synthetic name (e.g. "John Doe") everywhere in the document.
*   **Enforcing Related Entity Alignment**: Reconstructing emails based on name mappings (e.g., mapping `alice.smith@gmail.com` to `john.doe@example.com` if `Alice Smith` became `John Doe`).
*   **Evaluating Performance**: Comparing detections block-by-block against a golden benchmark to generate metrics (Precision, Recall, F1-Score) and compiling a formal error report.

---

## 2. Architecture & Processing Flow

The system operates as an offline pipeline. All text extraction, detection, conflict resolution, and rewriting are executed locally, satisfying strict security and offline data-handling constraints.

```
Input DOCX
    │
    ▼
Document Parser (DocxReader) ──► Assembles Paragraphs, Tables, Headers, Footers
    │
    ▼
Hybrid Detection Pipeline:
 ├── Regex Detector (Emails, SSNs, CCs, IPs, Phones, Dates)
 ├── spaCy NER Detector (Person Names, Organizations)
 └── Contextual Rules Engine (DOB context checks, Street/Unit/Zip Address heuristics)
    │
    ▼
Detection Aggregator ──► Compiles candidate detections
    │
    ▼
Conflict Resolver ──► Resolves overlapping intervals based on Confidence & Length
    │
    ▼
PII Entity Objects (Pydantic validated)
    │
    ▼
Replacement Engine ──► Generates synthetic values & maintains Mapping Store caches
    │
    ▼
Document Reconstruction (DocxWriter) ──► Splices replacements right-to-left into XML Runs
    │
    ▼
Redacted DOCX Output
    │
    ▼
Evaluation Engine ──► Compares against Ground Truth JSON ──► Generates Report.md
```

---

## 3. Supported PII Categories

The tool supports the following 9 mandatory PII categories:

| PII Category | Detection Strategy | Confidence | Default Threshold | Synthetic Replacement |
| :--- | :--- | :---: | :---: | :--- |
| **`FULL_NAME`** | spaCy NER (`PERSON` label) | `0.85` | `0.80` | Seeded Faker name |
| **`EMAIL`** | RFC 5322-compliant Regex | `0.99` | `0.95` | Seeded Faker / Aligned email |
| **`PHONE`** | Lookbehind regex for local/intl formats | `0.95` | `0.85` | Seeded Faker phone |
| **`COMPANY_NAME`** | spaCy NER (`ORG` label) | `0.80` | `0.80` | Seeded Faker company |
| **`ADDRESS`** | Street-suffix, unit, and ZIP heuristics | `0.75` | `0.70` | Flattened Faker address |
| **`SSN`** | Pattern match (`XXX-XX-XXXX`) | `0.99` | `0.95` | Seeded Faker SSN |
| **`CREDIT_CARD`** | Pattern match + Luhn Algorithm validation | `0.99` | `0.95` | Seeded Faker CC |
| **`DATE_OF_BIRTH`** | Date regex + birth keyword lookback | `0.90` | `0.85` | Age 18–90 date, matched format |
| **`IP_ADDRESS`** | IPv4 (0-255 octets) & IPv6 regexes | `0.99` | `0.95` | Seeded Faker IPv4/IPv6 |

*The architecture is modular; new detectors can be added by implementing the [BaseDetector](src/pii_redactor/detectors/base.py) interface.*

---

## 4. Project Structure

```text
pii-redaction-tool/
│
├── src/
│   └── pii_redactor/
│       ├── __init__.py
│       ├── config.py           # Configuration management (Pydantic model)
│       ├── models.py           # Core PIIEntity definition and RunMapping
│       ├── cli.py              # Command-line entry points
│       │
│       ├── document/
│       │   ├── __init__.py
│       │   ├── reader.py       # Extract text from Paragraphs, Tables, Headers
│       │   ├── writer.py       # Write back modifications to DOCX runs
│       │   └── processor.py    # Pipeline coordinator (orchestrates pipeline)
│       │
│       ├── detectors/
│       │   ├── __init__.py
│       │   ├── base.py         # Base class for all detectors
│       │   ├── regex_detector.py # Regex rules (Emails, SSNs, IP, CC, Phone)
│       │   ├── ner_detector.py   # spaCy NER wrapper
│       │   ├── contextual_detector.py # Validates DOB & Address contextual patterns
│       │   └── aggregator.py   # Conflict resolver (handles overlapping spans)
│       │
│       ├── replacement/
│       │   ├── __init__.py
│       │   ├── mapping_store.py  # Cache maps (e.g., Original -> Synthetic)
│       │   ├── faker_provider.py # Generates seeded fake data
│       │   └── replacement_engine.py # Links mapping store with faker providers
│       │
│       ├── evaluation/
│       │   ├── __init__.py
│       │   ├── ground_truth.py # Loads ground truth files
│       │   ├── evaluator.py    # Computes TP, FP, FN, Precision, Recall, F1
│       │   └── report.py       # Generates markdown reports
│       │
│       └── utils/
│           ├── __init__.py
│           ├── logging.py      # Secure logger (filters out potential raw PII)
│           └── text.py         # String utilities
│
├── tests/
│   ├── __init__.py
│   ├── unit/                   # Unit tests per module
│   └── integration/            # DOCX input-to-output tests
│
├── input/                      # Input directory for CLI
├── output/                     # Redacted output documents
├── evaluation/
│   ├── ground_truth.json       # Golden annotations dataset
│   └── reports/                # Location for generated evaluation reports
│
├── requirements.txt            # Python dependencies
├── pyproject.toml              # Ruff, Black, and Pytest configuration
└── README.md                   # Full product overview
```

---

## 5. Installation & Setup

### Prerequisites
*   Python 3.11 or Python 3.12 (Python 3.12 recommended for spaCy wheels).
*   Windows PowerShell or Linux terminal.

### 1. Initialize Virtual Environment
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

### 2. Install Pinned Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Download the spaCy Model
```powershell
python -m spacy download en_core_web_sm
```

---

## 6. CLI Usage & Examples

Verify execution using the package CLI entry point:

### 1. Basic Redaction
Redact a DOCX file using a random Faker seed:
```powershell
$env:PYTHONPATH="src"
python -m pii_redactor.cli -i input/sample_document.docx -o output/redacted.docx
```

### 2. Deterministic Redaction
Specify a random seed (e.g., `42`) to ensure that identical replacements are generated on repeated runs:
```powershell
$env:PYTHONPATH="src"
python -m pii_redactor.cli -i input/sample_document.docx -o output/redacted.docx --seed 42
```

### 3. Redaction & Performance Evaluation
Execute the redaction pipeline, compare findings block-by-block against the ground-truth benchmark, print Precision/Recall/F1-scores, and generate a markdown evaluation report:
```powershell
$env:PYTHONPATH="src"
python -m pii_redactor.cli -i input/sample_document.docx -o output/redacted.docx --seed 42 --evaluate --ground-truth evaluation/ground_truth.json --report evaluation/reports/evaluation_report.md
```

---

## 7. Testing

The tool has 100% locally runnable tests with **30 passing unit and integration tests** checking:
*   Structured detections (Luhn validation, invalid IP octets, formatted phone bounds).
*   Contextual boundaries (negative DOB checks, merging overlapping street addresses).
*   Replacement Engine (consistency caching, determinism seeds, name-to-email token alignments).
*   DOCX Reader/Writer (run-level styling preservation).
*   CLI and Argument parsing.

To run the full test suite:
```powershell
.\venv\Scripts\pytest.exe tests/
```

---

## 8. Performance Evaluation Results & Error Analysis

The tool was evaluated against the manually annotated `evaluation/ground_truth.json` golden standard.

### Core Metrics
*   **Overall Precision**: `0.6667` (66.67%)
*   **Overall Recall**: `0.9231` (92.31%)
*   **Overall F1-Score**: `0.7742` (77.42%)
*   **Overall Accuracy**: `0.6316` (63.16%)
*   **True Positives (TP)**: `12`
*   **False Positives (FP)**: `6`
*   **False Negatives (FN)**: `1`

### Detailed Error Analysis & Design Trade-offs
A deep-dive of our evaluation results reveals the following system behaviors:

1.  **Conflict-Resolution Clashing (The Missed Address)**:
    *   *Observation*: The tool missed the address `"Flat 201, Tower B, Sector 62, Noida"` (False Negative) and incorrectly flagged `"Noida"` as a `FULL_NAME` (False Positive).
    *   *Cause*: The contextual address detector matched the address block with confidence `0.75`. The spaCy model misclassified the city `"Noida"` as a `PERSON` with confidence `0.85`. Because they overlapped, the priority-based resolver prioritized the higher-confidence `PERSON` (0.85) and discarded the entire overlapping `ADDRESS` span (0.75).
    *   *Mitigation*: Adjust default NER scores or add a dependency rule: `ADDRESS` spans should never be overridden by overlapping semantic tags unless the semantic tag has a verified structural validation (like an email or phone number).
2.  **Small NER Model Limitations (The spaCy False Positives)**:
    *   *Observation*: The tool flagged `"Footer info - Page 1"`, `"Applicant Profile"`, and `"Date of Birth"` as names/organizations (False Positives).
    *   *Cause*: The fast statistical model (`en_core_web_sm`) struggles with parsing context in single short sentences or headers, mistaking capitalized words for proper nouns.
    *   *Mitigation*: Upgrading to transformer-based models (e.g. `en_core_web_trf` or a local RoBERTa model) significantly increases precision but adds CUDA GPU requirements and execution latency.

---

## 9. Security Considerations

To support strict compliance requirements, the tool enforces these safety mechanisms:
*   **Fully Local execution**: No cloud APIs are utilized. Detections are performed using regex and local spaCy models. Fake values are generated using local Faker providers.
*   **Sanitized Logging**: The logger formatted strings do not output raw document lines or redacted entities. They print block IDs, offsets, and count metrics only.
*   **Exception Safety**: File missing or parsing error exceptions do not echo out document contents, preventing PII leaks in stack traces.

---

## 10. Design Decisions & Interview Trade-offs

### Q: Why did you write a custom run-level splicing writer instead of using a standard text replacement on Paragraphs?
> *"In Microsoft Word, paragraphs are stored as XML sequences of styled runs. Assigning text directly to `paragraph.text` wipes out the run XML nodes, which strips away all inline bolding, italicizing, highlights, fonts, or colors. To build a production-quality utility, I decoupling parsing from writing: I merge run text for contiguous extraction, detect PII character indices, and project those offsets back into the individual DOCX runs to perform run-level splicing. This preserves the surrounding formatting."*

### Q: Why do you perform redaction replacements from right-to-left?
> *"If we redact text from left-to-right, replacing a name like 'Bob' (3 characters) with a fake name like 'Jonathan Smith' (14 characters) expands the text length. This shifts the start/end offsets of all subsequent entities in that paragraph, causing subsequent redactions to target incorrect coordinates and corrupt the text. By sorting entities and redacting right-to-left, any change in string length only affects the text to the right of our current modification. Since all remaining entities lie to the left, their pre-calculated offsets remain perfectly accurate."*
