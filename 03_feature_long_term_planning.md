# Ticket 3: Implement Long-Term Transfer Planning

## Description

This ticket introduces a sophisticated new feature: suggesting a multi-week transfer plan. Instead of only optimizing for the current gameweek, the AI will identify high-value players who are currently unaffordable and devise a two-step plan to acquire them. This elevates the AI from a simple suggester to a strategic advisor.

## Affected Files

-   **Backend:** `backend/squad_builder.py`, `backend/main.py`
-   **Frontend:** `frontend/src/components/SquadAnalysisPage.jsx`, `frontend/src/components/SquadAnalysisPage.css`

## Related Context

Advanced FPL play often involves planning transfers 2-3 gameweeks in advance. A common strategy is to "downgrade" one player to a cheaper, "enabler" player to free up funds. Those funds are then used in the following week to upgrade another player to a premium, high-scoring asset. This feature will automate that expert-level thought process.

## Action Required

### Backend

1.  **Design `suggest_long_term_plan` Method:**
    *   In `backend/squad_builder.py`, create a new method within `SquadAnalyzer` called `suggest_long_term_plan`.
    *   **Step 1: Identify Target:** The method should first identify the highest-scoring player in the game that the user's squad *cannot* afford.
    *   **Step 2: Find Enabler Transfer:** It then needs to find the optimal "downgrade" transfer for the *current* week. This means identifying a player in the user's squad who can be sold for a cheap, bench-fodder player to free up the exact funds needed for next week's upgrade.
    *   **Step 3: Formulate Plan:** The method should return a structured object containing the two-step plan (e.g., `{ "week_1": { "out": PlayerX, "in": PlayerY }, "week_2": { "out": PlayerZ, "in": TargetPlayer } }`).

2.  **Update API Response:**
    *   In `backend/main.py`, create new Pydantic models to represent the long-term plan.
    *   Update the `/api/analyze-squad` endpoint to call the new method and include the long-term plan in the response, separate from the immediate transfer suggestions.

### Frontend

1.  **Design a New UI Component:**
    *   In `frontend/src/components/SquadAnalysisPage.jsx`, create a new, distinct section for "Long-Term Transfer Plan".
    *   This component should clearly visualize the two-step process, with headings for "This Week" and "Next Week", showing the players being transferred in and out at each stage.

2.  **Add Specific Styling:**
    *   In `frontend/src/components/SquadAnalysisPage.css`, create new CSS rules to style the long-term plan card. It should stand out from the other suggestions, perhaps using a different background color or border to signify its strategic importance. 