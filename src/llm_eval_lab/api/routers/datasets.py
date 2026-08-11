from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from llm_eval_lab.api.deps import get_db
from llm_eval_lab.datasets.repository import (
    create_dataset,
    delete_dataset,
    get_dataset,
    list_datasets,
    update_dataset,
)
from llm_eval_lab.schemas import DatasetCreate, DatasetRead, DatasetUpdate, DatasetWithTestCases

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("", response_model=DatasetRead, status_code=status.HTTP_201_CREATED)
def create_dataset_endpoint(payload: DatasetCreate, session: Session = Depends(get_db)):
    return create_dataset(session, name=payload.name, description=payload.description)


@router.get("", response_model=list[DatasetRead])
def list_datasets_endpoint(session: Session = Depends(get_db)):
    return list_datasets(session)


@router.get("/{dataset_id}", response_model=DatasetWithTestCases)
def get_dataset_endpoint(dataset_id: int, session: Session = Depends(get_db)):
    dataset = get_dataset(session, dataset_id)
    if dataset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No dataset with id={dataset_id}")
    return dataset


@router.patch("/{dataset_id}", response_model=DatasetRead)
def update_dataset_endpoint(
    dataset_id: int, payload: DatasetUpdate, session: Session = Depends(get_db)
):
    try:
        return update_dataset(
            session, dataset_id, name=payload.name, description=payload.description
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset_endpoint(dataset_id: int, session: Session = Depends(get_db)):
    try:
        delete_dataset(session, dataset_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot delete dataset {dataset_id}: it still has experiments/runs referencing it",
        ) from exc
