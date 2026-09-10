"""Local OCR. Scores are model scores, never proof of correctness."""
import threading

import cv2
import numpy as np

_engine = None
_lock = threading.Lock()


def spaced_reading(engine, image, polygon, original):
    """Accept word spacing only when independent crops preserve every character."""
    if any(c.isdigit() for c in original):
        return original
    p=np.float32(polygon)
    width=int(max(np.linalg.norm(p[1]-p[0]),np.linalg.norm(p[2]-p[3])))
    height=int(max(np.linalg.norm(p[3]-p[0]),np.linalg.norm(p[2]-p[1])))
    if width < height*4 or height < 8:
        return original
    matrix=cv2.getPerspectiveTransform(p,np.float32([[0,0],[width-1,0],[width-1,height-1],[0,height-1]]))
    crop=cv2.warpPerspective(image,matrix,(width,height))
    gray=cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY)
    _,ink=cv2.threshold(gray,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
    occupied=np.any(ink[2:-2]>0,axis=0)
    runs=[]; start=None
    for x,value in enumerate(np.r_[~occupied,False]):
        if value and start is None: start=x
        if not value and start is not None:
            if x-start >= max(3,height*.22): runs.append((start,x))
            start=None
    cuts=[0]+[int((a+b)/2) for a,b in runs if a>1 and b<width-1]+[width]
    if len(cuts)<3 or len(cuts)>30:
        return original
    words=[crop[:,a:b] for a,b in zip(cuts,cuts[1:])]
    if any(word.shape[1]<height*.4 for word in words):
        return original
    readings,_=engine.text_rec(words)
    if any(score<.85 for _,score in readings):
        return original
    candidate=' '.join(text.strip() for text,_ in readings)
    return candidate if ''.join(candidate.split())==''.join(original.split()) else original


def read(image, source_mask=None):
    global _engine
    from rapidocr_onnxruntime import RapidOCR
    with _lock:
        if _engine is None:
            _engine = RapidOCR(intra_op_num_threads=2, inter_op_num_threads=1,
                               text_score=0.35, det_limit_side_len=1280)
        # Page rotation is handled geometrically. Avoid flipping isolated short words.
        result, _ = _engine(image, use_cls=False)
        originals = [row[1] for row in result or []]
        for row in result or []:
            row[1] = spaced_reading(_engine,image,row[0],row[1])
    lines = []
    for index,(box, text, score) in enumerate(result or []):
        points = np.array(box, dtype=np.int32)
        x, y, w, h = cv2.boundingRect(points)
        source = 'photo-1'
        if source_mask is not None:
            area = source_mask[max(y, 0):y+h, max(x, 0):x+w]
            fraction = float(np.mean(area > 0)) if area.size else 0
            source = 'photo-2' if fraction > .98 else 'mixed' if fraction > 0 else 'photo-1'
        lines.append({'id': f'line-{len(lines)+1}', 'text': text,
                      'score': round(float(score), 3), 'box': [x, y, w, h], 'polygon': np.asarray(box).tolist(),
                      'raw_text': originals[index], 'source': source, 'uncertain': score < .85})
    return lines


def text_of(lines):
    return '\n'.join(line['text'] for line in lines)
