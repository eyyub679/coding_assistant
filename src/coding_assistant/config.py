from pydantic import BaseModel

class Config(BaseModel):
    model: str = "gemini-3.5-flash-lite"
    max_retries: int = 10
    max_error_count: int = 3
    timeout: int = 30