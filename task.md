### 🛠️ TASK: Synchronize CLI Module Activation & Service Configuration

**PROBLEM:**
The `ModuleRegistry` skips loading hardware (e.g., Voice Engine) even when the `--modules voice` flag is passed. This is caused by:
1. **Reference Mismatch:** `ModuleRegistry` is initialized with a default `ProgramConfig` instance before the actual config is loaded from disk. It never receives the updated config object.
2. **Timing/Race Condition:** `ModuleRegistry.load_all()` runs during the boot phase, but CLI flags are processed in `CliArgs.py` *after* the boot phase. The "enable" signal arrives too late.

**REQUIRED ARCHITECTURAL FIX:**

1.  **Refactor `Program` Lifecycle:**
    * In `Program.__init__`, initialize `self.config = None`.
    * Update `Program.load_config()` to instantiate services (`ModelOrchestrator`, `ModuleRegistry`, `HistoryManager`, `UIOrchestrator`) **ONLY AFTER** the configuration is successfully loaded from disk. This ensures all services share the same `ProgramConfig` object reference.

2.  **Synchronize Boot Sequence in `Program.init_program`:**
    * Move the logic that processes `args.modules` into the start of `init_program`.
    * Iterate through `args.modules` and set `self.config.set(f"{mod.upper()}_ENABLED", True)` **BEFORE** calling `self.modules.load_all()`.

3.  **Update `ModuleRegistry` Logic:**
    * Ensure `load_all()` iterates through a manifest and checks `self.config.get(f"{name.upper()}_ENABLED", False)` at the exact moment of execution.
    * Implement `__getitem__(self, key)` to allow `prog.modules['voice']` access.

4.  **Cleanup `main.py` & `cli_args.py`:**
    * Ensure the execution order is: `load_args()` -> `prog.load_config(args)` -> `prog.init_program(args)` -> `prog.run()`.
    * Remove module-toggling logic from `cli_args.py` as it is now handled upstream in the initialization phase.

**SUCCESS CRITERIA:**
* Running `ai-dev --modules voice` triggers: `ModuleRegistry: Booting 'voice'...`
* Running without the flag triggers: `ModuleRegistry: Skipping 'voice' (Not requested).`
* History is preserved across the 2-stage (Stage 1 Persona -> Stage 2 Logic) process by ensuring the `SessionManager` and `HistoryManager` use the synchronized config object.