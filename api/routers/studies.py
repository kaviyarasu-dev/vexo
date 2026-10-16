from fastapi import APIRouter, Query, Request
from typing import Optional, List
from api.models.envelope import ApiResponse
from services.study_catalog_service import StudyCatalogService, StudyItem

router = APIRouter()
_catalog_service = StudyCatalogService()


@router.get("/api/v1/studies/catalog", response_model=ApiResponse[List[StudyItem]])
def get_studies_catalog(
    request: Request,
    query: Optional[str] = Query(None, description="Search term across name and tags"),
    section: Optional[str] = Query(None, description="personal | builtin | community"),
    category: Optional[str] = Query(None, description="technicals | fundamentals | scripts | community"),
    sub_category: Optional[str] = Query(None, description="indicators | strategies | profiles | patterns | options"),
):
    correlation_id = getattr(request.state, "correlation_id", "req-studies-catalog")

    if query:
        results = _catalog_service.search_studies(
            query=query,
            section=section,
            sub_category=sub_category
        )
    else:
        results = _catalog_service.get_catalog(
            section=section,
            category=category,
            sub_category=sub_category
        )

    return ApiResponse.success_response(data=results, correlation_id=correlation_id)


@router.get("/api/v1/studies/{study_id}", response_model=ApiResponse[Optional[StudyItem]])
def get_study_details(
    request: Request,
    study_id: str
):
    correlation_id = getattr(request.state, "correlation_id", f"req-study-{study_id}")
    study = _catalog_service.get_study_by_id(study_id)
    return ApiResponse.success_response(data=study, correlation_id=correlation_id)


@router.post("/api/v1/studies/custom", response_model=ApiResponse[StudyItem])
def create_custom_study(
    request: Request,
    study: StudyItem
):
    correlation_id = getattr(request.state, "correlation_id", "req-create-study")
    created = _catalog_service.add_custom_study(study)
    return ApiResponse.success_response(data=created, correlation_id=correlation_id)


@router.delete("/api/v1/studies/custom/{study_id}", response_model=ApiResponse[bool])
def delete_custom_study(
    request: Request,
    study_id: str
):
    correlation_id = getattr(request.state, "correlation_id", f"req-delete-study-{study_id}")
    success = _catalog_service.delete_custom_study(study_id)
    return ApiResponse.success_response(data=success, correlation_id=correlation_id)

