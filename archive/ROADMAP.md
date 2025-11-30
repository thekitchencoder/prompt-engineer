# Prompt Engineer - Product Roadmap

## Vision
A low-friction developer workbench for rapid prompt engineering iteration. Capture prompts from running applications, iterate quickly with fixed variables, version changes, and test complex workflows before compiling back into production applications.

## Core Architecture Decision: Workspace-Centric

**Prompts live in your application's source code, not in Prompt Engineer.**

This tool is a **workbench**, not a database. It points to prompt files in your SpringBoot/Python/Node.js app, edits them in-place, and leverages your existing git workflow for version control.

```
Your App Repo/
├── src/main/resources/prompts/          # Production prompts (.st files)
├── src/test/resources/prompts/vars/     # Test/dev variable configs (.yaml)
└── .prompt-engineer/workspace.yaml      # Workspace configuration

Prompt Engineer just points here ↑
```

**Benefits:**
- Single source of truth (your app's git repo)
- Zero sync issues
- Standard git workflow (branch, commit, PR, review)
- Prompts are code (CI/CD tested alongside app)

See [DESIGN.md](./DESIGN.md) for detailed architecture.

---

## Target Users
1. **Phase 1**: Personal use (solo developer)
2. **Phase 2**: Team use (collaborative prompt engineering)
3. **Phase 3**: Public tool (open source community)

---

## Key Design Decisions

### 1. Configurable Variable Delimiters
Spring allows custom delimiters. Workspace config supports any delimiter:
- `{variable}` (Spring default, Python)
- `$variable$` (StringTemplate)
- `<variable>` (StringTemplate)
- `[[variable]]` (custom)

### 2. Convention-Based File Discovery
- **Prompts**: `{role}-{name}.st` (e.g., `system-evaluator.st`, `user-evaluator.st`)
- **Variables**: `{name}.yaml` (e.g., `evaluator.yaml`)
- Auto-match by name, allow manual override

### 3. Multi-Language Support
- SpringBoot (`.st` files in `src/main/resources/prompts`)
- Python (`.txt` files in `app/prompts`)
- Node.js (`.txt` files in `src/prompts`)
- Custom layouts (configure in workspace.yaml)

### 4. Minimal Git Integration
- Show branch, uncommitted count in UI
- File watcher for external changes
- User handles commits via terminal/git client

### 5. Evaluator-Optimizer Pattern (Primary Use Case)
Chain steps where:
1. **Evaluate** code → capture issues
2. **Optimize** code using evaluation → capture optimized code
3. **Validate** optimized code → final evaluation

---

# Implementation Roadmap

## Phase 1: Foundation & Core Developer Experience
**Goal**: Create a solid, modular foundation with excellent UX for rapid iteration

### 1.1 Code Architecture Refactor
**Priority**: CRITICAL - Enables all future work

- [ ] **Task 1.1.1**: Design modular architecture
  - Create package structure: `src/prompt_engineer/`
  - Define modules: `core/`, `ui/`, `providers/`, `workspace/`, `templates/`, `chains/`
  - Design clear interfaces between modules

- [ ] **Task 1.1.2**: Extract provider logic
  - Create `providers/base.py` with abstract `LLMProvider` class
  - Implement `providers/openai.py`, `providers/ollama.py`, etc.
  - Add provider registry/factory pattern
  - Support for streaming responses

- [ ] **Task 1.1.3**: Workspace management system
  - Create `workspace/workspace.py` - manages workspace config and file discovery
  - Create `workspace/config.py` - workspace.yaml schema (Pydantic models)
  - Create `workspace/discovery.py` - auto-detect project type, scan/match files
  - Support multiple workspace layouts (SpringBoot, Python, Node.js, custom)

- [ ] **Task 1.1.4**: Template system (language-agnostic)
  - Create `templates/parser.py` - configurable variable delimiter support
  - Create `templates/resolver.py` - variable interpolation from files/values
  - Create `templates/models.py` - Template, Variable, Prompt data classes
  - Support for system/user/custom role separation

- [ ] **Task 1.1.5**: Configuration management
  - Create `config/settings.py` using Pydantic for type safety
  - Support workspace.yaml, .env files
  - Environment-based config (dev/prod)
  - Provider presets (OpenAI, Ollama, etc.)

**Deliverable**: Clean, testable codebase with clear separation of concerns

---

### 1.2 Modern UI/UX Overhaul
**Priority**: HIGH - Core developer experience

- [ ] **Task 1.2.1**: Workspace management UI
  - "Open Workspace" dialog
  - Auto-detect project type (Maven/Gradle/Python/Node.js)
  - Preset selection (SpringBoot, Python, Custom)
  - Generate workspace.yaml from preset
  - Recent workspaces list
  - Workspace switcher in UI

- [ ] **Task 1.2.2**: Design new layout (LMStudio-inspired)
  ```
  ┌─────────────────────────────────────────────────────────────┐
  │ [Workspace: MyApp ▼] [Branch: main ●2] [Provider] [Model] │
  ├──────────┬──────────────────────────────────────────────────┤
  │          │                                                  │
  │  Left    │  Main Workspace                                 │
  │  Nav:    │  ┌────────────────────────────────────────────┐ │
  │          │  │ System: system-evaluator.st      [Edit 📝] │ │
  │ Prompts  │  │ (collapsed - click to expand)              │ │
  │ • eval.. │  └────────────────────────────────────────────┘ │
  │ • optim..│  ┌────────────────────────────────────────────┐ │
  │          │  │ User: user-evaluator.st          [Edit 📝] │ │
  │ Chains   │  │ Please evaluate: {code_to_evaluate}        │ │
  │ • eval-..│  │ Criteria: {evaluation_criteria}            │ │
  │          │  └────────────────────────────────────────────┘ │
  │ History  │  Variables [evaluator.yaml]                    │
  │          │  [code_to_evaluate 📄] [evaluation_criteria 📝]│
  │ Settings │  ┌────────────────────────────────────────────┐ │
  │          │  │ Response: [Formatted | Raw Request | Raw]  │ │
  │          │  └────────────────────────────────────────────┘ │
  └──────────┴──────────────────────────────────────────────────┘
  ```

- [ ] **Task 1.2.3**: Left navigation panel
  - Workspace header (name, branch, git status)
  - Quick search across prompts
  - Prompts section (auto-discovered files)
    - Group by name (evaluator: system + user)
    - Show orphaned prompts (no var file)
  - Chains section (chain YAML files)
  - History section (recent runs)
  - Settings section (workspace config, providers)

- [ ] **Task 1.2.4**: Redesign prompt editor
  - System prompt section (collapsible, file name shown)
  - User prompt section (file name shown)
  - Syntax highlighting for prompt files
  - Variable highlighting (show `{var}` in different color)
  - Edit in-place or open external editor
  - Auto-reload on external file changes

- [ ] **Task 1.2.5**: Enhanced variable management UI
  - Auto-extract variables from prompts (based on workspace delimiter config)
  - Show variables as chips/cards
  - For each variable:
    - Toggle: [📝 Value] or [📄 File]
    - Value mode: textarea for inline editing
    - File mode: file path with browse button, preview
    - Validation: missing file, missing variable, etc.
  - Save changes to .yaml file
  - Drag-drop file support

- [ ] **Task 1.2.6**: Improved response display
  - Three tabs: Formatted | Raw Request | Raw Response
  - Formatted: Markdown rendering with syntax highlighting
  - Raw Request: JSON payload sent to LLM (copy button)
  - Raw Response: Full API response (copy button)
  - Footer: Token count, cost estimate, latency

- [ ] **Task 1.2.7**: Parameter controls redesign
  - Model selector (from workspace config)
  - Temperature/max_tokens sliders
  - Advanced params (collapsible)
  - Override per-prompt or use workspace defaults

**Deliverable**: Polished, intuitive UI that feels fast and low-friction

---

### 1.3 Role-Based Prompting & File Conventions
**Priority**: HIGH - Core feature

- [ ] **Task 1.3.1**: File-based role separation
  - Support `{role}-{name}.st` naming convention
  - Parse role from filename (system, user, assistant, etc.)
  - Display prompts grouped by name with roles shown
  - Allow custom role names (configurable in workspace.yaml)

- [ ] **Task 1.3.2**: Auto-matching system
  - Match prompt files to var files by name
  - `system-evaluator.st` + `user-evaluator.st` → `evaluator.yaml`
  - Warn about orphaned files (prompts without vars)
  - Allow manual override in var file

- [ ] **Task 1.3.3**: Variable file schema
  - Define YAML schema for variable configs
  - Support both file and value variable types
  - Support multiple prompt files per config
  - Validation and error handling

**Deliverable**: Convention-based file organization with auto-discovery

---

### 1.4 Raw Prompt Visibility
**Priority**: MEDIUM - Developer debugging

- [ ] **Task 1.4.1**: Add "Prepared Prompt" view
  - Show exact JSON/payload sent to LLM API
  - Syntax-highlighted JSON view
  - Copy button for debugging
  - Show headers, model, parameters

- [ ] **Task 1.4.2**: Request/Response inspector
  - Full request payload (like browser DevTools)
  - Full response payload
  - Timing breakdown (network, processing, etc.)

**Deliverable**: Complete visibility into LLM communication

---

## Phase 2: Template Management & Workflow
**Goal**: Version control, organization, and basic prompt chaining

### 2.1 Git Integration & File Management
**Priority**: MEDIUM - Leverage existing git workflow

- [ ] **Task 2.1.1**: Minimal git status UI
  - Show current branch in workspace header
  - Show count of uncommitted changes (●3 modified)
  - List modified/staged/untracked files
  - "Refresh" button to update git status
  - "Open in Git Client" button (opens external tool)

- [ ] **Task 2.1.2**: File watcher
  - Watch prompt and var files for external changes
  - Auto-reload when files change outside the tool
  - Notify user of changes
  - Handle conflicts gracefully

- [ ] **Task 2.1.3**: Folder organization
  - Support nested folders in prompt_dir
  - UI: Tree view showing folder structure
  - Organize prompts by folder in left nav
  - Search across all folders

- [ ] **Task 2.1.4**: Template metadata in YAML
  - Add metadata section to var files
  - Name, description, tags, created/modified dates
  - Track last run results (optional)
  - Performance metrics (avg response time, cost)

- [ ] **Task 2.1.5**: Search and filtering
  - Full-text search across prompt files
  - Filter by tags, folder, date modified
  - Quick find by name
  - Recent files list

**Deliverable**: Use git for version control, enhance file discovery/organization

---

### 2.2 Prompt Chaining (Evaluator-Optimizer Pattern)
**Priority**: HIGH - Core workflow for your use case

- [ ] **Task 2.2.1**: Chain YAML format
  - Define chain file schema (see DESIGN.md)
  - Support context variables (shared across steps)
  - Support step definitions (name, prompts, variables, model)
  - Output variable naming (`output_var` per step)
  - Variable interpolation syntax: `{steps.evaluate.output}`

- [ ] **Task 2.2.2**: Chain execution engine
  - Sequential step execution
  - Context variable resolution (files + values)
  - Step output capture and interpolation into next steps
  - Error handling (stop on error, log step results)
  - Save execution history with timestamps

- [ ] **Task 2.2.3**: Chain editor UI
  - Load chain YAML file
  - Display steps as expandable sections
  - Edit step configuration (prompts, variables, model)
  - Preview interpolated prompts before execution
  - Add/remove/reorder steps
  - Save changes back to YAML

- [ ] **Task 2.2.4**: Chain execution UI
  - "Run Chain" button
  - Progress indicator (show current step)
  - Intermediate results display (each step's output)
  - Highlight variable flow (where each variable came from)
  - Stop/resume execution
  - Export all results

- [ ] **Task 2.2.5**: Chain debugging tools
  - Step-by-step execution (pause between steps)
  - Re-run single step with modified inputs
  - Inspect interpolated variables at each step
  - Save successful runs as new test cases

- [ ] **Task 2.2.6**: Chain templates
  - Evaluator-Optimizer template
  - Evaluator-Optimizer-Validator template
  - Multi-round refinement template
  - Quick-start wizard for common patterns

**Deliverable**: Robust chaining system for evaluator-optimizer workflows

---

### 2.3 Testing & Comparison
**Priority**: MEDIUM - Important for prompt evolution

- [ ] **Task 2.3.1**: A/B testing framework
  - Compare two prompt versions side-by-side
  - Same variables, different prompts
  - Diff view of responses

- [ ] **Task 2.3.2**: Batch testing
  - Run same prompt with multiple variable sets
  - CSV import for variable sets
  - Aggregate results view
  - Export results as CSV/JSON

- [ ] **Task 2.3.3**: Response evaluation
  - Manual rating (thumbs up/down, 1-5 stars)
  - Store ratings with versions
  - Compare ratings across versions
  - Automated evaluation using another LLM (meta-evaluation)

**Deliverable**: Tools to objectively compare prompt performance

---

## Phase 3: Advanced Features
**Goal**: Proxy debugging, deployment, testing, advanced workflows

### 3.1 Proxy/Intercept Mode
**Priority**: MEDIUM - Powerful debugging feature

- [ ] **Task 3.1.1**: HTTP proxy server
  - Implement proxy server (listens on configurable port)
  - Forward requests to actual LLM providers
  - Capture request/response

- [ ] **Task 3.1.2**: Proxy capture UI
  - Real-time list of captured requests
  - View captured prompts
  - Save captured prompt as template
  - Edit and replay captured requests

- [ ] **Task 3.1.3**: Proxy configuration
  - Configure which providers to proxy
  - Request filtering (ignore certain patterns)
  - SSL/TLS support for HTTPS

- [ ] **Task 3.1.4**: Integration guide
  - Document how to configure apps to use proxy
  - Example configurations for common tools

**Deliverable**: Man-in-the-middle debugging for capturing production prompts

---

### 3.2 Visual Workflow Builder
**Priority**: MEDIUM - Advanced chaining

- [ ] **Task 3.2.1**: Graph-based UI
  - Node-based workflow editor (like n8n, Langflow)
  - Nodes: Prompt, Transform, Branch, Join
  - Visual connection lines showing data flow

- [ ] **Task 3.2.2**: Control flow nodes
  - Conditional branching (if/else based on response)
  - Loops (iterate over lists)
  - Parallel execution (run multiple prompts simultaneously)

- [ ] **Task 3.2.3**: Transform nodes
  - Text manipulation (extract, replace, format)
  - JSON parsing
  - Custom JavaScript/Python transforms

- [ ] **Task 3.2.4**: Workflow execution
  - Visual execution trace (highlight active nodes)
  - Pause/resume/step-through
  - Error handling and retry logic

**Deliverable**: Visual workflow builder for complex prompt orchestration

---

### 3.3 Testing & Quality
**Priority**: MEDIUM - Code quality

- [ ] **Task 3.3.1**: Unit test framework
  - pytest setup
  - Test coverage for core modules (>80%)
  - Mock LLM providers for testing

- [ ] **Task 3.3.2**: Integration tests
  - Test full workflows end-to-end
  - Test provider integrations (with mock servers)

- [ ] **Task 3.3.3**: UI tests
  - Gradio component tests
  - Key user flow tests (create template, run chain, etc.)

- [ ] **Task 3.3.4**: CI/CD pipeline
  - GitHub Actions for automated testing
  - Linting and type checking (mypy, ruff)
  - Automated releases

**Deliverable**: Robust test coverage for reliability

---

### 3.4 Docker & Deployment
**Priority**: MEDIUM - Easy distribution

- [ ] **Task 3.4.1**: Dockerfile
  - Multi-stage build for small image size
  - Environment configuration via env vars
  - Volume mounts for persistent data

- [ ] **Task 3.4.2**: Docker Compose
  - Single command startup
  - Configure all services
  - Example configurations for different use cases

- [ ] **Task 3.4.3**: Docker Hub publishing
  - Automated builds on release
  - Version tagging (latest, semver)
  - README with usage instructions

- [ ] **Task 3.4.4**: One-click deployment
  - Railway, Render, Fly.io templates
  - Kubernetes manifests (for advanced users)

**Deliverable**: `docker run` to get started instantly

---

## Phase 4: Team & Public Release
**Goal**: Multi-user support, collaboration, public launch

### 4.1 Multi-User Support
**Priority**: LOW (future) - Team collaboration

- [ ] **Task 4.1.1**: Database backend
  - PostgreSQL support via SQLAlchemy
  - User authentication (JWT or OAuth)
  - User-specific templates and settings

- [ ] **Task 4.1.2**: Sharing & permissions
  - Share templates with team members
  - Public/private templates
  - Role-based access control (viewer/editor/admin)

- [ ] **Task 4.1.3**: Collaboration features
  - Comments on templates
  - @mentions and notifications
  - Activity feed

**Deliverable**: Team workspace for collaborative prompt engineering

---

### 4.2 API & Integrations
**Priority**: LOW (future)

- [ ] **Task 4.2.1**: REST API
  - CRUD operations for templates, chains
  - Execute prompts/chains via API
  - Webhook support for integrations

- [ ] **Task 4.2.2**: CLI tool
  - Run prompts from command line
  - CI/CD integration (test prompts in pipeline)
  - Template sync with remote

**Deliverable**: Programmatic access to all features

---

### 4.3 Documentation & Community
**Priority**: MEDIUM (ongoing)

- [ ] **Task 4.3.1**: User documentation
  - Getting started guide
  - Feature tutorials
  - Best practices guide
  - Video walkthroughs

- [ ] **Task 4.3.2**: Developer documentation
  - Architecture overview
  - API documentation
  - Plugin development guide

- [ ] **Task 4.3.3**: Community building
  - GitHub discussions
  - Template marketplace
  - Example workflows/templates

**Deliverable**: Comprehensive docs and active community

---

## Additional Enhancements (Not in Original List)

### Performance & Optimization
- [ ] Response streaming (show tokens as they arrive)
- [ ] Response caching (avoid duplicate API calls)
- [ ] Background job queue for long-running chains
- [ ] Rate limiting and quota management

### Developer Experience
- [ ] Keyboard shortcuts (Cmd+Enter to run, Cmd+S to save, etc.)
- [ ] Dark/light theme toggle
- [ ] Customizable UI layouts
- [ ] Undo/redo for prompt editing
- [ ] Auto-save drafts

### Analytics & Insights
- [ ] Token usage tracking over time
- [ ] Cost analytics (spending by project/prompt)
- [ ] Response quality trends
- [ ] Performance dashboards

### Advanced Variable Features
- [ ] Secret management (API keys, credentials in variables)
- [ ] Environment variables (dev/staging/prod)
- [ ] Dynamic variables (current date, random values, etc.)
- [ ] Variable validation rules (regex, type checking)

### Export & Integration
- [ ] Export as Python code (prompt → production code)
- [ ] LangChain integration
- [ ] OpenAI SDK code generation
- [ ] Postman collection export

### Model Support
- [ ] Claude artifacts rendering (interactive components)
- [ ] Vision model support (image inputs)
- [ ] Function calling / tool use UI
- [ ] Multi-modal inputs (audio, video)

---

## Recommended Implementation Order

### Sprint 1-2 (Weeks 1-4): Foundation & Workspace
1. **Code refactoring** (1.1) - Modular architecture
   - Workspace management system
   - Configurable template parser (delimiter support)
   - Provider abstraction
2. **Workspace UI** (1.2.1) - Open workspace, auto-detect, presets
3. **File conventions** (1.3) - Role-based naming, auto-matching

**Why**: Workspace-centric foundation is critical for all features. Get this right first.

**Deliverable**: Can open SpringBoot project, auto-discover prompts, see system/user files

---

### Sprint 3-4 (Weeks 5-8): Core UX & Iteration
1. **New UI layout** (1.2.2-1.2.4) - Left nav, prompt editor, variable UI
2. **Variable management** (1.2.5) - Auto-extract, file/value toggle, validation
3. **Response display** (1.2.6) - Formatted, raw request, raw response
4. **Raw visibility** (1.4) - Full request/response inspection

**Why**: Achieves core "low-friction iteration" goal. This is your daily workflow.

**Deliverable**: Fast, intuitive prompt iteration with clear variable management

---

### Sprint 5-6 (Weeks 9-12): Chaining & Git
1. **Prompt chaining** (2.2) - Chain YAML format, execution engine, debugging
2. **Git integration** (2.1.1-2.1.2) - Minimal status UI, file watcher
3. **File organization** (2.1.3-2.1.5) - Folders, search, metadata

**Why**: Enables evaluator-optimizer pattern (your primary use case) and version control via git

**Deliverable**: Can build and debug multi-step evaluator-optimizer chains

---

### Sprint 7-8 (Weeks 13-16): Proxy & Quality
1. **Proxy server** (3.1) - Capture production prompts, save as templates
2. **Unit tests** (3.3) - Core functionality coverage
3. **Docker** (3.4) - Easy distribution and deployment
4. **Testing tools** (2.3) - A/B comparison, batch testing

**Why**: Debug production apps, ensure code quality, make it easy to deploy

**Deliverable**: Can intercept app prompts, containerized deployment

---

### Sprint 9+ (Weeks 17+): Advanced Features
1. **Visual workflow builder** (3.2) - Graph-based chain editor
2. **Advanced chain features** - Conditionals, loops, parallel execution
3. **Multi-user support** (4.1) - Database, auth, sharing
4. **API & CLI** (4.2) - Programmatic access
5. **Polish** - Performance, keyboard shortcuts, themes

**Why**: Power features for advanced workflows and team collaboration

---

## Success Metrics

### Phase 1 Success
- [ ] Can create and iterate on a prompt in <30 seconds
- [ ] Zero friction variable management (no config file editing)
- [ ] Clear visibility into what's sent to LLM

### Phase 2 Success
- [ ] Can version and rollback prompts easily
- [ ] Can build evaluator-optimizer chain in <5 minutes
- [ ] Can compare prompt versions side-by-side

### Phase 3 Success
- [ ] Can capture production prompts via proxy
- [ ] Can deploy with `docker run`
- [ ] >80% test coverage

### Phase 4 Success
- [ ] Team can collaborate on prompts
- [ ] Active community sharing templates
- [ ] Used by >100 developers

---

## Notes & Decisions

### Technology Stack
- **Backend**: Python 3.12+, FastAPI (for API/proxy), SQLAlchemy (for DB)
- **UI**: Gradio 6+ (current), consider migration to React/Svelte for advanced features
- **Storage**: Filesystem → PostgreSQL for multi-user
- **Testing**: pytest, coverage.py
- **Deployment**: Docker, docker-compose
- **CI/CD**: GitHub Actions

### Migration Path
- Phase 1-2: Keep Gradio (faster iteration)
- Phase 3+: Consider custom web UI if Gradio limitations hit
- Always maintain API backend (UI-agnostic)

### Breaking Changes
- No backward compatibility required
- Free to redesign file formats, APIs
- Document migration path for own templates

---

## Questions for Further Refinement

1. **Pricing model**: Will this ever be a paid product, or always free/open source?
2. **Hosting**: Self-hosted only, or also cloud-hosted SaaS?
3. **Target scale**: How many prompts/chains/versions per project?
4. **Integration priorities**: Which tools/platforms are most important? (VSCode, Cursor, etc.)
5. **Template sharing**: Public marketplace important? Or just team sharing?

---

**Last Updated**: 2025-11-29
**Status**: Draft - Ready for Review
