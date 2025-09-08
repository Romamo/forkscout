"""
Unit tests for TeamRoleDocumenter
"""

import json
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from src.forklift.analysis.team_role_documenter import (
    TeamRoleDocumenter,
    TeamMemberRole,
    CollaborationPattern,
    ResponsibilityBreakdown,
    TeamRoleReport
)


class TestTeamRoleDocumenter:
    """Test cases for TeamRoleDocumenter class."""
    
    @pytest.fixture
    def documenter(self, tmp_path):
        """Create a TeamRoleDocumenter instance with temporary directory."""
        return TeamRoleDocumenter(project_root=tmp_path)
    
    def test_init(self, tmp_path):
        """Test TeamRoleDocumenter initialization."""
        documenter = TeamRoleDocumenter(project_root=tmp_path)
        
        assert documenter.project_root == tmp_path
    
    def test_init_default_path(self):
        """Test TeamRoleDocumenter initialization with default path."""
        with patch('pathlib.Path.cwd') as mock_cwd:
            mock_cwd.return_value = Path("/test/path")
            documenter = TeamRoleDocumenter()
            
            assert documenter.project_root == Path("/test/path")
    
    def test_document_team_roles(self, documenter):
        """Test team roles documentation."""
        report = documenter.document_team_roles()
        
        assert isinstance(report, TeamRoleReport)
        assert len(report.team_members) == 2  # Primary developer + Kiro AI
        assert len(report.collaboration_patterns) > 0
        assert len(report.responsibility_breakdowns) > 0
        assert isinstance(report.team_dynamics, dict)
        assert report.development_methodology == "Spec-driven development with AI assistance"
        assert isinstance(report.success_metrics, dict)
        assert isinstance(report.lessons_learned, list)
    
    def test_define_team_members(self, documenter):
        """Test team member definition."""
        team_members = documenter._define_team_members()
        
        assert len(team_members) == 2
        
        # Check primary developer
        primary_dev = team_members[0]
        assert primary_dev.name == "Primary Developer"
        assert primary_dev.role == "Lead Developer & AI Collaboration Specialist"
        assert len(primary_dev.primary_responsibilities) > 0
        assert len(primary_dev.contributions) > 0
        assert len(primary_dev.kiro_collaboration_examples) > 0
        assert len(primary_dev.expertise_areas) > 0
        assert isinstance(primary_dev.time_allocation, dict)
        assert sum(primary_dev.time_allocation.values()) == 100.0
        
        # Check Kiro AI
        kiro_ai = team_members[1]
        assert kiro_ai.name == "Kiro AI Assistant"
        assert kiro_ai.role == "AI Development Partner"
        assert len(kiro_ai.primary_responsibilities) > 0
        assert len(kiro_ai.contributions) > 0
        assert len(kiro_ai.kiro_collaboration_examples) > 0
        assert len(kiro_ai.expertise_areas) > 0
        assert isinstance(kiro_ai.time_allocation, dict)
        assert sum(kiro_ai.time_allocation.values()) == 100.0
    
    def test_identify_collaboration_patterns(self, documenter):
        """Test collaboration pattern identification."""
        patterns = documenter._identify_collaboration_patterns()
        
        assert len(patterns) >= 4  # Should have at least 4 patterns
        
        pattern_names = [p.pattern_name for p in patterns]
        expected_patterns = [
            "Spec-Driven Development",
            "Iterative Refinement", 
            "Knowledge Transfer",
            "AI-Assisted Quality Assurance"
        ]
        
        for expected in expected_patterns:
            assert expected in pattern_names
        
        # Check pattern structure
        for pattern in patterns:
            assert isinstance(pattern, CollaborationPattern)
            assert pattern.pattern_name is not None
            assert pattern.description is not None
            assert pattern.human_role is not None
            assert pattern.ai_role is not None
            assert len(pattern.workflow_steps) > 0
            assert len(pattern.examples) > 0
            assert 1 <= pattern.effectiveness_rating <= 10
            assert len(pattern.use_cases) > 0
    
    def test_create_responsibility_breakdowns(self, documenter):
        """Test responsibility breakdown creation."""
        breakdowns = documenter._create_responsibility_breakdowns()
        
        assert len(breakdowns) >= 4  # Should have at least 4 categories
        
        categories = [b.category for b in breakdowns]
        expected_categories = [
            "Architecture and Design",
            "Feature Development",
            "Testing and Quality Assurance",
            "Documentation and Communication"
        ]
        
        for expected in expected_categories:
            assert expected in categories
        
        # Check breakdown structure
        for breakdown in breakdowns:
            assert isinstance(breakdown, ResponsibilityBreakdown)
            assert breakdown.category is not None
            assert len(breakdown.human_responsibilities) > 0
            assert len(breakdown.ai_responsibilities) > 0
            assert len(breakdown.shared_responsibilities) > 0
            assert breakdown.decision_making_process is not None
            assert breakdown.quality_assurance is not None
    
    def test_analyze_team_dynamics(self, documenter):
        """Test team dynamics analysis."""
        dynamics = documenter._analyze_team_dynamics()
        
        assert isinstance(dynamics, dict)
        
        # Check required sections
        required_sections = [
            "collaboration_effectiveness",
            "development_velocity",
            "strengths",
            "challenges",
            "success_factors"
        ]
        
        for section in required_sections:
            assert section in dynamics
        
        # Check collaboration effectiveness ratings
        collab_eff = dynamics["collaboration_effectiveness"]
        for rating in collab_eff.values():
            assert 1 <= rating <= 10
        
        # Check lists are populated
        assert len(dynamics["strengths"]) > 0
        assert len(dynamics["challenges"]) > 0
        assert len(dynamics["success_factors"]) > 0
    
    def test_calculate_success_metrics(self, documenter):
        """Test success metrics calculation."""
        metrics = documenter._calculate_success_metrics()
        
        assert isinstance(metrics, dict)
        
        # Check required metric categories
        required_categories = [
            "development_metrics",
            "collaboration_metrics",
            "productivity_metrics",
            "quality_metrics"
        ]
        
        for category in required_categories:
            assert category in metrics
        
        # Check development metrics
        dev_metrics = metrics["development_metrics"]
        assert dev_metrics["specs_created"] > 0
        assert dev_metrics["steering_rules_established"] > 0
        assert 0 <= dev_metrics["code_coverage_percentage"] <= 100
        assert 0 <= dev_metrics["test_pass_rate"] <= 100
        
        # Check collaboration metrics
        collab_metrics = metrics["collaboration_metrics"]
        assert 0 <= collab_metrics["ai_contribution_percentage"] <= 100
        assert 0 <= collab_metrics["human_oversight_effectiveness"] <= 100
        
        # Check productivity metrics
        prod_metrics = metrics["productivity_metrics"]
        assert prod_metrics["development_velocity_multiplier"] > 1.0
        assert 0 <= prod_metrics["code_generation_efficiency"] <= 100
    
    def test_extract_lessons_learned(self, documenter):
        """Test lessons learned extraction."""
        lessons = documenter._extract_lessons_learned()
        
        assert isinstance(lessons, list)
        assert len(lessons) > 10  # Should have substantial lessons
        
        # Check that lessons are meaningful strings
        for lesson in lessons:
            assert isinstance(lesson, str)
            assert len(lesson) > 20  # Should be substantial content
            assert lesson[0].isupper()  # Should start with capital letter
    
    def test_generate_team_role_documentation(self, documenter):
        """Test comprehensive team role documentation generation."""
        documentation = documenter.generate_team_role_documentation()
        
        assert isinstance(documentation, dict)
        
        # Check required sections
        required_sections = [
            "documentation_timestamp",
            "project_context",
            "team_composition",
            "collaboration_patterns",
            "responsibility_matrix",
            "team_dynamics_analysis",
            "success_metrics",
            "lessons_learned",
            "recommendations"
        ]
        
        for section in required_sections:
            assert section in documentation
        
        # Verify timestamp format
        timestamp = documentation["documentation_timestamp"]
        datetime.fromisoformat(timestamp)  # Should not raise exception
        
        # Check project context
        context = documentation["project_context"]
        assert "project_name" in context
        assert "development_methodology" in context
        assert context["team_size"] == 2
        
        # Check team composition
        team_comp = documentation["team_composition"]
        assert len(team_comp) == 2
        
        # Check recommendations
        recommendations = documentation["recommendations"]
        assert "for_future_ai_collaboration" in recommendations
        assert "for_scaling_ai_development" in recommendations
        assert len(recommendations["for_future_ai_collaboration"]) > 0
        assert len(recommendations["for_scaling_ai_development"]) > 0
    
    def test_serialize_for_json(self, documenter):
        """Test JSON serialization helper."""
        # Test datetime serialization
        dt = datetime.now()
        serialized_dt = documenter._serialize_for_json(dt)
        assert isinstance(serialized_dt, str)
        assert dt.isoformat() == serialized_dt
        
        # Test dict serialization
        test_dict = {"key": dt, "nested": {"inner_dt": dt}}
        serialized_dict = documenter._serialize_for_json(test_dict)
        assert serialized_dict["key"] == dt.isoformat()
        assert serialized_dict["nested"]["inner_dt"] == dt.isoformat()
        
        # Test list serialization
        test_list = [dt, {"dt": dt}]
        serialized_list = documenter._serialize_for_json(test_list)
        assert serialized_list[0] == dt.isoformat()
        assert serialized_list[1]["dt"] == dt.isoformat()
        
        # Test primitive types
        assert documenter._serialize_for_json("string") == "string"
        assert documenter._serialize_for_json(42) == 42
        assert documenter._serialize_for_json(True) is True
    
    def test_save_documentation_to_file(self, documenter, tmp_path):
        """Test saving documentation to file."""
        output_path = tmp_path / "test_team_docs.json"
        
        saved_path = documenter.save_documentation_to_file(output_path)
        
        assert saved_path == output_path
        assert output_path.exists()
        assert output_path.stat().st_size > 0
        
        # Verify JSON structure
        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert isinstance(data, dict)
        assert "documentation_timestamp" in data
        assert "team_composition" in data
    
    def test_save_documentation_default_path(self, documenter):
        """Test saving documentation with default path."""
        with patch.object(documenter, 'generate_team_role_documentation') as mock_gen:
            mock_gen.return_value = {"test": "data"}
            
            output_path = documenter.save_documentation_to_file()
            
            assert output_path.name == "team_role_documentation.json"
            assert output_path.exists()


