# Prompt Engineer - Design Document

## Core Concepts

### 1. Workspace-Centric Architecture

Prompt Engineer is a **workbench tool** that points to prompts in your application's source code. It does NOT store prompts - your app's git repository is the source of truth.

```
Your App Repo/
├── src/main/resources/prompts/     # Production prompts
│   ├── system-evaluator.st
│   ├── user-evaluator.st
│   ├── system-optimizer.st
│   └── user-optimizer.st
├── src/test/resources/prompts/vars/ # Dev/test variable configs
│   ├── evaluator.yaml
│   ├── optimizer.yaml
│   └── evaluator-optimizer-chain.yaml
└── .prompt-engineer/
    └── workspace.yaml               # Workspace configuration
```

---

## Workspace Configuration

### Basic Structure

```yaml
# .prompt-engineer/workspace.yaml
name: "MyApp Prompts Workspace"
version: "1.0"

# Project layout
layout:
  prompt_dir: "src/main/resources/prompts"
  vars_dir: "src/test/resources/prompts/vars"
  chains_dir: "src/test/resources/prompts/chains"  # Optional

  # File extensions
  prompt_extension: ".st"      # StringTemplate files
  vars_extension: ".yaml"       # Variable config files

# Template syntax configuration
template:
  # Variable delimiter configuration
  variable_delimiters:
    start: "{"          # Start delimiter (default: "{")
    end: "}"            # End delimiter (default: "}")

  # Examples of other delimiter configs:
  # start: "$", end: "$"     # For $var$
  # start: "<", end: ">"     # For <var>
  # start: "[[", end: "]]"   # For [[var]]

  # File naming conventions
  naming:
    # Pattern for prompt files: {role}-{name}.st
    # role: system, user, assistant, etc.
    # name: evaluator, optimizer, etc.
    pattern: "{role}-{name}.st"

    # Recognized roles
    roles: ["system", "user"]

    # Var file pattern: {name}.yaml
    var_pattern: "{name}.yaml"

  # Auto-matching behavior
  matching:
    auto_match: true               # Auto-match prompts to vars by name
    allow_override: true           # Allow manual override in var files
    warn_orphans: true            # Warn about prompts without vars

# Git integration (minimal)
git:
  show_status: true          # Show git status in UI
  show_branch: true          # Show current branch
  show_uncommitted: true     # Show uncommitted changes count

# Default model settings for this workspace
defaults:
  provider: "openai"
  model: "gpt-4o"
  temperature: 0.7
  max_tokens: 2000

# Workspace settings
settings:
  auto_reload: true          # Watch for external file changes
  auto_extract_vars: true    # Auto-detect variables in prompts
  auto_save: false           # Auto-save on change (default: false)
```

---

## Variable Configuration Files

### Single Prompt (Simple Case)

```yaml
# evaluator.yaml
name: "Code Evaluator"
description: "Evaluates code quality and suggests improvements"

# Prompt files (auto-matched by name, or explicitly specified)
prompts:
  system: "system-evaluator.st"    # Explicit path (relative to prompt_dir)
  user: "user-evaluator.st"         # Explicit path

  # Alternative: rely on auto-matching
  # If omitted, will look for system-evaluator.st and user-evaluator.st

# Variables with test/dev values
variables:
  code_to_evaluate:
    type: file
    path: "../../examples/SampleService.java"
    description: "Sample Java code for testing"

  evaluation_criteria:
    type: value
    value: |
      - Code correctness and logic
      - Performance and efficiency
      - Security best practices
      - Code maintainability and readability
      - Error handling
    description: "Criteria for code evaluation"

  coding_standards:
    type: file
    path: "../../docs/java-coding-standards.md"
    description: "Company coding standards"

  max_issues:
    type: value
    value: "10"
    description: "Maximum number of issues to report"

# Model settings (override workspace defaults)
model:
  provider: "openai"
  name: "gpt-4o"
  temperature: 0.3      # Lower temp for consistent evaluation
  max_tokens: 3000

# Metadata
tags: ["evaluator", "code-review", "java"]
created: "2024-11-29"
last_modified: "2024-11-29"
```

### Auto-Matching Behavior

**Workspace has:**
- `system-evaluator.st`
- `user-evaluator.st`
- `evaluator.yaml`

**Auto-matching logic:**
1. Parse filename: `evaluator.yaml` → name = "evaluator"
2. Look for prompts matching pattern: `{role}-evaluator.st`
3. Find: `system-evaluator.st` and `user-evaluator.st`
4. Map: system → system-evaluator.st, user → user-evaluator.st

