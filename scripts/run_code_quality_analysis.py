#!/usr/bin/env python3
"""
Script to run code quality analysis on the Forkscout codebase
"""

import sys
import logging
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from forkscout.analysis.code_quality_analyzer import CodeQualityAnalyzer
from forkscout.analysis.quality_report_generator import QualityReportGenerator


def main():
    """Run code quality analysis on the Forkscout codebase"""
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize analyzer for the Forkscout source code
        source_path = Path(__file__).parent.parent / "src"
        logger.info(f"Analyzing code quality in: {source_path}")
        
        analyzer = CodeQualityAnalyzer(str(source_path))
        
        # Run analysis
        logger.info("Starting code quality analysis...")
        metrics = analyzer.analyze_codebase()
        logger.info("Analysis completed")
        
        # Generate reports
        report_generator = QualityReportGenerator(analyzer)
        
        # Create reports directory
        reports_dir = Path(__file__).parent.parent / "reports"
        reports_dir.mkdir(exist_ok=True)
        
        # Generate comprehensive markdown report
        markdown_path = reports_dir / "code_quality_analysis.md"
        logger.info(f"Generating comprehensive report: {markdown_path}")
        report_generator.generate_comprehensive_report(str(markdown_path))
        
        # Generate JSON report for programmatic access
        json_path = reports_dir / "code_quality_analysis.json"
        logger.info(f"Generating JSON report: {json_path}")
        report_generator.generate_json_report(str(json_path))
        
        # Display summary
        print("\n" + "="*80)
        print("CODE QUALITY ANALYSIS SUMMARY")
        print("="*80)
        
        total_issues = sum(metrics.issue_count_by_priority.values())
        
        print(f"Files analyzed: {metrics.total_files}")
        print(f"Total lines of code: {metrics.total_lines:,}")
        print(f"Average complexity: {metrics.average_complexity:.2f}")
        print(f"Average maintainability: {metrics.average_maintainability:.1f}/100")
        print(f"Technical debt score: {metrics.technical_debt_score:.2f}/4.0")
        print(f"Total issues found: {total_issues}")
        
        # Issue breakdown
        if metrics.issue_count_by_priority:
            print("\nIssue breakdown by priority:")
            for priority, count in metrics.issue_count_by_priority.items():
                if count > 0:
                    print(f"  {priority.value.title()}: {count}")
        
        # Technical debt items
        if analyzer.technical_debt_items:
            print(f"\nTechnical debt items identified: {len(analyzer.technical_debt_items)}")
            print("\nTop 5 technical debt items:")
            for i, debt_item in enumerate(analyzer.technical_debt_items[:5], 1):
                print(f"  {i}. {debt_item.title} ({debt_item.priority.value})")
                print(f"     Files affected: {len(debt_item.files_affected)}")
                print(f"     Related issues: {len(debt_item.related_issues)}")
        
        # Health assessment
        print("\n" + "-"*80)
        if metrics.average_maintainability >= 80 and metrics.technical_debt_score <= 1.5:
            print("Overall Health: 🟢 GOOD - Code quality is well-maintained")
        elif metrics.average_maintainability >= 60 and metrics.technical_debt_score <= 2.5:
            print("Overall Health: 🟡 FAIR - Code quality has room for improvement")
        else:
            print("Overall Health: 🔴 NEEDS ATTENTION - Significant quality issues")
        
        print(f"\nDetailed reports saved to:")
        print(f"  Markdown: {markdown_path}")
        print(f"  JSON: {json_path}")
        print("="*80)
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()