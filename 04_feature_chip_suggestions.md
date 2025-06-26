# Ticket 4: Implement AI Chip Usage Suggestions

## Description

This ticket outlines the "ultimate coach" feature: enabling the AI to analyze the user's squad and upcoming fixtures to recommend when to play high-impact FPL chips like the Wildcard, Bench Boost, or Triple Captain. This transforms the application from a transfer suggester into a comprehensive strategic advisor.

## Affected Files

-   **Backend:** `backend/squad_builder.py`, `backend/main.py`
-   **Frontend:** `frontend/src/components/SquadAnalysisPage.jsx`, `frontend/src/components/SquadAnalysisPage.css`

## Related Context

Knowing *when* to use chips is one of the most difficult and important parts of FPL. A well-timed Wildcard or Triple Captain can be game-changing. By adding this intelligence, the app will provide enormous value, helping users make critical decisions at the most opportune moments.

## Action Required

### Backend

1.  **Create `suggest_chip_usage` Method:**
    *   In `backend/squad_builder.py`, implement a new method `suggest_chip_usage` in the `SquadAnalyzer` class. This method will contain the logic for each chip.

2.  **Implement Wildcard Logic:**
    *   The AI should run the `GeneticSquadBuilder` to generate a completely new, optimal 15-player squad from the entire player pool.
    *   It will then calculate the total projected `ai_score` of this new squad and compare it to the user's current squad's projected score over the next several gameweeks.
    *   If the potential score gain is above a significant, predefined threshold, it should recommend playing the Wildcard.

3.  **Implement Bench Boost Logic:**
    *   The AI should analyze the four players on the user's bench.
    *   It should calculate the `ai_score` for each bench player, heavily factoring in their upcoming fixture difficulty.
    *   If all four players have a high projected score (i.e., they are all strong starters with good fixtures), it should recommend activating the Bench Boost.

4.  **Update API Response:**
    *   In `backend/main.py`, update the analysis endpoint to include a new, optional `chip_suggestion` section in the response. This section should contain the name of the recommended chip and potentially the proposed new squad if a Wildcard is suggested.

### Frontend

1.  **Design High-Impact UI Card:**
    *   In `frontend/src/components/SquadAnalysisPage.jsx`, design a new component to display the chip suggestion. This should be a prominent banner or card that immediately draws the user's attention (e.g., "🔥 Wildcard Recommended!").

2.  **Display Proposed Wildcard Squad:**
    *   If a Wildcard is recommended, the UI must be able to display the entire proposed 15-player squad. This will likely require a new, detailed view showing the new pitch and bench.

3.  **Add Styling:**
    *   In `frontend/src/components/SquadAnalysisPage.css`, create styles for the chip suggestion card to make it stand out. Use strong colors, larger fonts, and clear iconography to convey its importance. 