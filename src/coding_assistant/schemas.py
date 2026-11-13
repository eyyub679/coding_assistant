from pydantic import BaseModel, Field
from typing import Literal

class ReadFileSchema(BaseModel):
    path: str = Field(
        ...,
        description="File's absolute path"
    )

class WriteFileSchema(BaseModel):
    path: str = Field(
        ...,
        description="File's absolute path"
    )
    content: str= Field(
        ...,
        description="Content of the new file"
    )

class EditFileSchema(BaseModel):
    path: str = Field(
        ...,
        description="File's absolute path"
    )
    old_string: str = Field(
        ...,
        description="String to be replaced"
    )
    new_string: str = Field(
        ...,
        description="New string which will replace the old one"
    )

class AppendToFileSchema(BaseModel):
    path: str = Field(
        ...,
        description="File's absolute path"
    )
    new_content: str= Field(
        ...,
        description="New content to be appended to the file"
    )


class RunCommandSchema(BaseModel):
    command: str = Field(
        ...,
        description="Bash command"
    )


class PlannerOutput(BaseModel):
    steps: list[str] = Field(
        ...,
        description="Step-by-step plan to complete user's request"
    )

class RouterOutput(BaseModel):
    reason: str = Field(
        ...,
        description="Model's chain of thoughts"
    )
    next: Literal["coder","reviewer","next_step","end"] = Field(
        ...,
        description="Which path to go in the graph"
    )