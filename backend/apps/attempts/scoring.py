from decimal import Decimal


def _to_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _normalized(value):
    if value is None:
        return ""
    return str(value).strip().lower()


def score_single_choice(answer_payload: dict, question_payload: dict, max_points: Decimal):
    selected = answer_payload.get("selected")
    correct = question_payload.get("correct_option")
    is_correct = selected == correct
    return is_correct, max_points if is_correct else Decimal("0")


def score_multiple_choice(answer_payload: dict, question_payload: dict, max_points: Decimal):
    selected = {str(item) for item in answer_payload.get("selected", [])}
    correct = {str(item) for item in question_payload.get("correct_options", [])}
    is_correct = selected == correct and len(correct) > 0
    return is_correct, max_points if is_correct else Decimal("0")


def score_text_answer(answer_payload: dict, question_payload: dict, max_points: Decimal):
    answer = _normalized(answer_payload.get("value"))
    options = question_payload.get("correct_answers") or []
    normalized_options = {_normalized(opt) for opt in options}
    is_correct = answer in normalized_options and answer != ""
    return is_correct, max_points if is_correct else Decimal("0")


def score_question(question_type: str, answer_payload: dict, question_payload: dict, max_points):
    max_points = _to_decimal(max_points)

    if question_type == "single":
        return score_single_choice(answer_payload, question_payload, max_points)
    if question_type == "multiple":
        return score_multiple_choice(answer_payload, question_payload, max_points)
    if question_type == "text":
        return score_text_answer(answer_payload, question_payload, max_points)
    if question_type == "extended":
        return None, Decimal("0")

    return None, Decimal("0")
