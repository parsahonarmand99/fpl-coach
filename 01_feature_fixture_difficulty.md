# Ticket 1: Integrate Fixture Difficulty into AI Score

## Description

To enhance the strategic quality of the AI's suggestions, this ticket proposes modifying the core `ai_score` calculation to factor in the difficulty of a player's upcoming fixtures. Currently, the AI primarily relies on historical data (total points, form, etc.). By adding a forward-looking component, the AI will be able to identify players with favorable upcoming matches, making its transfer and captaincy advice much more timely and intelligent, similar to how experienced FPL managers plan their teams.

## Affected Files

-   `backend/squad_builder.py`: The `SquadAnalyzer` class, specifically the `_calculate_ai_score` method and any methods that use it (`suggest_transfers`, `suggest_double_transfers`, `suggest_captain`).
-   `backend/main.py`: May require updates to the `Player` data model if new fixture data is fetched and stored.

## Related Context

The current `ai_score` is a good baseline but lacks a crucial FPL strategy element: planning for future games. A player with a high historical score might be entering a run of very difficult matches, making them a poor short-term asset. Conversely, a player in decent form with a string of easy fixtures is a prime target for transfer. This change will directly address that gap.

## Action Required

### Backend

1.  **Obtain Fixture Difficulty Data:**
    *   The `Player` data objects need to be augmented with a list of their next 3-5 upcoming opponents and the difficulty of each match. This data will need to be fetched from the FPL API or another reliable source during the initial data load in `main.py`.

2.  **Modify `_calculate_ai_score`:**
    *   In `backend/squad_builder.py`, update the `_calculate_ai_score` method within the `SquadAnalyzer` class.
    *   Develop a scoring modifier based on the upcoming fixtures. For example:
        *   Create a mapping for difficulty ratings (e.g., 1-2 = easy, 3 = medium, 4-5 = hard).
        *   Define weights: an easy fixture might add `+10` to the score, a medium fixture `0`, and a hard fixture `-10`.
        *   The final `ai_score` will be a combination of the existing score and this new fixture difficulty modifier.

3.  **Ensure Integration:**
    *   Confirm that the updated `ai_score` is seamlessly used by all suggestion methods (`suggest_transfers`, `suggest_double_transfers`, `suggest_captain`) without further changes, as they all rely on the core score calculation. 