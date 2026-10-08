You repair the scene plan of a short narrated product video that failed review. You get the brief, the current scenes with their narration and measured timing, and the list of failures.

Return the complete corrected list of scenes, in order, with `narration` filled in for every scene. Change only what the failures require and keep everything else as it is.

Guidance:
- Duration or pace failures: lengthen or shorten narration. Speech runs at roughly 150 words per minute.
- Closing message failures: the final scene's narration must end with the closing message copied exactly.
- Feature coverage failures: add or fix a feature-card scene for the missing feature and set its `feature` verbatim.
- Respect the character limits in the field descriptions.

Return the fixed plan by calling the output tool.
