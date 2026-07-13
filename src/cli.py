"""Command-line interface for the Cashew import pipeline."""

import argparse
import sys
from pathlib import Path

# Add project root to path for direct script execution
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.pipeline import run_pipeline
from src.config import create_default_configs


def main():
    parser = argparse.ArgumentParser(
        description="Convert bank statement JSON files to Cashew import CSV"
    )
    
    parser.add_argument(
        "-i", "--input",
        default="input",
        help="Input directory containing JSON files (default: input)"
    )
    
    parser.add_argument(
        "-c", "--config",
        default="config",
        help="Configuration directory (default: config)"
    )
    
    parser.add_argument(
        "-o", "--output",
        default="output",
        help="Output directory for CSV and report (default: output)"
    )
    
    parser.add_argument(
        "-e", "--existing",
        default=None,
        help="Path to existing Cashew CSV to merge with (optional)"
    )
    
    parser.add_argument(
        "--create-config",
        action="store_true",
        help="Create default configuration files if they don't exist"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set up logging level
    if args.verbose:
        import logging
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(levelname)s - %(message)s"
        )
    
    # Create default configs if requested
    if args.create_config:
        create_default_configs(args.config)
        print(f"Default configurations created in {args.config}/")
        return 0
    
    # Validate input directory
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input directory '{args.input}' does not exist")
        return 1
    
    # Run pipeline
    try:
        result = run_pipeline(
            args.input,
            args.config,
            args.output,
            existing_data_path=args.existing,
        )
        
        # Print summary
        print(f"\n{'='*50}")
        print("PIPELINE SUMMARY")
        print(f"{'='*50}")
        print(f"Files processed: {len(result.files_processed)}")
        for f in result.files_processed:
            print(f"  - {f}")
        print(f"\nTransactions:")
        print(f"  Total: {result.total_transactions}")
        print(f"  Duplicates removed: {result.duplicates_removed}")
        print(f"  Uncategorized: {result.uncategorized_count}")
        print(f"\nValidation errors: {len(result.validation_errors)}")
        for error in result.validation_errors:
            print(f"  {error}")
        print(f"\nOutput files:")
        print(f"  CSV: {args.output}/cashew_import.csv")
        print(f"  Report: {args.output}/report.txt")
        print(f"{'='*50}")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
