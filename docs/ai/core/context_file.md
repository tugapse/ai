## Module Purpose
This file defines the `ContextFile` class, which is responsible for representing and loading the content of a specified file into memory, with an option to handle file not found errors.

## Interface & Exports
*   `ContextFile` (Class): Represents a file and provides methods to load its content.
*   `THROW_ERROR_ON_LOAD_CONTEXT_FILE_NOT_EXIST` (Variable): A boolean constant controlling the default error handling behavior for `ContextFile`.

## Internal Logic
The `ContextFile` class initializes with a `filename` and a flag `throw_error_on_load`. The `load` method checks if the `filename` exists using `pathlib.Path.exists()`. If the file does not exist, it logs an error and, if `throw_error_on_load` is `True`, raises a `FileNotFoundError`. Otherwise, it reads the file's content into the `content` attribute and sets the `loaded` flag to `True`.

## Dependencies
*   `logging`
*   `os.path`
*   `pathlib`

## Constants & Environment
*   `THROW_ERROR_ON_LOAD_CONTEXT_FILE_NOT_EXIST`: `False`