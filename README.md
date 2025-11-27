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

   Task: {task}
   ```

2. **Define Variables**: Input as JSON
   ```json
   {
     "role": "helpful assistant",
     "task": "Explain quantum computing"
   }
   ```

3. **Test**: Click "🚀 Test Prompt" to see the formatted prompt and API response

4. **Iterate**: Modify the template and test again - no restart needed!

### Template Management

- **Save**: Give your template a name and click "💾 Save"
- **Load**: Enter a template name and click "📂 Load"
- **List**: Click "📋 List" to see all saved templates

### Model Parameters

- **Model**: Choose from GPT-4o, GPT-4 Turbo, or GPT-3.5 Turbo
- **Temperature**: Control randomness (0 = deterministic, 2 = very random)
- **Max Tokens**: Limit response length

## Example Templates

### Customer Support
```
You are a friendly customer support agent for {company}.

Customer issue: {issue}

Provide a helpful and empathetic response.
```

Variables:
```json
{
  "company": "Acme Corp",
  "issue": "I received a damaged product"
}
```

### Code Review
```
You are an expert {language} developer.

Review this code and provide feedback:

{code}

Focus on: {focus_areas}
```

Variables:
```json
{
  "language": "Python",
  "code": "def add(a, b):\n    return a + b",
  "focus_areas": "performance and best practices"
}
```

## Extending to Other AI APIs

The app is designed to be extensible. To add support for other AI APIs:

1. Create a new function similar to `call_openai()` in `app.py`
2. Add the new API to the model dropdown
3. Update the `test_prompt()` function to route to the appropriate API

## Project Structure

```
prompt-engineer/
├── app.py              # Main Gradio application
├── requirements.txt    # Python dependencies
├── .env.example        # Environment template
├── .env               # Your API keys (git-ignored)
├── templates/         # Saved prompt templates
└── README.md          # This file
```

## License

MIT