**Manual override:**
```yaml
# evaluator.yaml
prompts:
  system: "custom-system-prompt.st"  # Override auto-match
  user: "user-evaluator.st"           # Use auto-matched
```

---

## Prompt Chaining

### Chain Configuration

```yaml
# evaluator-optimizer-chain.yaml
name: "Evaluator-Optimizer Chain"
description: "Evaluate code, optimize it, then re-evaluate"

# Shared context variables (available to all steps)
context:
  code_to_evaluate:
    type: file
    path: "../../examples/SampleService.java"

  coding_standards:
    type: file
    path: "../../docs/java-coding-standards.md"

# Chain steps (executed sequentially)
steps:
  - name: "evaluate"
    description: "Initial code evaluation"

    prompts:
      system: "system-evaluator.st"
      user: "user-evaluator.st"

    # Variables for this step (in addition to context)
    variables:
      evaluation_criteria:
        type: value
        value: "correctness, performance, security, maintainability"

      max_issues:
        type: value
        value: "10"

    # Model settings for this step
    model:
      provider: "openai"
      name: "gpt-4o"
      temperature: 0.3
      max_tokens: 3000

    # Output variable name (stores LLM response)
    output_var: "evaluation"

  - name: "optimize"
    description: "Optimize code based on evaluation"

    prompts:
      system: "system-optimizer.st"
      user: "user-optimizer.st"

    # Variables for this step
    variables:
      # Reference output from previous step
      evaluation: "{steps.evaluate.output}"

      optimization_focus:
        type: value
        value: "Address all critical and high-priority issues from evaluation"

    model:
      provider: "openai"
      name: "gpt-4o"
      temperature: 0.5
      max_tokens: 4000

    output_var: "optimized_code"

  - name: "validate"
    description: "Re-evaluate optimized code"

    prompts:
      system: "system-evaluator.st"
      user: "user-evaluator.st"

    variables:
      # Override context variable with optimized code
      code_to_evaluate: "{steps.optimize.output}"

      # Include previous evaluation for comparison
      previous_evaluation: "{steps.evaluate.output}"

      evaluation_criteria:
        type: value
        value: "Compare with previous evaluation, verify improvements"

    model:
      provider: "openai"
      name: "gpt-4o"
      temperature: 0.3
      max_tokens: 3000

    output_var: "final_evaluation"

    # Optional: conditional execution
    condition:
      run_if: "{steps.evaluate.needs_improvement}"  # Future: support conditionals

# Chain-level model defaults (used if step doesn't specify)
defaults:
  provider: "openai"
  model: "gpt-4o"
  temperature: 0.7
  max_tokens: 2000

# Metadata
tags: ["chain", "evaluator-optimizer", "code-improvement"]
created: "2024-11-29"
```

### Chain Execution Flow

```
Step 1: Evaluate
┌─────────────────────────────────────────────────────────┐
│ Context Variables:                                      │
│   - code_to_evaluate: <SampleService.java content>     │
│   - coding_standards: <standards.md content>           │
│                                                         │
│ Step Variables:                                         │
│   - evaluation_criteria: "correctness, performance..." │
│   - max_issues: "10"                                   │
│                                                         │
│ Prompts:                                               │
│   - system-evaluator.st (interpolated)                 │
│   - user-evaluator.st (interpolated)                   │
│                                                         │
│ → LLM Call → evaluation output                        │
└─────────────────────────────────────────────────────────┘
                          ↓
Step 2: Optimize
┌─────────────────────────────────────────────────────────┐
│ Context Variables:                                      │
│   - code_to_evaluate: <SampleService.java content>     │
│   - coding_standards: <standards.md content>           │
│                                                         │
│ Step Variables:                                         │
│   - evaluation: <output from step 1>                   │
│   - optimization_focus: "Address all critical..."      │
│                                                         │
│ Prompts:                                               │
│   - system-optimizer.st (interpolated)                 │
│   - user-optimizer.st (interpolated)                   │
│                                                         │
│ → LLM Call → optimized_code output                    │
└─────────────────────────────────────────────────────────┘
                          ↓
Step 3: Validate
┌─────────────────────────────────────────────────────────┐
│ Context Variables (partially overridden):              │
│   - code_to_evaluate: <optimized_code from step 2>     │
│   - coding_standards: <standards.md content>           │
│                                                         │
│ Step Variables:                                         │
│   - previous_evaluation: <output from step 1>          │
│   - evaluation_criteria: "Compare with previous..."    │
│                                                         │
│ Prompts:                                               │
│   - system-evaluator.st (interpolated)                 │
│   - user-evaluator.st (interpolated)                   │
│                                                         │
│ → LLM Call → final_evaluation output                  │
└─────────────────────────────────────────────────────────┘
```

