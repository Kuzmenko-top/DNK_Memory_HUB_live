from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from datetime import datetime

class RepoMetadata(BaseModel):
    stars: int = 0
    forks: int = 0
    watchers: int = 0
    open_issues: int = 0
    open_prs: int = 0
    primary_language: Optional[str] = None
    topics: List[str] = []
    license: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    pushed_at: Optional[datetime] = None
    last_commit_date: Optional[datetime] = None
    latest_release_tag: Optional[str] = None
    is_archived: bool = False

class RepoDossier(BaseModel):
    summary_ua: Optional[str] = Field(None, description="Короткий опис українською мовою")
    capabilities: List[str] = Field(default_factory=list, description="Технічні можливості")
    logic_flow: Optional[str] = Field(None, description="Логіка роботи або архітектурний патерн")
    dnk_fit_score: int = Field(0, ge=0, le=10, description="Оцінка корисності для DNK OS")
    use_cases: List[str] = Field(default_factory=list, description="Кейси використання")

class GoldenPassport(BaseModel):
    full_name: str
    url: str
    status: str = "pending" # pending, metadata_scanned, fully_analyzed
    metadata: Optional[RepoMetadata] = None
    dossier: Optional[RepoDossier] = None
    analyzed_at: Optional[datetime] = None
    version: str = "v1.0"
