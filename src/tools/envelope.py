from __future__ import annotations

from pydantic import BaseModel


class Artifact(BaseModel):
    path_hint: str
    media_type: str
    content: str


class ToolResult(BaseModel):
    summary: str
    artifacts: list[Artifact]
