from typing import List, Dict

class SeedQuestion:
    def __init__(self, id: str, text: str, expected_signals: List[str]):
        self.id = id
        self.text = text
        self.expected_signals = expected_signals

SEED_QUESTIONS: List[SeedQuestion] = [
    SeedQuestion(
        id="q1",
        text="Why do users repeatedly buy from the same categories?",
        expected_signals=["habit", "convenience", "quality", "trust"]
    ),
    SeedQuestion(
        id="q2",
        text="What prevents users from exploring new categories?",
        expected_signals=["price", "quality doubt", "lack of info", "trust"]
    ),
    SeedQuestion(
        id="q3",
        text="How do users discover products today?",
        expected_signals=["search", "ad", "word-of-mouth", "social media", "app home feed"]
    ),
    SeedQuestion(
        id="q4",
        text="What role do habits play in shopping behavior?",
        expected_signals=["repeat-purchase", "routine", "loyalty"]
    ),
    SeedQuestion(
        id="q5",
        text="What information do users need before trying a new category?",
        expected_signals=["reviews", "ingredients", "brand", "return policy"]
    ),
    SeedQuestion(
        id="q6",
        text="What frustrations emerge repeatedly?",
        expected_signals=["delivery", "quality", "support", "refund", "app crash"]
    ),
    SeedQuestion(
        id="q7",
        text="Which user segments are more likely to experiment?",
        expected_signals=["student", "young professional", "tech-savvy"]
    ),
    SeedQuestion(
        id="q8",
        text="What unmet needs emerge consistently across discussions?",
        expected_signals=["unmet_need", "wish", "feature request", "complaint"]
    )
]