---

## Variable Interpolation Syntax

### Context Variables
```
{context.code_to_evaluate}
{context.coding_standards}
```

### Step Outputs
```
{steps.evaluate.output}           # Full output from 'evaluate' step
{steps.optimize.output}           # Full output from 'optimize' step
```

### Nested Access (Future)
```
{steps.evaluate.output.issues[0]}      # First issue from JSON response
{steps.evaluate.output.severity}       # Severity field
```

---

## Template Syntax Support

### Configurable Delimiters

The tool supports any delimiter configuration:

| Config | Example | Common Usage |
|--------|---------|--------------|
| `{` `}` | `{variable}` | Spring default, Python, Jinja2 |
| `$` `$` | `$variable$` | StringTemplate alternate |
| `<` `>` | `<variable>` | StringTemplate alternate |
| `[[` `]]` | `[[variable]]` | MediaWiki style |
| `${` `}` | `${variable}` | Shell, Spring EL |

**Variable Extraction:**
```python
def extract_variables(template: str, start: str, end: str) -> List[str]:
    """
    Extract variable names from template with custom delimiters.

    Example:
      template = "Hello {name}, your code: {code}"
      start = "{"
      end = "}"
      → ["name", "code"]
    """
    # Escape special regex chars
    start_escaped = re.escape(start)
    end_escaped = re.escape(end)

    # Pattern: {start}word_chars{end}
    pattern = f'{start_escaped}(\\w+){end_escaped}'
    return re.findall(pattern, template)
```

**Variable Substitution:**
```python
def render_template(template: str, variables: Dict, start: str, end: str) -> str:
    """
    Render template with variables using custom delimiters.

    Example:
      template = "Hello {name}"
      variables = {"name": "Alice"}
      start = "{"
      end = "}"
      → "Hello Alice"
    """
    result = template
    for key, value in variables.items():
        placeholder = f"{start}{key}{end}"
        result = result.replace(placeholder, str(value))
    return result
```

---

## File Discovery & Matching

### Discovery Process

1. **Scan prompt_dir:**
   ```
   src/main/resources/prompts/
   ├── system-evaluator.st
   ├── user-evaluator.st
   ├── system-optimizer.st
   ├── user-optimizer.st
   └── legacy-prompt.st
   ```

2. **Scan vars_dir:**
   ```
   src/test/resources/prompts/vars/
   ├── evaluator.yaml
   ├── optimizer.yaml
   └── evaluator-optimizer-chain.yaml
   ```

3. **Auto-match prompts to vars:**
   - `evaluator.yaml` → `system-evaluator.st` + `user-evaluator.st`
   - `optimizer.yaml` → `system-optimizer.st` + `user-optimizer.st`
   - `legacy-prompt.st` → ⚠️ orphan (no matching var file)

4. **Display in UI:**
   ```
   Prompts/
   ├── evaluator (system, user)
   ├── optimizer (system, user)
   └── ⚠️ legacy-prompt (orphan)

   Chains/
   └── evaluator-optimizer-chain
   ```

### Matching Rules

**Naming convention:** `{role}-{name}.{ext}`

| Prompt File | Extracted Name | Matched Var File |
|-------------|----------------|------------------|
| `system-evaluator.st` | `evaluator` | `evaluator.yaml` |
| `user-evaluator.st` | `evaluator` | `evaluator.yaml` |
| `system-optimizer.st` | `optimizer` | `optimizer.yaml` |
| `legacy-prompt.st` | N/A (no role prefix) | ⚠️ orphan |

**Override in var file:**
```yaml
# evaluator.yaml
prompts:
  system: "custom-system.st"      # Override auto-match
  user: "user-evaluator.st"       # Use auto-match (or explicit)
```

---

## UI Layout

### Left Navigation Panel

```
┌──────────────────────────────┐
│ 📁 Workspace: MyApp          │
│    Branch: main [●2]         │
├──────────────────────────────┤
│ 🔍 Search prompts...         │
├──────────────────────────────┤
│ 📝 Prompts                   │
│   ▸ evaluator               │
│   ▸ optimizer               │
│   ⚠️ legacy-prompt (orphan) │
│                              │
│ 🔗 Chains                    │
│   ▸ evaluator-optimizer     │
│                              │
│ 📊 History                   │
│   ▸ Recent runs (5)         │
│                              │
│ 🔧 Settings                  │
│   • Workspace config        │
│   • Providers               │
│   • Git status              │
└──────────────────────────────┘
```

