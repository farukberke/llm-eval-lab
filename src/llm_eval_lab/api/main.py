from fastapi import FastAPI

from llm_eval_lab.api.routers import datasets, experiments, results

app = FastAPI(title="LLM Evaluation Lab")

app.include_router(datasets.router)
app.include_router(experiments.router)
app.include_router(results.router)
