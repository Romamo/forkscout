#!/usr/bin/env python3
"""
Documentation completeness and accuracy analysis script.

This script performs a comprehensive analysis of the project's documentation,
including README completeness, API documentation coverage, user guides,
contributor documentation, and example validation.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from forklift.analysis.documentation_analyzer import DocumentationAnalyzer
from forklift.analysis.documentation_report_generator import DocumentationReportGenerator


def setup_logging(verbose: bool = False):
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def main():
    """Main function to run documentation analysis."""
    parser = argparse.ArgumentParser(
        description="Analyze project documentation completeness and accuracy"
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="Root directory of the project to analyze (default: current directory)"
    )
    parser.add_argument(
        "--output",
        help="Output file path for the report (default: print to stdout)"
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format for the report (default: markdown)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize analyzer
        logger.info(f"Starting documentation analysis for project: {args.project_root}")
        analyzer = DocumentationAnalyzer(args.project_root)
        
        # Perform analysis
        assessment = analyzer.analyze_documentation()
        
        # Generate report
        logger.info("Generating documentation assessment report")
        report_generator = DocumentationReportGenerator()
        
        if args.format == "json":
            report_content = report_generator.generate_json_report(assessment)
        else:
            report_content = report_generator.generate_markdown_report(assessment)
        
        # Output report
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            logger.info(f"Report saved to: {output_path}")
            
            # Print summary to stdout
            print(f"Documentation Assessment Complete!")
            print(f"Overall Score: {assessment.overall_score}/100")
            print(f"Report saved to: {output_path}")
            
            # Print key metrics
            if assessment.api_documentation:
                api_files = len(assessment.api_documentation)
                avg_coverage = sum(doc.overall_coverage for doc in assessment.api_documentation.values()) / api_files
                print(f"API Documentation: {avg_coverage:.1f}% average coverage across {api_files} files")
            
            print(f"README Score: {assessment.readme_assessment['completeness_score']:.1f}% completeness, {assessment.readme_assessment['accuracy_score']:.1f}% accuracy")
            
            critical_gaps = len([gap for gap in assessment.documentation_gaps if gap.severity == "critical"])
            high_gaps = len([gap for gap in assessment.documentation_gaps if gap.severity == "high"])
            print(f"Documentation Gaps: {critical_gaps} critical, {high_gaps} high priority")
            
        else:
            # Print to stdout
            print(report_content)
        
        # Exit with appropriate code based on score
        if assessment.overall_score < 50:
            logger.warning("Documentation score is below 50% - consider this a failure")
            sys.exit(1)
        elif assessment.overall_score < 75:
            logger.warning("Documentation score is below 75% - improvement needed")
            sys.exit(0)
        else:
            logger.info("Documentation score is good (75%+)")
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Documentation analysis failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()