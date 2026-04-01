# MISSION: Trello-Lite Architect

**OBJECTIVE:** Create a "complete but simple" Trello-like application for personal organization.

**APP SPECIFICATIONS:**
- **Hierarchy:** Projects > Boards > Lists > Cards.
- **Tech Stack:** React (Single File), Tailwind CSS (Modern/Minimalist).
- **Persistence:** LocalStorage (Save data in-browser automatically).
- **Interactions:** Use "Action Buttons" (Move Left/Right, Up/Down, Edit, Delete) for card management to ensure stability.
- **UI:** A sidebar for "Projects" and a main horizontal-scroll area for "Boards/Lists".

**STRATEGIC PHASES:**
1. **MAPPING:** Delegate to the **SECRETARY** to check for any existing `@ROOT/src/trello` directory or relevant config files.
2. **ARCHITECTING:** The **MASTER** must define the JSON data structure for the nested hierarchy (Projects[Boards[Lists[Cards]]]) and store it in `notes`.
3. **IMPLEMENTATION:** Delegate to the **ENGINEER** to create `@ROOT/src/App.tsx`.
   - **Constraint:** The code must be 100% functional with no placeholders.
   - **Requirement:** Include a "Seed Data" function so the app isn't empty on first load.

**INITIALIZATION COMMANDS:**
- **Phase:** Set `manifest.phase` to `MAPPING`.
- **Target:** **SECRETARY**.
- **Task:** "Scan the root directory for any existing React project structure or workspace folders."
- **Constraint:** Delegate ask the **ENGINEER** to do write actions until the Data Structure is architected in your `notes`.
- **Strict Output:** Respond only with the mandatory JSON object. No Markdown wrappers.