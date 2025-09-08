#!/usr/bin/env python3
"""
Generate Comprehensive Project Health Report

This script generates a unified project health report that compiles all assessment
results from functionality, code quality, test coverage, documentation, and cleanup analyses.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from forklift.analysis.project_health_report_generator import ProjectHealthReportGenerator


def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def load_analysis_data(file_path: str) -> dict:
    """Load analysis data from JSON file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.warning(f"Analysis file not found: {file_path}")
        return {}
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse JSON from {file_path}: {e}")
        return {}
    except Exception as e:
        logging.error(f"Error loading {file_path}: {e}")
        return {}


def load_markdown_analysis(file_path: str) -> dict:
    """Load analysis data from markdown file and extract key metrics."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Extract key metrics from markdown
        data = {
            'overall_score': 0.0,
            'api_coverage': 0.0,
            'readme_score': 0.0,
            'user_guides_score': 0.0,
            'contributor_docs_score': 0.0,
            'gaps': []
        }
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if 'Overall Score:' in line:
                try:
                    # Extract score from patterns like "**Overall Score:** 73.7/100"
                    parts = line.split('Overall Score:')
                    if len(parts) > 1:
                        score_part = parts[1].strip().replace('*', '').strip()
                        score = float(score_part.split('/')[0])
                        data['overall_score'] = score
                except:
                    pass
            elif 'API Documentation Coverage:' in line:
                try:
                    # Extract coverage from patterns like "- **API Documentation Coverage:** 95.6% across 79 files"
                    parts = line.split('API Documentation Coverage:')
                    if len(parts) > 1:
                        coverage_part = parts[1].strip().replace('*', '').strip()
                        coverage = float(coverage_part.split('%')[0])
                        data['api_coverage'] = coverage
                except:
                    pass
        
        return data
        
    except FileNotFoundError:
        logging.warning(f"Analysis file not found: {file_path}")
        return {}
    except Exception as e:
        logging.error(f"Error loading {file_path}: {e}")
        return {}


async def main():
    """Main function to generate comprehensive project health report."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting comprehensive project health report generation")
    
    # Define analysis file paths
    analysis_files = {
        'cleanup': 'project_cleanup_analysis.json',
        'code_quality': 'reports/code_quality_analysis.json',
        'test_coverage': 'coverage.json',
        'documentation': 'reports/documentation_assessment.md',
        'optimization': 'reports/optimization_recommendations.json'
    }
    
    # Load all analysis data
    analysis_data = {}
    
    for analysis_type, file_path in analysis_files.items():
        if analysis_type == 'documentation' and file_path.endswith('.md'):
            analysis_data[analysis_type] = load_markdown_analysis(file_path)
        else:
            analysis_data[analysis_type] = load_analysis_data(file_path)
        
        if analysis_data[analysis_type]:
            logger.info(f"Loaded {analysis_type} analysis data from {file_path}")
        else:
            logger.warning(f"No data loaded for {analysis_type} from {file_path}")
    
    # Create report generator
    generator = ProjectHealthReportGenerator(project_name="Forklift")
    
    # Generate comprehensive report
    try:
        report = generator.generate_comprehensive_report(
            functionality_data=analysis_data.get('cleanup'),  # Cleanup data contains functionality analysis
            code_quality_data=analysis_data.get('code_quality'),
            test_coverage_data=analysis_data.get('test_coverage'),
            documentation_data=analysis_data.get('documentation'),
            cleanup_data=analysis_data.get('cleanup'),
            optimization_data=analysis_data.get('optimization')
        )
        
        logger.info("Successfully generated comprehensive project health report")
        
        # Save markdown report
        markdown_output = "reports/project_health_report.md"
        Path("reports").mkdir(exist_ok=True)
        
        markdown_content = generator.generate_markdown_report(report)
        with open(markdown_output, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        logger.info(f"Markdown report saved to {markdown_output}")
        
        # Save JSON report
        json_output = "reports/project_health_report.json"
        json_content = generator.generate_json_report(report)
        with open(json_output, 'w', encoding='utf-8') as f:
            f.write(json_content)
        
        logger.info(f"JSON report saved to {json_output}")
        
        # Print summary to console
        print("\n" + "="*80)
        print("PROJECT HEALTH REPORT SUMMARY")
        print("="*80)
        print(f"Overall Health: {report.metrics.health_status}")
        print(f"Health Score: {report.metrics.overall_health_score:.1f}/100")
        print()
        print("Component Scores:")
        print(f"  Functionality: {report.metrics.functionality_score:.1f}%")
        print(f"  Code Quality: {report.metrics.code_quality_score:.1f}%")
        print(f"  Test Coverage: {report.metrics.test_coverage_score:.1f}%")
        print(f"  Documentation: {report.metrics.documentation_score:.1f}%")
        print(f"  Project Cleanup: {report.metrics.cleanup_score:.1f}%")
        print()
        print(f"Critical Issues: {len(report.critical_issues)}")
        print(f"Quick Wins Available: {len(report.quick_wins)}")
        print(f"Priority Actions: {len(report.prioritized_actions)}")
        print()
        print(f"Reports generated:")
        print(f"  - Markdown: {markdown_output}")
        print(f"  - JSON: {json_output}")
        print("="*80)
        
        # Show executive summary
        print("\nEXECUTIVE SUMMARY:")
        print("-" * 50)
        print(report.executive_summary)
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to generate project health report: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)