import argparse

from llm_eval_lab.datasets.repository import load_dataset_from_file
from llm_eval_lab.db import SessionLocal


def main() -> None:
    parser = argparse.ArgumentParser(description="Import a dataset from a JSON file")
    parser.add_argument("path", help="Path to a JSON file (flat list of test cases)")
    parser.add_argument("--name", required=True, help="Name for the new dataset")
    parser.add_argument("--description", default=None, help="Optional dataset description")
    args = parser.parse_args()

    with SessionLocal() as session:
        dataset = load_dataset_from_file(
            session,
            path=args.path,
            dataset_name=args.name,
            dataset_description=args.description,
        )
        session.commit()
        test_case_count = len(dataset.test_cases)
        print(f"Imported dataset '{dataset.name}' (id={dataset.id}) with {test_case_count} test case(s)")


if __name__ == "__main__":
    main()
