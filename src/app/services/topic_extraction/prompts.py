"""
Prompts for LLM-based topic extraction and normalization/dedup.

Maps to doc/pdf-extraction.md Stages 10-11 (extraction) and 16-17
(normalization, deduplication).
"""

from src.app.schemas.pdf import PdfChunk

EXTRACTION_SYSTEM_PROMPT = (
    "You are extracting learning topics from one section of an educational or "
    "interview-preparation document, for a study app. Identify the meaningful "
    "concepts, technologies, principles, techniques, APIs, algorithms, "
    "frameworks, architectural ideas, and interview topics a learner should "
    "study from this text.\n\n"
    "Do NOT turn every paragraph or sentence into a topic. Prefer a smaller "
    "set of genuinely useful learning topics over exhaustive extraction.\n\n"
    "Ignore page numbers, navigation text, copyright notices, author bios, "
    "advertisements, and generic filler that carries no learning content. "
    "If the text has no real topics (e.g. it's a cover page or a table of "
    "contents), return an empty list.\n\n"
    "Respond with ONLY a JSON object of this exact shape:\n"
    '{"topics": ["<topic name>", "<topic name>", ...]}\n\n'
    'Each topic name should be short and learner-facing (e.g. "React Hooks", '
    "not a full sentence). Do not include any text outside the JSON object."
)


def build_extraction_user_prompt(chunk: PdfChunk) -> str:
    """Builds the human message for one chunk, including its heading if known."""
    heading = f'Section: "{chunk.heading}"\n\n' if chunk.heading else ""
    return f"{heading}{chunk.text}"


NORMALIZATION_SYSTEM_PROMPT = (
    "You are given a numbered list of candidate learning topics, extracted "
    "independently from different parts of the same document. Some entries "
    "are just different phrasings of the exact same concept (e.g. "
    '"React Hooks", "Hooks in React", "React.js Hooks" all mean one topic).\n\n'
    "Group entries that refer to the exact same concept together, and choose "
    "the clearest, most natural learner-facing name for each group. Do NOT "
    "merge topics that are merely related but conceptually distinct -- for "
    'example "React State" and "Redux" are related but must stay separate '
    "groups.\n\n"
    "Every input index must end up in exactly one group, including topics "
    "that have no duplicates (those form a group of one).\n\n"
    "Respond with ONLY a JSON object of this exact shape:\n"
    '{"groups": [{"name": "<canonical name>", "indices": [<index>, ...]}, ...]}\n\n'
    "Do not include any text outside the JSON object."
)


def build_normalization_user_prompt(topic_names: list) -> str:
    """Builds the human message: a numbered list of raw extracted topic names."""
    return "\n".join(f"{i}. {name}" for i, name in enumerate(topic_names))
