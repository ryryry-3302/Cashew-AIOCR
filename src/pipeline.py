"""Main pipeline orchestrating all processing stages."""

import logging
from pathlib import Path
from typing import List, Optional

from models import (
    CanonicalTransaction,
    CashewTransaction,
    ProcessingResult,
    PipelineResult,
    Direction,
)
from validator import validate_json_file, load_and_validate
from normalizer import DescriptionNormalizer, normalize_transaction
from merchant_rules import MerchantMatcher, match_transactions
from deduplicator import DuplicateDetector
from cashew_mapper import CashewMapper
from exporter import CashewExporter
from config import load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CashewPipeline:
    """Main pipeline for processing bank statements to Cashew CSV."""
    
    def __init__(
        self,
        config_dir: str = "config",
        output_dir: str = "output",
        existing_data_path: Optional[str] = None,
    ):
        self.config_dir = Path(config_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load configuration
        self.config = load_config(str(self.config_dir))
        
        # Initialize components
        self.normalizer = DescriptionNormalizer()
        self.merchant_matcher = MerchantMatcher(self.config.get_merchant_rules())
        self.deduplicator = DuplicateDetector()
        self.exporter = CashewExporter(str(self.output_dir / "cashew_import.csv"))
        
        # Load existing Cashew data if provided
        self.existing_transactions: List[CanonicalTransaction] = []
        self.existing_account: Optional[str] = None
        if existing_data_path:
            self.existing_transactions = self._load_existing_cashew_data(
                existing_data_path
            )
            # Extract account name from existing transactions
            if self.existing_transactions:
                self.existing_account = self.existing_transactions[0].account
                logger.info(f"Using account: {self.existing_account}")
            logger.info(f"Loaded {len(self.existing_transactions)} existing transactions")
        
        # Initialize CashewMapper with the account (may be None if no existing data)
        self.cashew_mapper = CashewMapper(self.config.get_all(), self.existing_account)
    
    def process_file(self, filepath: str) -> ProcessingResult:
        """Process a single JSON file."""
        logger.info(f"Reading {filepath}")
        
        # Validate and load transactions
        results = validate_json_file(filepath)
        
        valid_txs = []
        errors = []
        
        for result in results:
            if result.valid and result.transaction:
                # Set provenance
                result.transaction.source_file = filepath
                valid_txs.append(result.transaction)
            else:
                errors.append((result.errors,))
        
        logger.info(f"Loaded {len(valid_txs)} transactions")
        
        # Normalize descriptions
        logger.info("Normalizing merchants")
        for tx in valid_txs:
            normalize_transaction(tx, self.normalizer)
        
        # Match merchants
        logger.info("Matching merchants")
        matched_count = 0
        for tx in valid_txs:
            rule = self.merchant_matcher.match(tx)
            if rule:
                self.merchant_matcher.apply_rule(tx, rule)
                matched_count += 1
        
        logger.info(f"Matched {matched_count} merchant rules")
        
        # Count uncategorized
        uncategorized = sum(1 for tx in valid_txs if tx.category == "Uncategorized")
        logger.info(f"{uncategorized} Uncategorized")
        
        return ProcessingResult(
            source_file=filepath,
            transactions=valid_txs,
            validation_errors=errors,
            skipped_count=len(errors),
        )
    
    def process_directory(self, input_dir: str, timeout: int = 60) -> PipelineResult:
        """Process all JSON files in a directory."""
        import time
        start_time = time.time()
        
        input_path = Path(input_dir)
        
        all_transactions: List[CanonicalTransaction] = []
        all_errors: List[tuple] = []
        files_processed: List[str] = []
        
        # Find all JSON files
        json_files = sorted(input_path.glob("*.json"))
        
        logger.info(f"Found {len(json_files)} JSON files in {input_dir}")
        
        if not json_files:
            logger.warning(f"No JSON files found in {input_dir}")
            return PipelineResult(
                total_transactions=0,
                duplicates_removed=0,
                uncategorized_count=0,
                validation_errors=[],
                files_processed=[],
                output_transactions=[],
            )
        
        # Process each file
        for i, filepath in enumerate(json_files):
            # Check timeout
            if time.time() - start_time > timeout:
                logger.error(f"Timeout reached after processing {i} files")
                break
            
            logger.info(f"Processing file {i+1}/{len(json_files)}: {filepath.name}")
            result = self.process_file(str(filepath))
            all_transactions.extend(result.transactions)
            all_errors.extend(result.validation_errors)
            files_processed.append(filepath.name)
            logger.info(f"  Loaded {len(result.transactions)} transactions")
        
        logger.info(f"Total transactions: {len(all_transactions)}")
        
        # Deduplicate
        logger.info("Removing duplicates")
        unique_transactions = self.deduplicator.add_all(all_transactions)
        duplicates_removed = self.deduplicator.duplicate_count
        
        logger.info(f"Removed {duplicates_removed} duplicates")
        
        # Count uncategorized
        uncategorized_count = sum(
            1 for tx in unique_transactions if tx.category == "Uncategorized"
        )
        
        elapsed = time.time() - start_time
        logger.info(f"Processing completed in {elapsed:.2f}s")
        
        return PipelineResult(
            total_transactions=len(unique_transactions),
            duplicates_removed=duplicates_removed,
            uncategorized_count=uncategorized_count,
            validation_errors=all_errors,
            files_processed=files_processed,
            output_transactions=unique_transactions,
        )
    
    def _load_existing_cashew_data(self, filepath: str) -> List[CanonicalTransaction]:
        """Load existing Cashew transactions and convert to canonical format."""
        cashew_txs = CashewExporter.read(filepath)
        
        canonical_txs = []
        for tx in cashew_txs:
            canonical = CanonicalTransaction(
                date=tx.date,
                description_original=tx.title,
                description_normalized=tx.title,
                amount=abs(tx.amount),
                currency=tx.currency,
                direction=Direction.CREDIT if tx.income else Direction.DEBIT,
                merchant=tx.title,
                category=tx.category_name,
                subcategory=tx.subcategory_name,
                account=tx.account,
                institution=None,
                reference=None,
                notes=tx.note,
                balance=None,
                income=tx.income,
                confidence=1.0,
                source_file=filepath,
                statement_start=None,
                statement_end=None,
            )
            canonical_txs.append(canonical)
        
        return canonical_txs
    
    def _convert_existing_to_cashew(
        self, canonical_txs: List[CanonicalTransaction]
    ) -> List[CashewTransaction]:
        """Convert existing canonical transactions to Cashew format."""
        # Use the overridden account if available
        config = self.config.get_all()
        if self.existing_account:
            config["accounts"] = {"_": self.existing_account}
        return [tx.to_cashew(config) for tx in canonical_txs]
    
    def export(self, result: PipelineResult):
        """Export the pipeline result to Cashew CSV."""
        # Map to Cashew format
        cashew_transactions = self.cashew_mapper.map_all(result.output_transactions)
        
        if self.existing_transactions:
            # Merge with existing data
            existing_cashew = self._convert_existing_to_cashew(
                self.existing_transactions
            )
            added_count = self.exporter.export_merged(
                existing_cashew, cashew_transactions
            )
            logger.info(f"Merged {added_count} new transactions")
        else:
            # Export new transactions
            self.exporter.export(cashew_transactions)
            logger.info(f"Exported {len(cashew_transactions)} transactions")
        
        # Export report
        self.exporter.export_report(
            cashew_transactions,
            result.duplicates_removed,
            result.uncategorized_count,
            result.validation_errors,
            result.files_processed,
        )
        
        return cashew_transactions


def run_pipeline(
    input_dir: str = "input",
    config_dir: str = "config",
    output_dir: str = "output",
    existing_data_path: Optional[str] = None,
    timeout: int = 60,  # seconds
) -> PipelineResult:
    """Run the complete pipeline."""
    logger.info("Starting Cashew import pipeline")
    logger.info(f"Input directory: {input_dir}")
    logger.info(f"Config directory: {config_dir}")
    logger.info(f"Output directory: {output_dir}")
    
    pipeline = CashewPipeline(
        config_dir=config_dir,
        output_dir=output_dir,
        existing_data_path=existing_data_path,
    )
    
    # Process all files
    result = pipeline.process_directory(input_dir, timeout=timeout)
    
    # Export
    pipeline.export(result)
    
    logger.info("Pipeline completed")
    
    return result


if __name__ == "__main__":
    import sys
    
    input_dir = sys.argv[1] if len(sys.argv) > 1 else "input"
    config_dir = sys.argv[2] if len(sys.argv) > 2 else "config"
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "output"
    
    result = run_pipeline(input_dir, config_dir, output_dir)
    
    print(f"\nSummary:")
    print(f"  Files processed: {len(result.files_processed)}")
    print(f"  Total transactions: {result.total_transactions}")
    print(f"  Duplicates removed: {result.duplicates_removed}")
    print(f"  Uncategorized: {result.uncategorized_count}")
    print(f"  Validation errors: {len(result.validation_errors)}")
