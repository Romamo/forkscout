#!/usr/bin/env python3
"""
Generate Optimization Recommendations

This script generates comprehensive optimization recommendations based on
project analysis data including cleanup analysis, code quality, test coverage,
and documentation assessment.
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from forkscout.analysis.optimization_recommender import OptimizationRecommender
from forkscout.analysis.optimization_report_generator import OptimizationReportGenerator


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Generate optimization recommendations for the project"
    )
    parser.add_argument(
        "--cleanup-analysis",
        default="project_cleanup_analysis.json",
        help="Path to project cleanup analysis JSON file"
    )
    parser.add_argument(
        "--code-quality-analysis", 
        default="reports/code_quality_analysis.json",
        help="Path to code quality analysis JSON file"
    )
    parser.add_argument(
        "--test-coverage",
        default="coverage.json",
        help="Path to test coverage JSON file"
    )
    parser.add_argument(
        "--documentation-analysis",
        default="reports/final_documentation_assessment.md",
        help="Path to documentation analysis file"
    )
    parser.add_argument(
        "--output-dir",
        default="reports",
        help="Output directory for generated reports"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting optimization recommendations generation")
    
    # Verify input files exist
    input_files = [
        args.cleanup_analysis,
        args.code_quality_analysis,
        args.test_coverage,
        args.documentation_analysis
    ]
    
    missing_files = []
    for file_path in input_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        logger.error("Missing required input files:")
        for file_path in missing_files:
            logger.error(f"  - {file_path}")
        logger.error("Please run the required analysis scripts first:")
        logger.error("  - python scripts/analyze_project_cleanup.py")
        logger.error("  - python scripts/run_code_quality_analysis.py")
        logger.error("  - uv run pytest --cov=src --cov-report=json")
        logger.error("  - python scripts/analyze_documentation.py")
        return 1
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    try:
        # Generate recommendations
        logger.info("Generating optimization recommendations...")
        recommender = OptimizationRecommender()
        
        report = recommender.generate_recommendations(
            cleanup_analysis_path=args.cleanup_analysis,
            code_quality_analysis_path=args.code_quality_analysis,
            test_coverage_path=args.test_coverage,
            documentation_analysis_path=args.documentation_analysis
        )
        
        logger.info(f"Generated {report.total_recommendations} recommendations")
        logger.info(f"Project health score: {report.project_health_score:.1f}/100")
        
        # Generate reports
        logger.info("Generating reports...")
        report_generator = OptimizationReportGenerator()
        
        # Markdown report
        markdown_path = output_dir / "optimization_recommendations.md"
        report_generator.generate_markdown_report(report, str(markdown_path))
        
        # JSON report
        json_path = output_dir / "optimization_recommendations.json"
        report_generator.generate_json_report(report, str(json_path))
        
        # Implementation roadmap
        roadmap_path = output_dir / "implementation_roadmap.md"
        report_generator.generate_implementation_roadmap(report, str(roadmap_path))
        
        logger.info("Reports generated successfully:")
        logger.info(f"  - Markdown report: {markdown_path}")
        logger.info(f"  - JSON report: {json_path}")
        logger.info(f"  - Implementation roadmap: {roadmap_path}")
        
        # Print summary
        print("\n" + "="*60)
        print("OPTIMIZATION RECOMMENDATIONS SUMMARY")
        print("="*60)
        print(f"Project Health Score: {report.project_health_score:.1f}/100")
        print(f"Total Recommendations: {report.total_recommendations}")
        print(f"Critical Issues: {len(report.critical_issues)}")
        print(f"Quick Wins Available: {len(report.quick_wins)}")
        print(f"Estimated Total Effort: {report.resource_estimates.get('total', 0)} hours")
        print("\nTop Priorities:")
        
        # Show top 3 recommendations
        all_recs = report.critical_issues + report.high_priority_recommendations
        for i, rec in enumerate(all_recs[:3], 1):
            print(f"  {i}. {rec.title} ({rec.priority.value.title()} Priority)")
        
        if report.quick_wins:
            print("\nQuick Wins:")
            for i, win in enumerate(report.quick_wins[:3], 1):
                print(f"  {i}. {win.title} ({win.effort_hours}h)")
        
        print(f"\nDetailed reports available in: {output_dir}")
        print("="*60)
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to generate optimization recommendations: {e}")
        if args.verbose:
            logger.exception("Full traceback:")
        return 1


if __name__ == "__main__":
    sys.exit(main())