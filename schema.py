from pydantic import BaseModel, Field


class ProjectIdea(BaseModel):
    name: str = Field(..., description="Project name")
    problem_statement: str = Field(..., description="1–2 sentences describing the problem")
    why_it_fits: list[str] = Field(..., description="Short bullets per tech in the stack")
    real_world_value: str = Field(..., description="One sentence on real-world value")
    implementation_plan: list[str] = Field(..., description="3–5 high-level implementation steps")


class IdeasResponse(BaseModel):
    ideas: list[ProjectIdea] = Field(..., min_length=3, max_length=3)
