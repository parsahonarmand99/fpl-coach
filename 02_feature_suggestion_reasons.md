# Ticket 2: Provide Reasons for AI Suggestions

## Description

To improve user trust and provide a better user experience, the AI should explain *why* it's making a particular transfer suggestion. Instead of just showing a quantitative score gain, the system will generate a human-readable string that provides qualitative context for the decision (e.g., mentioning form, fixture difficulty, etc.).

## Affected Files

-   **Backend:** `backend/squad_builder.py`, `backend/main.py`
-   **Frontend:** `frontend/src/components/SquadAnalysisPage.jsx`, `frontend/src/components/SquadAnalysisPage.css`

## Related Context

Currently, the UI displays suggestions like "Salah -> Son (+5.2 score)". This is useful but opaque. Adding a simple sentence of reasoning will make the tool feel more like an intelligent coach and less like a black box, helping users understand the logic behind the suggestions.

## Action Required

### Backend

1.  **Generate Reason String:**
    *   In `backend/squad_builder.py`, modify the `suggest_transfers` and `suggest_double_transfers` methods.
    *   For each suggested transfer, generate a dynamic `reason` string. This string should be concise and informative.
    *   *Example Reason:* "Suggesting Son due to excellent recent form and favorable upcoming fixtures, while Salah faces a tough run of matches."

2.  **Update API Response:**
    *   In `backend/main.py`, update the Pydantic models for transfer suggestions (`TransferSuggestion`, `DoubleTransferSuggestion`) to include the new optional `reason: str` field.
    *   Ensure the analysis endpoint (`/api/analyze-squad`) includes this new field in its JSON response.

### Frontend

1.  **Update State Management:**
    *   In `frontend/src/components/SquadAnalysisPage.jsx`, update the component's state to store the `reason` string for each transfer suggestion.

2.  **Render the Reason:**
    *   Modify the JSX for the transfer suggestion cards to display the new `reason` text below the player details. Conditionally render this section only if a reason is provided.

3.  **Style the New Element:**
    *   In `frontend/src/components/SquadAnalysisPage.css`, add styling for the new reason text. It should be visually distinct from the other card elements, perhaps with a smaller font size and a secondary text color to indicate it's explanatory text. 