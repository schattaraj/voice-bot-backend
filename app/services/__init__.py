"""Business logic and use-case orchestration.

Services coordinate repositories/, prompts/, voice/, and evaluation/ to
fulfill a use case. They know nothing about HTTP — that's api/'s job — and
never talk to the database directly — that's repositories/'s job.
"""
