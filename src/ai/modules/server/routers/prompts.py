import json
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Request

import ai.functions as func
from ai.modules.server.schemas import PromptCreateRequest, PromptUpdateRequest
from ai.modules.server.services.prompt_manager import (
    InvalidPathError as PromptInvalidPathError,
    PromptNotFoundError,
    PromptAccessError,
)

router = APIRouter()

MODEL_CONFIG_DIR = Path(func.get_root_directory()) / "models"

@router.get("/api/v1/prompts")
async def get_prompts(request: Request, prompt_folder: Optional[str] = None):
    """
    Retrieve a list of saved prompts. Optionally filter by a sub-folder.
    """
    prompt_manager = request.app.state.prompt_manager
    if prompt_manager is None:
        raise HTTPException(
            status_code=500, detail="Prompt manager not configured."
        )
    try:
        prompts = prompt_manager.list_prompts(prompt_folder)
        return {"prompts": prompts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load prompts: {e}")

@router.get("/api/v1/prompts/{prompt_path:path}")
async def get_prompt_content(request: Request, prompt_path: str):
    """
    Get the content of a specific prompt file.
    """
    prompt_manager = request.app.state.prompt_manager
    if prompt_manager is None:
        raise HTTPException(
            status_code=500, detail="Prompt manager not configured."
        )
    try:
        return prompt_manager.read_prompt(prompt_path)
    except PromptNotFoundError:
        raise HTTPException(status_code=404, detail="Prompt not found")
    except PromptInvalidPathError:
        raise HTTPException(status_code=400, detail="Invalid prompt path")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load prompt: {e}")

@router.get("/api/v1/model-configs")
async def get_model_configs(request: Request):
    """
    Retrieve all model config JSON objects from the models directory.
    """
    if not MODEL_CONFIG_DIR.exists() or not MODEL_CONFIG_DIR.is_dir():
        raise HTTPException(
            status_code=500,
            detail=f"Model config directory not found: {MODEL_CONFIG_DIR}",
        )

    model_configs = []
    try:
        for model_file in sorted(MODEL_CONFIG_DIR.rglob("*.json")):
            with model_file.open("r", encoding="utf-8") as f:
                model = json.load(f)
                model_configs.append(
                    {
                        "model_name": model.get("name", model_file.stem),
                        "model_file": str(model_file.relative_to(func.get_root_directory() + '/models/')),
                    }
                )
        return model_configs
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid JSON in model config {model_file.name}: {e}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load model configs: {e}",
        )

@router.post("/api/v1/prompts")
async def create_prompt(request: Request, payload: PromptCreateRequest):
    """
    Create a new prompt file.
    """
    prompt_manager = request.app.state.prompt_manager
    if prompt_manager is None:
        raise HTTPException(
            status_code=500, detail="Prompt manager not configured."
        )
    try:
        result = prompt_manager.create_prompt(
            payload.prompt_path, payload.content
        )
        return result
    except PromptInvalidPathError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PromptAccessError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create prompt: {e}")

@router.put("/api/v1/prompts/{prompt_path:path}")
async def update_prompt_content(
    request: Request, prompt_path: str, payload: PromptUpdateRequest
):
    """
    Update/overwrite an existing prompt file.
    """
    prompt_manager = request.app.state.prompt_manager
    if prompt_manager is None:
        raise HTTPException(
            status_code=500, detail="Prompt manager not configured."
        )
    try:
        result = prompt_manager.update_prompt(prompt_path, payload.content)
        return result
    except PromptNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PromptInvalidPathError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PromptAccessError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update prompt: {e}")

@router.delete("/api/v1/prompts/{prompt_path:path}")
async def delete_prompt(request: Request, prompt_path: str):
    """
    Delete a specific prompt file.
    """
    prompt_manager = request.app.state.prompt_manager
    if prompt_manager is None:
        raise HTTPException(
            status_code=500, detail="Prompt manager not configured."
        )
    try:
        prompt_manager.delete_prompt(prompt_path)
        return {"status": "success", "message": f"Prompt {prompt_path} deleted."}
    except PromptNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PromptInvalidPathError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PromptAccessError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete prompt: {e}"
        )