### Main Workspace

```
┌─────────────────────────────────────────────────────────────────┐
│ [Provider: OpenAI ▼] [Model: gpt-4o ▼] [Temp: 0.7] [⚙️ ▼]     │
├─────────────────────────────────────────────────────────────────┤
│ Prompt: evaluator                                    [Save] [▶️ Run]│
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ System Prompt  [system-evaluator.st]              [Edit 📝]│ │
│ │ ─────────────────────────────────────────────────────────── │ │
│ │ You are an expert code reviewer...                         │ │
│ │ (collapsed - click to expand)                              │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ User Prompt  [user-evaluator.st]                  [Edit 📝]│ │
│ │ ─────────────────────────────────────────────────────────── │ │
│ │ Please evaluate the following code:                        │ │
│ │                                                             │ │
│ │ ```java                                                     │ │
│ │ {code_to_evaluate}                                         │ │
│ │ ```                                                         │ │
│ │                                                             │ │
│ │ Evaluation criteria: {evaluation_criteria}                 │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ Variables  [evaluator.yaml]                                    │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ code_to_evaluate         [📄 File]                          │ │
│ │   ../../examples/SampleService.java                        │ │
│ │   [Browse...] [Preview ▼]                                  │ │
│ │                                                             │ │
│ │ evaluation_criteria      [📝 Value]                         │ │
│ │   - Code correctness and logic                             │ │
│ │   - Performance and efficiency                             │ │
│ │   - Security best practices                                │ │
│ │   [Edit...]                                                │ │
│ │                                                             │ │
│ │ coding_standards         [📄 File]                          │ │
│ │   ../../docs/java-coding-standards.md                      │ │
│ │   [Browse...] [Preview ▼]                                  │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Tabs: [Formatted] [Raw Request] [Raw Response]             │ │
│ │ ─────────────────────────────────────────────────────────── │ │
│ │ Response appears here...                                   │ │
│ │                                                             │ │
│ │ [Copy] [Save to File]                                      │ │
│ │                                                             │ │
│ │ Tokens: 1,234 | Cost: $0.05 | Time: 2.3s                  │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Maven/Gradle Awareness (Nice-to-Have)

### Auto-Detection

When opening a workspace, detect project structure:

```python
def detect_project_type(path: Path) -> Optional[str]:
    """Detect project type from directory structure."""
    if (path / "pom.xml").exists():
        return "maven"
    elif (path / "build.gradle").exists() or (path / "build.gradle.kts").exists():
        return "gradle"
    elif (path / "package.json").exists():
        return "nodejs"
    elif (path / "requirements.txt").exists() or (path / "pyproject.toml").exists():
        return "python"
    return None
```

### Auto-Suggest Layout

```
Detected: Maven project
Suggested layout:
  prompt_dir: src/main/resources/prompts
  vars_dir: src/test/resources/prompts/vars

[Accept] [Customize]
```

---

## Implementation Notes

### Phase 1 Priorities

1. **Workspace management** - Critical foundation
2. **Configurable delimiters** - Support Spring's flexibility
3. **File auto-matching** - Low-friction UX
4. **Basic variable UI** - Core iteration workflow

### Phase 2 Priorities

1. **Chain builder** - Evaluator-optimizer pattern
2. **Chain execution engine** - Sequential step processing
3. **Chain debugging UI** - See intermediate results

### Phase 3 Priorities

1. **Maven/Gradle detection** - Nice-to-have
2. **Advanced chain features** - Conditionals, loops
3. **Visual workflow builder** - Drag-drop chains

---

## Open Questions

1. **Delimiter escaping**: How to handle literal `{` or `}` in prompts when using those as delimiters?
   - Suggestion: `\{` and `\}` for escaping

2. **Chain state persistence**: Should chain execution state be saved between runs?
   - Suggestion: Save to `chain_runs/` directory with timestamp

3. **Multi-role prompts**: What if you need more than system/user?
   - Suggestion: Support arbitrary roles: `assistant-evaluator.st`, `context-evaluator.st`

4. **Variable validation**: Should the tool validate variables before running?
   - Check file paths exist
   - Check required variables are defined
   - Type checking (future)?

---

**Last Updated**: 2024-11-29
