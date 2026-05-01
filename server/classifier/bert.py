"""Issue classifier using fine-tuned DistilBERT.

No taxonomy prompt, no system context. BERT is a classification head:
text in → softmax → IssueType enum out. The model learns the mapping during training.

Training loop:
  1. Collect labeled signals from DuckDB (issue_type, original utterance)
  2. Fine-tune DistilBERT on the labeled set
  3. Export and load here

Inference: ~5ms vs ~400ms Gemini API call. Zero cost per call.
Keeps proprietary data on-prem — no utterances sent to external APIs.
"""

from __future__ import annotations

from pathlib import Path

from server.models.schemas import Classification, IssueType

MODEL_PATH = Path(__file__).parent / "trained_model"

_model = None
_tokenizer = None


def _load_model():
    global _model, _tokenizer
    if _model is not None:
        return

    from transformers import DistilBertForSequenceClassification, DistilBertTokenizer

    _tokenizer = DistilBertTokenizer.from_pretrained(str(MODEL_PATH))
    _model = DistilBertForSequenceClassification.from_pretrained(str(MODEL_PATH))
    _model.eval()


# label index → IssueType enum (must match training label order)
LABEL_MAP: list[IssueType] = [
    IssueType.PAYMENT_FAILED,
    IssueType.ITEM_NOT_DELIVERED,
    IssueType.WRONG_ITEM,
    IssueType.REFUND_DELAYED,
    IssueType.AGENT_NO_SHOW,
    IssueType.UNKNOWN,
]


async def classify(text: str) -> Classification:
    """Classify a customer utterance. Returns IssueType + confidence."""
    import torch

    _load_model()

    inputs = _tokenizer(text, return_tensors="pt", truncation=True, max_length=128)

    with torch.no_grad():
        logits = _model(**inputs).logits

    probs = torch.softmax(logits, dim=-1)
    confidence, label_idx = torch.max(probs, dim=-1)

    return Classification(
        issue_type=LABEL_MAP[label_idx.item()],
        confidence=confidence.item(),
    )
