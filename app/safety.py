"""Hard safety rules. Skills and prompts cannot override these."""

# This file is the documented non-overridable layer (S3).
# Agent wording belongs in skills/ and prompts/, not in Python strings.

HARD_RULES = (
    "Hard rules (not overridable by skills or prompts): "
    "never send mail or SMS; never invent prices, stock, hours, or names; "
    "draft only and stop for the owner to review."
)

DOC = (
    "Safety rules live in app/safety.py. Editing a skill file cannot turn "
    "sending or invented facts back on."
)
