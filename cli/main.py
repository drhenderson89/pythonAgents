import argparse
import json
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama.chat_models import ChatOllama

from core.runtime import build_system_prompt, configure_runtime_logger, prompt_likely_requires_tools, run_agent_turns
import functions


def generate_content_loop(model_with_tools, messages, tool_map, args, max_iterations=10):
    """Main conversation loop for the AI agent."""
    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\nExiting agent. Goodbye!")
                break

            messages.append(HumanMessage(content=user_input))

            def on_tool_event(event: dict) -> None:
                if args.verbose:
                    print(
                        f"\n[Iteration {event['iteration']}] Tool={event['tool']} "
                        f"Status={event['status']} Args={event['args']}"
                    )
                    print(f"Result: {event['result_preview']}")
                else:
                    print(f"\n[Using tool: {event['tool']}]")

            result = run_agent_turns(
                model_with_tools=model_with_tools,
                tool_map=tool_map,
                messages=messages,
                max_iterations=max_iterations,
                likely_requires_tools=prompt_likely_requires_tools(user_input),
                on_tool_event=on_tool_event,
                run_label="cli",
            )

            print(f"\nAssistant: {result['response']}")

            print()

        except KeyboardInterrupt:
            print("\n\nInterrupted. Exiting agent. Goodbye!")
            break
        except Exception as e:
            print(f"\nError: {str(e)}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            print()


def main():
    with open("config.json", mode="r", encoding="utf-8") as read_file:
        config = json.load(read_file)

    parser = argparse.ArgumentParser(
        description="AI Agent using langchain and ollama")

    def parse_arguments():
        parser.add_argument("--model", type=str,
                            default="qwen2.5:7b-instruct", help="Name of the model to use")
        parser.add_argument("--system-prompt", type=str,
                            default=config["llm_options"]["system_prompt"], help="System prompt for the ai model to use")
        parser.add_argument("--ollama-address", type=str,
                            default="http://127.0.0.1:11434", help="Ollama server address")
        parser.add_argument("--max-iterations", type=int, default=10,
                            help="Maximum reasoning/tool iterations per user turn")
        parser.add_argument("--verbose", action="store_true",
                            help="Enable verbose output")
        return parser.parse_args()

    args = parse_arguments()
    configure_runtime_logger("DEBUG" if args.verbose else "INFO")
    system_prompt = build_system_prompt(
        args.system_prompt, max_iterations=args.max_iterations)

    model = ChatOllama(
        model=args.model,
        base_url=args.ollama_address,
        temperature=config["llm_options"]["temperature"],
        num_ctx=config["llm_options"].get("num_ctx", 4096),
        num_predict=config["llm_options"]["tokens_to_generate"],
    )

    available_tools = functions.get_tools()
    model_with_tools = model.bind_tools(available_tools)
    tool_map = {tool.name: tool for tool in available_tools}

    if args.verbose:
        print("\n" + "=" * 60)
        print("TOOL SCHEMAS DEBUG:")
        print("=" * 60)
        for tool in available_tools:
            print(f"\nTool: {tool.name}")
            print(f"Description: {tool.description[:100]}...")
            if hasattr(tool, 'args_schema') and tool.args_schema:
                print(f"Args Schema: {tool.args_schema.schema()}")
            elif hasattr(tool, 'args'):
                print(f"Args: {tool.args}")
            else:
                print(f"Tool object: {tool}")
        print("=" * 60 + "\n")

    print("=" * 60)
    print("AI Agent with Tools - Powered by Ollama")
    print("=" * 60)
    print("\nAvailable tools:")
    for tool in available_tools:
        print(f"  - {tool.name}: {tool.description.split('.')[0]}")
    print("\nType 'quit' or 'exit' to stop the agent.")
    print("=" * 60)
    print()

    messages = [SystemMessage(content=system_prompt)]
    generate_content_loop(model_with_tools, messages,
                          tool_map, args, max_iterations=args.max_iterations)


if __name__ == "__main__":
    main()
