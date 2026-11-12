from typing import Optional
from fastapi import APIRouter, HTTPException, Request

from ai.modules.server.schemas import PromptCreateRequest, PromptUpdateRequest
from ai.modules.server.services.prompt_manager import (
    InvalidPathError as PromptInvalidPathError,
    PromptNotFoundError,
    PromptAccessError,
)

router = APIRouter()

@router.get("/api/v1/prompts")
async def get_prompts(request: Request, prompt_folder: Optional[str] = None):
    """
    Retrieve a list of saved prompts. Optionally filter by a sub-folder.

    :param request: The FastAPI Request object.
    :param prompt_folder: Optional string specifying a sub-folder to filter prompts by.
    :raises HTTPException: If the prompt manager is not configured (500) or if loading fails (500).
    :return: A dictionary containing the list of prompts.
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

    :param request: The FastAPI Request object.
    :param prompt_path: The full path to the prompt file.
    :raises HTTPException: If the prompt is not found (404), path is invalid (400), or loading fails (500).
    :return: The content of the specified prompt.
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
    List every model config the server knows (user and system models folders, subfolders included).

    :param request: The FastAPI Request object.
    :raises HTTPException: If the server has no BrainHub (500).
    :return: A list of ``{key, model_name, model_type, loadable}``; ``key`` is what a chat request
             sends as ``model``. ``jarvis`` configs and invalid files are listed with ``loadable: false``.
    """
    brain_hub = getattr(request.app.state, "brain_hub", None)
    if brain_hub is None:
        raise HTTPException(status_code=500, detail="Brain hub not configured.")
    return brain_hub.list_model_configs()

@router.post("/api/v1/prompts")
async def create_prompt(request: Request, payload: PromptCreateRequest):
    """
    Create a new prompt file.

    :param request: The FastAPI Request object.
    :param payload: The data containing the prompt path and content to create.
    :raises HTTPException: If the prompt manager is not configured (500), path is invalid (400), access is denied (500), or creation fails (500).
    :return: The result of the prompt creation operation.
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

    :param request: The FastAPI Request object.
    :param prompt_path: The path to the prompt file to update.
    :param payload: The data containing the new content for the prompt.
    :raises HTTPException: If the prompt is not found (404), path is invalid (400), access is denied (500), or update fails (500).
    :return: The result of the prompt update operation.
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

    :param request: The FastAPI Request object.
    :param prompt_path: The path to the prompt file to delete.
    :raises HTTPException: If the prompt is not found (404), path is invalid (400), access is denied (500), or deletion fails (500).
    :return: A success message indicating the prompt was deleted.
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