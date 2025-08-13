---
inclusion: always
---

# Task Decomposition and Management Guidelines

## Core Principles

Break down complex features into small, focused, independently testable units that can be implemented incrementally and completed within manageable timeframes.

## Task Sizing Principles

Break down work into manageable, atomic units that can be completed and verified independently:

- **Single Session Tasks**: Each task should be completable in one focused work session (1-2 hours maximum)
- **Testable Units**: Every task must produce code that can be tested in isolation
- **Clear Acceptance Criteria**: Define specific, measurable outcomes for each task
- **Minimal Dependencies**: Reduce coupling between tasks to enable parallel development

## Decomposition Strategy

### Feature Breakdown
- Split large features into logical components (data layer, business logic, API endpoints, UI)
- Each component should have a single, well-defined responsibility
- Components should be loosely coupled and highly cohesive
- Identify dependencies between components and implement in dependency order

### Implementation Units
- Create tasks that can be completed in 1-2 hours maximum
- Each unit should be independently testable
- Units should produce working, demonstrable functionality
- Avoid tasks that require changes across multiple unrelated files

### Task Planning Approach
1. **Identify Core Domain Objects**: Start with data models and core business entities
2. **Define Interfaces**: Establish contracts between components before implementation
3. **Implement Bottom-Up**: Build foundational components before dependent ones
4. **Add Integration Points**: Connect components with well-defined interfaces
5. **Enhance Incrementally**: Add features and optimizations in small steps

### Task Prioritization
- **Foundation First**: Build core models and utilities before dependent features
- **Critical Path**: Prioritize tasks that unblock other development
- **Risk Mitigation**: Tackle uncertain or complex tasks early
- **Value Delivery**: Ensure each increment provides demonstrable progress

## Implementation Strategy

### Vertical Slicing
- Implement complete, end-to-end functionality for narrow use cases
- Each slice should be deployable and provide user value
- Build breadth through additional slices rather than incomplete depth

### Incremental Development
- Start with core functionality and build outward
- Implement minimal viable versions first, then enhance
- Each increment should maintain system stability
- Use feature flags or configuration to enable/disable incomplete features

## Quality Gates and Checkpoints

Each task completion must include:
- **Working Code**: All new code executes without errors
- **Test Coverage**: Comprehensive tests for new functionality
- **Documentation**: Updated inline and external documentation
- **Integration Verification**: Confirm compatibility with existing code
- **Rollback Plan**: Ability to revert changes if issues arise
- **Code Review**: All code should be reviewable in isolation
- **Continuous Integration**: All existing tests must continue to pass

## Communication Standards

- **Clear Task Descriptions**: Include context, requirements, and expected outcomes
- **Progress Updates**: Regular status communication on task completion
- **Blocker Identification**: Immediate escalation of impediments
- **Knowledge Sharing**: Document decisions and learnings for team benefit