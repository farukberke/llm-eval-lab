"""Thin Gradio demo UI for the LLM Evaluation Lab.

Talks to the existing FastAPI backend over HTTP via `ApiClient` — it holds
no scoring/aggregation/runner logic of its own, only orchestrates the
existing endpoints in sequence and renders the result. Run the FastAPI
backend separately (e.g. `docker compose up`) before launching this.
"""

import gradio as gr
import httpx
import pandas as pd

from llm_eval_lab.schemas import ComparisonReportRead
from llm_eval_lab.ui.api_client import ApiClient
from llm_eval_lab.ui.config import ui_settings

_client: ApiClient | None = None


def _get_client() -> ApiClient:
    global _client
    if _client is None:
        _client = ApiClient(base_url=ui_settings.fastapi_base_url)
    return _client


def _report_to_dataframe(report: ComparisonReportRead) -> pd.DataFrame:
    rows = []
    for run in report.runs:
        rows.append(
            {
                "model": run.model_name,
                "success_rate": round(run.success_rate, 3),
                "avg_latency_ms": round(run.avg_latency_ms, 1)
                if run.avg_latency_ms is not None
                else None,
                "avg_prompt_tokens": round(run.avg_prompt_tokens, 1)
                if run.avg_prompt_tokens is not None
                else None,
                "avg_completion_tokens": round(run.avg_completion_tokens, 1)
                if run.avg_completion_tokens is not None
                else None,
                "exact_match": run.avg_scores.get("exact_match"),
                "normalized_similarity": run.avg_scores.get("normalized_similarity"),
            }
        )
    return pd.DataFrame(rows)


def load_dropdown_data():
    client = _get_client()
    datasets = client.list_datasets()
    model_configs = client.list_model_configs()
    prompts = client.list_prompts()

    dataset_choices = [(d.name, d.id) for d in datasets]
    model_choices = [(f"{m.name} ({m.model_name})", m.id) for m in model_configs]
    prompt_choices = [(p.name, p.id) for p in prompts]

    return (
        gr.update(choices=dataset_choices, value=None),
        gr.update(choices=model_choices, value=None),
        gr.update(choices=model_choices, value=None),
        gr.update(choices=prompt_choices, value=None),
        {d.id: d.name for d in datasets},
        {m.id: m.name for m in model_configs},
        {p.id: p.name for p in prompts},
    )


def run_comparison(
    dataset_id, model_a_id, model_b_id, prompt_id, dataset_names, model_names, prompt_names
):
    log_lines: list[str] = []

    def log(message: str) -> str:
        log_lines.append(message)
        return "\n".join(log_lines)

    if None in (dataset_id, model_a_id, model_b_id, prompt_id):
        yield log("Select a dataset, both models, and a prompt before running."), None
        return

    dataset_name = dataset_names.get(dataset_id, str(dataset_id))
    model_a_name = model_names.get(model_a_id, str(model_a_id))
    model_b_name = model_names.get(model_b_id, str(model_b_id))
    prompt_name = prompt_names.get(prompt_id, str(prompt_id))

    client = _get_client()

    try:
        yield log(f"Preparing experiments for {model_a_name} vs {model_b_name}..."), None
        experiment_a = client.get_or_create_experiment(
            dataset_id,
            model_a_id,
            prompt_id,
            name=f"UI Demo - {model_a_name} - {dataset_name} - {prompt_name}",
        )
        experiment_b = client.get_or_create_experiment(
            dataset_id,
            model_b_id,
            prompt_id,
            name=f"UI Demo - {model_b_name} - {dataset_name} - {prompt_name}",
        )

        yield log(f"Running {model_a_name}..."), None
        run_a = client.run_experiment(experiment_a.id)

        yield log(f"Running {model_b_name}..."), None
        run_b = client.run_experiment(experiment_b.id)

        yield log("Evaluating..."), None
        client.evaluate_run(run_a.id)
        client.evaluate_run(run_b.id)

        yield log("Comparing results..."), None
        report = client.compare_runs([run_a.id, run_b.id])

        yield log("Comparison complete"), _report_to_dataframe(report)
    except httpx.HTTPError as exc:
        yield log(f"Error: {exc}"), None


def build_app() -> gr.Blocks:
    with gr.Blocks(title="LLM Evaluation Lab - Model Comparison Demo") as demo:
        gr.Markdown("# LLM Evaluation Lab — Model Comparison Demo")

        with gr.Row():
            dataset_dd = gr.Dropdown(label="Dataset")
            model_a_dd = gr.Dropdown(label="Model A")
            model_b_dd = gr.Dropdown(label="Model B")
            prompt_dd = gr.Dropdown(label="Prompt")

        with gr.Row():
            refresh_btn = gr.Button("Refresh dropdowns")
            run_btn = gr.Button("Run Comparison", variant="primary")

        status_box = gr.Textbox(label="Status", lines=6, interactive=False)
        results_table = gr.Dataframe(label="Comparison Results", interactive=False)

        dataset_names = gr.State({})
        model_names = gr.State({})
        prompt_names = gr.State({})

        dropdown_outputs = [
            dataset_dd,
            model_a_dd,
            model_b_dd,
            prompt_dd,
            dataset_names,
            model_names,
            prompt_names,
        ]
        demo.load(fn=load_dropdown_data, outputs=dropdown_outputs)
        refresh_btn.click(fn=load_dropdown_data, outputs=dropdown_outputs)

        run_btn.click(
            fn=run_comparison,
            inputs=[
                dataset_dd,
                model_a_dd,
                model_b_dd,
                prompt_dd,
                dataset_names,
                model_names,
                prompt_names,
            ],
            outputs=[status_box, results_table],
        )

    return demo


def main() -> None:
    build_app().launch(server_port=7860)


if __name__ == "__main__":
    main()