class TestDataClasses:
    """Test the data classes used by TeamRoleDocumenter."""
    
    def test_team_member_role_creation(self):
        """Test TeamMemberRole dataclass creation."""
        role = TeamMemberRole(
            name="Test Developer",
            role="Developer",
            primary_responsibilities=["Coding", "Testing"],
            secondary_responsibilities=["Documentation"],
            contributions=["Feature A", "Feature B"],
            kiro_collaboration_examples=["Example 1"],
            development_approach="TDD",
            expertise_areas=["Python", "API"],
            time_allocation={"coding": 70.0, "testing": 30.0}
        )
        
        assert role.name == "Test Developer"
        assert role.role == "Developer"
        assert len(role.primary_responsibilities) == 2
        assert sum(role.time_allocation.values()) == 100.0
    
    def test_collaboration_pattern_creation(self):
        """Test CollaborationPattern dataclass creation."""
        pattern = CollaborationPattern(
            pattern_name="Test Pattern",
            description="Test description",
            human_role="Human role",
            ai_role="AI role",
            workflow_steps=["Step 1", "Step 2"],
            examples=["Example 1"],
            effectiveness_rating=8,
            use_cases=["Use case 1"]
        )
        
        assert pattern.pattern_name == "Test Pattern"
        assert pattern.effectiveness_rating == 8
        assert len(pattern.workflow_steps) == 2
    
    def test_responsibility_breakdown_creation(self):
        """Test ResponsibilityBreakdown dataclass creation."""
        breakdown = ResponsibilityBreakdown(
            category="Test Category",
            human_responsibilities=["Human task 1"],
            ai_responsibilities=["AI task 1"],
            shared_responsibilities=["Shared task 1"],
            decision_making_process="Test process",
            quality_assurance="Test QA"
        )
        
        assert breakdown.category == "Test Category"
        assert len(breakdown.human_responsibilities) == 1
        assert len(breakdown.ai_responsibilities) == 1
        assert len(breakdown.shared_responsibilities) == 1
    
    def test_team_role_report_creation(self):
        """Test TeamRoleReport dataclass creation."""
        report = TeamRoleReport(
            team_members=[],
            collaboration_patterns=[],
            responsibility_breakdowns=[],
            team_dynamics={},
            development_methodology="Test methodology",
            success_metrics={},
            lessons_learned=[]
        )
        
        assert report.development_methodology == "Test methodology"
        assert isinstance(report.team_members, list)
        assert isinstance(report.collaboration_patterns, list)
        assert isinstance(report.responsibility_breakdowns, list)