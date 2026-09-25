import datetime
from typing import Optional

from pydantic import BaseModel


class ProcessTemplateCreateRequest(BaseModel):
    category: str
    title: str
    description: str
    department_id: Optional[str] = None
    required_items: Optional[str] = None
    form_doc_url: Optional[str] = None
    contact_teacher_id: Optional[str] = None


class ProcessTemplateUpdateRequest(BaseModel):
    category: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    department_id: Optional[str] = None
    required_items: Optional[str] = None
    form_doc_url: Optional[str] = None
    contact_teacher_id: Optional[str] = None


class ProcessTemplateResponse(BaseModel):
    id: str
    school_id: str
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    category: str
    title: str
    description: str
    required_items: Optional[str] = None
    form_doc_url: Optional[str] = None
    contact_teacher_id: Optional[str] = None
    contact_teacher_name: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
