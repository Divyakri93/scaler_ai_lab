# PII Redactor - Performance Evaluation Report

## 1. Executive Summary

This report evaluates the automatic detection performance of the PII Redaction Tool against a manually annotated ground-truth benchmark dataset.

*   **Overall Precision**: `0.6667`
*   **Overall Recall**: `0.9231`
*   **Overall F1-Score**: `0.7742`
*   **Overall Accuracy**: `0.6316`
*   **True Positives (TP)**: `12`
*   **False Positives (FP)**: `6`
*   **False Negatives (FN)**: `1`

## 2. Per-PII-Type Metrics

| PII Type | Precision | Recall | F1-Score | Accuracy | TP | FP | FN |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **ADDRESS** | 1.0000 | 0.5000 | 0.6667 | 0.5000 | 1 | 0 | 1 |
| **COMPANY_NAME** | 0.2500 | 1.0000 | 0.4000 | 0.2500 | 1 | 3 | 0 |
| **CREDIT_CARD** | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1 | 0 | 0 |
| **DATE_OF_BIRTH** | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1 | 0 | 0 |
| **EMAIL** | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 3 | 0 | 0 |
| **FULL_NAME** | 0.4000 | 1.0000 | 0.5714 | 0.4000 | 2 | 3 | 0 |
| **IP_ADDRESS** | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1 | 0 | 0 |
| **PHONE** | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1 | 0 | 0 |
| **SSN** | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1 | 0 | 0 |

## 3. False Positives (Detections not in Ground Truth)

| Block ID | PII Type | Detected Text | Character Span |
| :--- | :--- | :--- | :---: |
| `body_table_0_r0_c0_p0` | `FULL_NAME` | `Noida` | `51-56` |
| `body_p_0` | `FULL_NAME` | `Applicant Profile` | `0-17` |
| `body_p_0` | `COMPANY_NAME` | `Date of Birth` | `67-80` |
| `body_p_2` | `COMPANY_NAME` | `SSN` | `0-3` |
| `section_0_footer_p_0` | `FULL_NAME` | `Footer info - Page 1` | `0-20` |
| `body_p_1` | `COMPANY_NAME` | `IP` | `33-35` |

## 4. False Negatives (Ground Truth PII Missed)

| Block ID | PII Type | Missed Text | Character Span |
| :--- | :--- | :--- | :---: |
| `body_table_0_r0_c0_p0` | `ADDRESS` | `Flat 201, Tower B, Sector 62, Noida` | `21-56` |
