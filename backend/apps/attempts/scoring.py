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
    if correct is None:
        correct = question_payload.get("correct_option_id")
    is_correct = selected == correct
    return is_correct, max_points if is_correct else Decimal("0")


def score_multiple_choice(answer_payload: dict, question_payload: dict, max_points: Decimal):
    selected = {str(item) for item in answer_payload.get("selected", [])}
    correct = {str(item) for item in question_payload.get("correct_options", [])}
    is_correct = selected == correct and len(correct) > 0
    return is_correct, max_points if is_correct else Decimal("0")


def score_short_answer(answer_payload: dict, question_payload: dict, max_points: Decimal):
    answer = _normalized(answer_payload.get("value"))
    options = question_payload.get("correct_answers")
    if options is None:
        options = question_payload.get("acceptable_answers")
    if options is None:
        options = [question_payload.get("correct_answer", "")]
    normalized_options = {_normalized(opt) for opt in options}
    is_correct = answer in normalized_options and answer != ""
    return is_correct, max_points if is_correct else Decimal("0")


def score_matching(answer_payload: dict, question_payload: dict, max_points: Decimal):
    submitted = answer_payload.get("pairs", {}) or {}
    correct_pairs = question_payload.get("pairs", {}) or {}
    if not correct_pairs:
        return False, Decimal("0")

    errors = 0
    for left_key, right_value in correct_pairs.items():
        if submitted.get(left_key) != right_value:
            errors += 1

    if errors == 0:
        return True, max_points
    if errors <= 2:
        return False, (max_points * Decimal("0.5"))
    return False, Decimal("0")


def score_ordering(answer_payload: dict, question_payload: dict, max_points: Decimal):
    submitted = answer_payload.get("order", []) or []
    correct_order = question_payload.get("correct_order", []) or []
    if not correct_order:
        return False, Decimal("0")

    # Ошибка — элемент не на своей позиции
    compared_len = min(len(submitted), len(correct_order))
    errors = 0
    for idx in range(compared_len):
        if submitted[idx] != correct_order[idx]:
            errors += 1
    errors += abs(len(submitted) - len(correct_order))

    if errors == 0:
        return True, max_points
    if errors <= 2:
        return False, (max_points * Decimal("0.5"))
    return False, Decimal("0")


def score_cloze(answer_payload: dict, question_payload: dict, max_points: Decimal):
    submitted = answer_payload.get("blanks", {}) or {}
    correct = question_payload.get("blanks", {}) or {}
    mode = question_payload.get("scoring", "per_blank")
    if not correct:
        return False, Decimal("0")

    correct_count = 0
    for key, expected in correct.items():
        if _normalized(submitted.get(key)) == _normalized(expected):
            correct_count += 1

    if mode == "all_or_nothing":
        is_correct = correct_count == len(correct)
        return is_correct, max_points if is_correct else Decimal("0")

    per_blank = max_points / Decimal(str(len(correct)))
    points = per_blank * Decimal(str(correct_count))
    return correct_count == len(correct), points


def score_question(question_type: str, answer_payload: dict, question_payload: dict, max_points):
    max_points = _to_decimal(max_points)

    if question_type == "single":
        return score_single_choice(answer_payload, question_payload, max_points)
    if question_type == "multiple":
        return score_multiple_choice(answer_payload, question_payload, max_points)
    if question_type == "text":
        return score_short_answer(answer_payload, question_payload, max_points)
    if question_type == "extended":
        return None, Decimal("0")

    # Старая несовместимая логика типов: по умолчанию не начисляем очки.
    return None, Decimal("0")
