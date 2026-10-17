from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Kokoro voices with a character of their own, for a narrator who is part of the story. The best-graded of Kokoro's
# English voices; the name's first letter is the accent (a: US, b: UK), the second the gender.
VoiceName = Literal[
    "af_heart", "af_bella", "af_nicole", "am_michael", "am_fenrir", "am_puck",
    "bf_emma", "bf_isabella", "bm_george", "bm_fable",
]  # fmt: skip
CHARACTERS: dict[str, str] = {
    "af_heart": "US female, warm (the default)",
    "af_bella": "US female, bright and lively",
    "af_nicole": "US female, soft and close",
    "am_michael": "US male, steady (the default)",
    "am_fenrir": "US male, deep",
    "am_puck": "US male, playful",
    "bf_emma": "UK female, clear (the default)",
    "bf_isabella": "UK female, poised",
    "bm_george": "UK male, classic (the default)",
    "bm_fable": "UK male, a storyteller",
}


class Voice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    gender: Literal["female", "male"] = "female"
    accent: Literal["us", "uk"] = "us"
    speed: float = Field(1.0, ge=0.8, le=1.2)
    name: VoiceName | None = Field(
        None, description="A Kokoro voice with a character of its own; it sets the gender and accent"
    )

    def record(self) -> dict:
        """What a scene was voiced with, to tell later whether it must be voiced again. An unset name is left out,
        so runs recorded before named voices existed still match."""
        return self.model_dump(exclude_none=True)

    @model_validator(mode="after")
    def named(self) -> "Voice":
        if self.name:
            self.accent = "us" if self.name[0] == "a" else "uk"
            self.gender = "female" if self.name[1] == "f" else "male"
        return self
