#!/usr/bin/env python3
"""
Test Coverage Analysis Script

Analyzes test coverage and quality for the Forklift project and generates a comprehensive report.
"""

import sys
import logging
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from forklift.analysis.test_coverage_analyzer import TestCoverageAnalyzer
from forklift.analysis.test_coverage_report_generator import TestCoverageReportGenerator

def main():
    """Run test coverage analysis and generate report."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    project_root = Path(__file__).parent.parent
    
    print("🔍 Starting Test Coverage and Quality Analysis...")
    print(f"📁 Project Root: {project_root}")
    
    # Initialize analyzer
    analyzer = TestCoverageAnalyzer(project_root)
    
    # Perform analysis
    print("\n📊 Analyzing test coverage and quality...")
    analysis = analyzer.analyze_test_coverage_and_quality()
    
    # Generate report
    print("📝 Generating comprehensive report...")
    report_generator = TestCoverageReportGenerator()
    markdown_report = report_generator.generate_markdown_report(analysis)
    
    # Save report
    report_file = project_root / "TEST_COVERAGE_ANALYSIS.md"
    with open(report_file, 'w') as f:
        f.write(markdown_report)
    
    print(f"✅ Report saved to: {report_file}")
    
    # Print summary
    print("\n" + "="*60)
    print("📋 ANALYSIS SUMMARY")
    print("="*60)
    print(f"Overall Coverage: {analysis.overall_coverage.coverage_percentage:.1f}%")
    print(f"Branch Coverage: {analysis.overall_coverage.branch_coverage:.1f}%")
    print(f"Test Failures: {len(analysis.test_failures)}")
    print(f"Test Errors: {len(analysis.test_errors)}")
    print(f"Quality Issues: {len(analysis.quality_issues)}")
    print(f"Organization Score: {analysis.test_organization_score:.1f}/100")
    print(f"Reliability Score: {analysis.test_reliability_score:.1f}/100")
    print("="*60)
    
    # Print key recommendations
    if analysis.recommendations:
        print("\n🎯 KEY RECOMMENDATIONS:")
        for i, rec in enumerate(analysis.recommendations[:5], 1):
            print(f"{i}. {rec}")
    
    print(f"\n📖 Full report available at: {report_file}")

if __name__ == "__main__":
    main()