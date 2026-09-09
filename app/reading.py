"""Local OCR. Scores are model scores, never proof of correctness."""
import threading

import cv2
import numpy as np

_engine = None
_lock = threading.Lock()


def read(image, source_mask=None):
    global _engine
    from rapidocr_onnxruntime import RapidOCR
    with _lock:
        if _engine is None:
            _engine = RapidOCR(intra_op_num_threads=2, inter_op_num_threads=1,
                               text_score=0.35)
        result, _ = _engine(image)
    lines = []
    for box, text, score in result or []:
        points = np.array(box, dtype=np.int32)
        x, y, w, h = cv2.boundingRect(points)
        source = 'photo-1'
        if source_mask is not None:
            area = source_mask[max(y, 0):y+h, max(x, 0):x+w]
            fraction = float(np.mean(area > 0)) if area.size else 0
            source = 'photo-2' if fraction > .98 else 'mixed' if fraction > 0 else 'photo-1'
        lines.append({'id': f'line-{len(lines)+1}', 'text': text,
                      'score': round(float(score), 3), 'box': [x, y, w, h],
                      'source': source, 'uncertain': score < .85})
    return lines


def text_of(lines):
    return '\n'.join(line['text'] for line in lines)
