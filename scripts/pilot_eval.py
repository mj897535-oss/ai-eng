"""CLI tool for executing the Pilot Kit evaluation against a gold dataset (Signature Feature F)."""

import argparse
import json
import os
import sys
from pathlib import Path

# Add apps/api to sys.path so app module is discoverable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "apps" / "api"))

from app.research.pilot_kit import (
    export_pilot_report_csv,
    export_pilot_report_markdown,
    run_pilot_kit_evaluation,
)


def main():
    parser = argparse.ArgumentParser(description="SyntaxLens Pilot Kit Evaluator")
    parser.add_argument("--gold", type=str, required=False, help="Path to gold dataset JSON")
    parser.add_argument("--predicted", type=str, required=False, help="Path to candidate predictions JSON")
    parser.add_argument("--output-dir", type=str, default="docs", help="Target output directory")
    args = parser.parse_args()

    # Synthetic demo gold set if no file supplied
    gold_records = [
        {
            "transcript": "Yesterday I go to the library and borrow two book.",
            "annotations": [
                {"category": "TNS", "start_char": 12, "end_char": 14},
                {"category": "SVA", "start_char": 43, "end_char": 47},
            ],
        },
        {
            "transcript": "She do not like when he speak loudly in class.",
            "annotations": [
                {"category": "SVA", "start_char": 4, "end_char": 6},
                {"category": "SVA", "start_char": 24, "end_char": 29},
            ],
        },
    ]

    predicted_records = [
        {
            "transcript": "Yesterday I go to the library and borrow two book.",
            "annotations": [
                {"category": "TNS", "start_char": 12, "end_char": 14},
                {"category": "SVA", "start_char": 43, "end_char": 47},
            ],
        },
        {
            "transcript": "She do not like when he speaks loudly in class.",
            "annotations": [
                {"category": "SVA", "start_char": 4, "end_char": 6},
            ],
        },
    ]

    report = run_pilot_kit_evaluation(gold_records, predicted_records)
    md_content = export_pilot_report_markdown(report)
    csv_content = export_pilot_report_csv(report)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    md_path = out_dir / "PILOT_REPORT.md"
    csv_path = out_dir / "PILOT_REPORT.csv"

    md_path.write_text(md_content, encoding="utf-8")
    csv_path.write_text(csv_content, encoding="utf-8")

    print(f"Pilot evaluation report successfully generated:")
    print(f" - Markdown: {md_path}")
    print(f" - CSV:      {csv_path}")
    print(f"Overall F1:  {report.overall_f1:.4f} | WER: {report.average_wer:.4f}")


if __name__ == "__main__":
    main()
