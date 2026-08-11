import argparse

from llm_eval_lab.config import settings
from llm_eval_lab.llm.factory import get_llm_client


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a single prompt to Ollama and print the response")
    parser.add_argument(
        "prompt", nargs="?", default="Why is the sky blue? Answer in one sentence."
    )
    parser.add_argument("--model", default=settings.ollama_default_model)
    args = parser.parse_args()

    client = get_llm_client("ollama", host=settings.ollama_host)
    response = client.generate(model=args.model, prompt=args.prompt)

    print(f"Model: {args.model}")
    print(f"Latency: {response.latency_ms:.0f} ms")
    print(f"Tokens: {response.prompt_tokens} prompt / {response.completion_tokens} completion")
    print(f"Response:\n{response.text}")


if __name__ == "__main__":
    main()
