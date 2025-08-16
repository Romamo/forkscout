# Spec Management Guidelines

## Default Spec Behavior

**All planning and task management should default to the current spec unless explicitly requested otherwise.**

### Core Principles

- **Current Spec Focus**: When users request new features, enhancements, or modifications, add them to the existing spec that is currently being worked on
- **Avoid Spec Proliferation**: Do not create new specs unless the user specifically requests a completely separate feature that doesn't belong to the current project scope
- **Incremental Development**: Build upon existing specs by adding new requirements, design elements, and tasks rather than starting fresh

### When to Create New Specs

Only create new specs when:
- User explicitly asks for a "new spec" or "separate spec"
- The requested feature is completely unrelated to the current project domain
- User specifically mentions they want to work on a different project or feature set

### When to Update Current Spec

Update the existing spec when:
- Adding new functionality to the current project
- Enhancing existing features
- Fixing issues or bugs in the current system
- Improving performance or user experience of current features
- Adding new requirements that extend the current project scope

### Implementation Approach

1. **Default to Current**: Always assume new work belongs to the current spec
2. **Extend Existing**: Add new requirements, design sections, and tasks to existing spec documents
3. **Maintain Continuity**: Keep the development flow within the same spec to maintain context and coherence
4. **Ask for Clarification**: Only ask about creating a new spec if the request is genuinely ambiguous about project scope

### Example Scenarios

**Add to Current Spec:**
- "Add a new export format"
- "Improve the analysis algorithm"
- "Add better error handling"
- "Create a web interface"
- "Add database support"

**Create New Spec (only if explicitly requested):**
- "Create a new spec for a mobile app"
- "I want to start a separate project for..."
- "Let's create a new spec for the documentation system"

This approach ensures focused development and prevents unnecessary fragmentation of project planning.