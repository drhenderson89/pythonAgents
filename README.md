# pythonAgents
Creating python AI agents interacting with local Ollama LLM

> ⚠️ **Development Toy / Not Production**
>
> This project is an experimental learning tool. It is **not production-ready** and should be used only in a **controlled, dockerized environment**.
>
> The agent can execute Python code via tools. To reduce risk, run it with container isolation and keep tool access limited to the mounted sandbox workspace.

## Overview
This project implements an AI agent that can interact with your local file system, execute Python code, and perform calculations. The agent uses LangChain and Ollama for natural language understanding and tool execution.

It supports both:
- a local CLI workflow (`cli/main.py`)
- a containerized `web` + `agent` + `ollama` architecture via Docker Compose

## Features

### AI Agent with Tools
The agent has access to the following tools:
- **read_file_tool**: Read files from the working directory
- **write_file_tool**: Write or create files in the working directory
- **list_directory_tool**: List contents of directories
- **execute_python_code**: Execute Python code snippets
- **calculate_expression**: Evaluate mathematical expressions with support for:
  - Basic operators: `+`, `-`, `*`, `/`
  - Parentheses/brackets: `()`, `[]`, `{}`
  - Negative numbers: `-5`, `-(5+3)`
  - Complex expressions: `(10+5)*2-(8/2)`

### Advanced Calculator
The calculator module supports:
- Expressions with or without spaces: `10+5*2` or `10 + 5 * 2`
- Operator precedence: `*` and `/` before `+` and `-`
- Parentheses for grouping: `(3+5)*2`
- All bracket types: `()`, `[]`, `{}`
- Negative numbers: `-5 + 3`, `10 * -2`
- Unary negation: `-(5+3)`
- Decimal numbers: `3.5 + 2.5`

## Installation

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) installed
- [Ollama](https://ollama.ai/) installed and running
- A compatible model downloaded (default in this project: `qwen2.5:7b-instruct`)

### Setup
1. Clone this repository
2. Install dependencies:
   ```bash
   uv add -r requirements.txt
   ```
3. Make sure Ollama is running:
   ```bash
   ollama serve
   ```
4. Download a model if you haven't already:
   ```bash
   ollama pull qwen2.5:7b-instruct
   ```

## Usage

### Running the Agent
Start the interactive agent loop:
```bash
python -m cli.main
```

With options:
```bash
python -m cli.main --model qwen2.5:7b-instruct --verbose --ollama-address http://localhost:11434
```

### Running the Containerized Stack (Web + Agent + Ollama)
Start all services:
```bash
docker compose up --build
```

Then open:
- Web UI: `http://localhost:8000`
- Agent API health: `http://localhost:8001/health`
- Ollama API: `http://localhost:11434`

Stop the stack:
```bash
docker compose down
```

The agent container uses a bind mount (`./agent_workspace:/workspace`) so you can add context files from the host, and all file tools are sandboxed to that directory.

Web conversation memory:
- The web UI sends a `session_id` with each prompt for the current page session.
- The agent service keeps per-session message history in memory, so follow-up prompts can use prior tool outputs.
- Refreshing the web page creates a new `session_id` and starts a fresh conversation context.

### Command Line Arguments
- `--model`: Name of the Ollama model to use (default: `qwen2.5:7b-instruct`)
- `--system-prompt`: Custom system prompt for the AI
- `--ollama-address`: Ollama server address (default: `http://127.0.0.1:11434`)
- `--max-iterations`: Maximum tool/reasoning steps per prompt turn
- `--verbose`: Enable verbose output to see tool calls and intermediate steps

### Example Interactions

#### File Operations
```
You: Read the config.json file
Assistant: [Using tool: read_file_tool]
Assistant: The config.json file contains...

You: Create a new file called test.txt with the content "Hello World"
Assistant: [Using tool: write_file_tool]
Assistant: Successfully wrote 11 characters to 'test.txt'.

You: List all files in the current directory
Assistant: [Using tool: list_directory_tool]
Assistant: Contents of '.':
[DIR]  calculator/
[FILE] config.json (450 bytes)
[FILE] main.py (3245 bytes)
...
```

#### Code Execution
```
You: Calculate the factorial of 5 using Python
Assistant: [Using tool: execute_python_code]
Assistant: I'll calculate the factorial of 5:

def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n-1)

print(factorial(5))

Result: 120
```

#### Calculations
```
You: What is (10 + 5) * 2 - 8 / 2?
Assistant: [Using tool: calculate_expression]
Assistant: The result is 26.0

You: Calculate -5 * (3 + 2) + 10
Assistant: [Using tool: calculate_expression]
Assistant: The result is -15.0
```

#### Complex Workflows
```
You: Read calculator/tests.py, count how many test methods it has, and write the count to a new file
Assistant: [Using tool: read_file_tool]
[Using tool: execute_python_code]
[Using tool: write_file_tool]
Assistant: I found 60 test methods in the calculator tests. I've written this count to 'test_count.txt'.
```

## Project Structure
```
pythonAgents/
├── core/
│   └── runtime.py         # Shared agent orchestration loop for CLI + web
├── cli/
│   └── main.py             # CLI agent implementation
├── webagents/
│   ├── agent_service.py    # FastAPI agent service (tool execution + LLM)
│   └── web_service.py      # FastAPI web UI service
├── main.py                 # Compatibility entrypoint for CLI
├── Dockerfile.agent        # Agent container image
├── Dockerfile.web          # Web container image
├── docker-compose.yml      # web + agent + ollama stack
├── model_handler.py        # Model initialization (legacy)
├── config.json             # Configuration for LLM options
├── requirements.txt        # Python dependencies
├── functions/              # Tools exposed to the agent
├── calculator/
│   ├── pkg/
│   │   └── calculator.py  # Calculator implementation with tokenizer
│   └── tests.py           # Comprehensive test suite (60+ tests)
├── pyproject.toml         # Project metadata
└── README.md              # This file
```

## Configuration
Edit `config.json` to customize:
- System prompt for the agent
- Temperature (creativity level)
- Maximum tokens to generate
- RAG options (if using retrieval-augmented generation)

Runtime logging:
- CLI: use `--verbose` for detailed step logging (iteration/tool/status/result preview)
- Web/Agent container: set `AGENT_LOG_LEVEL` (`DEBUG`, `INFO`, `WARNING`, `ERROR`) in `docker-compose.yml`

## Running Tests
Test the calculator module:
```bash
cd calculator
python tests.py
```

All tests should pass, covering:
- Basic arithmetic operations
- Operator precedence
- Parentheses and brackets
- Negative numbers
- Unary negation
- Complex expressions
- Error handling

## Security Notes
- This project is intended for development/testing and education, not production workloads
- File operations are restricted to the configured working directory (`AGENT_WORKDIR`) and subdirectories
- Python code execution runs in a restricted environment
- Absolute paths and `..` are not allowed in file operations
- In Docker Compose, the host filesystem is isolated from tools by mounting only `./agent_workspace` into `/workspace` in the agent container
- Use Docker isolation and avoid mounting sensitive host paths, because agent tools can execute Python against mounted files

## Troubleshooting

### Model Not Found
```bash
ollama pull qwen2.5:7b-instruct
```

### Connection Refused
Make sure Ollama is running (CLI mode):
```bash
ollama serve
```

If using Docker Compose, check service health:
```bash
docker compose ps
```

### Import Errors
Install dependencies:
```bash
uv add -r requirements.txt
```

## License
This project is open source under the **MIT License**. See [LICENSE](LICENSE).
