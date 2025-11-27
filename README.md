# Prompt Engineer 🎯

A Gradio-based web app for rapid AI prompt iteration. Test and refine your prompts without restarting the application.

## Features

- **Live Prompt Editing**: Modify prompts on the fly and test immediately
- **Variable Substitution**: Use JSON variables to keep inputs fixed while iterating
- **Template Management**: Save and load your prompt templates
- **Model Selection**: Test across different OpenAI models (GPT-4o, GPT-4 Turbo, GPT-3.5)
- **Parameter Control**: Adjust temperature and max tokens
- **No Restart Required**: Edit and test instantly

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your OpenAI API key:
```bash
cp .env.example .env
# Edit .env and add your API key
```

3. Run the app:
```bash
python app.py
```

4. Open your browser to `http://localhost:7860`

## Usage

### Basic Workflow

1. **Write Your Prompt Template**: Use `{variable_name}` syntax for variables
   ```
   You are a {role}.

   Context: {background}

   Task: {task}
   ```

2. **Configure Variables**: Define each variable as either a fixed value or file reference
   ```
   # Click "🔍 Generate Variable Config" to auto-generate template
   role:value:helpful assistant
   background:file:variables/company_context.md
   task:value:Explain quantum computing
   ```

3. **Test**: Click "🚀 Test Prompt" to see the formatted prompt and API response

4. **Iterate**: Modify the template or variables and test again - no restart needed!

### Variable Configuration Format

Variables can be defined in two ways:

**Fixed Value:**
```
variable_name:value:Your text content here
```

**File Reference (for large markdown/YAML/code):**
```
variable_name:file:path/to/your/file.md
```

This is perfect for:
- Large markdown documentation
- YAML configuration files
- Code snippets
- Data structures
- Any content you want to keep in separate files

### Template Management

- **Save**: Give your template a name and click "💾 Save" (saves both template and variable config)
- **Load**: Enter a template name and click "📂 Load" (loads both)
- **List**: Click "📋 List" to see all saved templates

### Model Parameters

- **Model**: Choose from GPT-4o, GPT-4 Turbo, or GPT-3.5 Turbo
- **Temperature**: Control randomness (0 = deterministic, 2 = very random)
- **Max Tokens**: Limit response length

## Example Templates

### Simple Example - Customer Support
```
You are a friendly customer support agent for {company}.

Customer issue: {issue}

Provide a helpful and empathetic response.
```

Variables:
```
company:value:Acme Corp
issue:value:I received a damaged product
```

### Advanced Example - Product Announcement with File-Based Context
```
You are a professional marketing copywriter.

Company Context:
{context}

Write a compelling product announcement for: {feature_name}

Target channel: {channel}
Tone: {tone}
```

Variables:
```
context:file:variables/sample_context.md
feature_name:value:AI-Powered Workflow Suggestions
channel:value:email newsletter
tone:value:professional yet friendly
```

### Technical Spec with YAML Requirements
```
You are a senior software architect.

Project Requirements:
{requirements}

Create a technical specification for {component}.

Focus on: {focus_areas}
```

Variables:
```
requirements:file:variables/sample_requirements.yaml
component:value:authentication system
focus_areas:value:scalability and security
```

## Extending to Other AI APIs

The app is designed to be extensible. To add support for other AI APIs:

1. Create a new function similar to `call_openai()` in `app.py`
2. Add the new API to the model dropdown
3. Update the `test_prompt()` function to route to the appropriate API

## Project Structure

```
prompt-engineer/
├── app.py                    # Main Gradio application
├── requirements.txt          # Python dependencies
├── .env.example              # Environment template
├── .env                      # Your API keys (git-ignored)
├── templates/                # Saved prompt templates
│   ├── *.txt                # Template files
│   └── *.vars               # Variable configuration files
├── variables/                # Reusable variable content files
│   ├── sample_context.md    # Example: company/product context
│   ├── sample_requirements.yaml  # Example: YAML specifications
│   ├── sample_code.py       # Example: code to review
│   └── sample_data.md       # Example: data for analysis
└── README.md                 # This file
```

### Sample Files Included

The project includes sample variable files to get you started:

- **variables/sample_context.md** - Company and product context
- **variables/sample_requirements.yaml** - Technical requirements in YAML
- **variables/sample_code.py** - Python code for review
- **variables/sample_data.md** - Business data for analysis

Load the included templates to see how these work:
- `product_announcement` - Uses file-based company context
- `technical_spec` - Uses YAML requirements file
- `data_analysis` - Uses markdown data file

## License

MIT
