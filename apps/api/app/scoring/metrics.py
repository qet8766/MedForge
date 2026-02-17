from __future__ import annotations

from .types import Box

_MAP_IOU_THRESHOLDS = [0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75]


def _compute_accuracy(labels: dict[str, int], preds: dict[str, int]) -> float:
    keys = set(labels.keys())
    if keys != set(preds.keys()):
        raise ValueError("Submission IDs do not match expected evaluation IDs.")

    total = len(keys)
    correct = sum(1 for key in keys if labels[key] == preds[key])
    return correct / total if total else 0.0


def _iou(a: Box, b: Box) -> float:
    x1 = max(a.x, b.x)
    y1 = max(a.y, b.y)
    x2 = min(a.x + a.w, b.x + b.w)
    y2 = min(a.y + a.h, b.y + b.h)

    inter_w = max(0.0, x2 - x1)
    inter_h = max(0.0, y2 - y1)
    inter_area = inter_w * inter_h

    area_a = a.w * a.h
    area_b = b.w * b.h
    union_area = area_a + area_b - inter_area

    if union_area <= 0.0:
        return 0.0
    return inter_area / union_area


def _score_single_image(
    gt_boxes: list[Box],
    pred_boxes: list[Box],
    iou_thresholds: list[float],
) -> float:
    # Negative image (no GT boxes) -> always 1.0 per Kaggle RSNA rules.
    if not gt_boxes:
        return 1.0

    sorted_preds = sorted(pred_boxes, key=lambda b: b.confidence, reverse=True)

    threshold_precisions: list[float] = []
    for threshold in iou_thresholds:
        matched_gt: set[int] = set()
        tp = 0
        fp = 0

        for pred in sorted_preds:
            best_iou = 0.0
            best_gt_idx = -1
            for gt_idx, gt in enumerate(gt_boxes):
                if gt_idx in matched_gt:
                    continue
                current_iou = _iou(pred, gt)
                if current_iou > best_iou:
                    best_iou = current_iou
                    best_gt_idx = gt_idx

            if best_iou >= threshold and best_gt_idx >= 0:
                tp += 1
                matched_gt.add(best_gt_idx)
            else:
                fp += 1

        fn = len(gt_boxes) - tp
        precision = tp / (tp + fp + fn) if (tp + fp + fn) > 0 else 0.0
        threshold_precisions.append(precision)

    return sum(threshold_precisions) / len(threshold_precisions)


def _compute_map_iou(
    labels: dict[str, list[Box]],
    preds: dict[str, list[Box]],
) -> float:
    if set(labels.keys()) != set(preds.keys()):
        raise ValueError("Submission patient IDs do not match expected evaluation IDs.")

    image_scores: list[float] = []
    for patient_id in labels:
        gt_boxes = labels[patient_id]
        pred_boxes = preds[patient_id]
        image_scores.append(_score_single_image(gt_boxes, pred_boxes, _MAP_IOU_THRESHOLDS))

    return sum(image_scores) / len(image_scores) if image_scores else 0.0


def _compute_mean_iou(labels: dict[str, set[int]], preds: dict[str, set[int]]) -> float:
    if set(labels.keys()) != set(preds.keys()):
        raise ValueError("Submission IDs do not match expected evaluation IDs.")

    image_scores: list[float] = []
    for image_id, label_pixels in labels.items():
        pred_pixels = preds[image_id]
        intersection = len(label_pixels & pred_pixels)
        union = len(label_pixels | pred_pixels)
        if union == 0:
            image_scores.append(1.0)
            continue
        image_scores.append(intersection / union)

    return sum(image_scores) / len(image_scores) if image_scores else 0.0
