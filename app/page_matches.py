"""Stateless visual candidates. Recovery independently verifies OCR identity."""
import cv2
from app.recovery import register


def find_matches(images):
    small=[];features=[];sift=cv2.SIFT_create(nfeatures=4500)
    for image in images:
        h,w=image.shape[:2];s=min(1,800/max(h,w))
        image=cv2.resize(image,None,fx=s,fy=s)
        small.append(image);features.append(sift.detectAndCompute(cv2.cvtColor(image,cv2.COLOR_BGR2GRAY),None))
    pairs=[]
    for i in range(len(images)):
        for j in range(i+1,len(images)):
            try:
                _,_,_,evidence=register(small[i],small[j],(features[i],features[j]))
                if evidence['inliers']>=30 and evidence['inlier_ratio']>=.5:
                    pairs.append({'first':i,'second':j,**evidence})
            except ValueError:pass
    return {'pairs':sorted(pairs,key=lambda p:-p['inliers'])}
