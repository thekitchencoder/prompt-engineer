"""Setup for Prompt Engineer CLI tool."""

from setuptools import setup, find_packages

setup(
    name="prompt-engineer",
    version="0.1.0",
    description="Developer workbench for rapid AI prompt engineering iteration",
    author="The Kitchen Coder",
    packages=find_packages(),
    install_requires=[
        "gradio>=6.0.0",
        "openai>=1.0.0",
        "pyyaml>=6.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "prompt-engineer=prompt_engineer.app:main",
        ],
    },
    python_requires=">=3.9",
)
