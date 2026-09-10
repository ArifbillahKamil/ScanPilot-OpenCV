"""Conservative continuation of four visible paper edges beyond the photo frame."""
import cv2
import numpy as np


def partial_page_quad(image):
    h,w = image.shape[:2]
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = np.uint8((hsv[:,:,1] < 45) & (hsv[:,:,2] > 95))*255
    kernel = max(5, int(min(h,w)*.012)|1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((kernel,kernel),np.uint8))
    contours,_ = cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    contour = max(contours,key=cv2.contourArea)
    if not .3*h*w < cv2.contourArea(contour) < .97*h*w:
        return None
    poly = cv2.approxPolyDP(contour,.002*cv2.arcLength(contour,True),True).reshape(-1,2).astype(float)
    center = poly.mean(axis=0)
    edges = {}
    for a,b in zip(poly,np.roll(poly,-1,axis=0)):
        # Photo-frame edges are clipping boundaries, never evidence of paper edges.
        if any(abs(a[k]-v)<3 and abs(b[k]-v)<3 for k,v in [(0,0),(0,w-1),(1,0),(1,h-1)]):
            continue
        d = b-a
        length = np.linalg.norm(d)
        midpoint = (a+b)/2
        if abs(d[0]) > 2*abs(d[1]) and length > w*.3:
            side = 'top' if midpoint[1]<center[1] else 'bottom'
        elif abs(d[1]) > 2*abs(d[0]) and length > h*.3:
            side = 'left' if midpoint[0]<center[0] else 'right'
        else:
            continue
        if side not in edges or length > edges[side][0]:
            edges[side] = (length,a,b)
    if len(edges)!=4:
        return None
    def crossing(first,second):
        _,a,b=edges[first]; _,c,d=edges[second]
        line1=np.cross([*a,1],[*b,1]); line2=np.cross([*c,1],[*d,1])
        point=np.cross(line1,line2)
        return point[:2]/point[2] if abs(point[2])>1e-6 else np.array([np.nan,np.nan])
    points=np.float32([crossing('top','left'),crossing('top','right'),crossing('bottom','right'),crossing('bottom','left')])
    if not np.isfinite(points).all() or not cv2.isContourConvex(points):
        return None
    if np.any(points < [-w*.2,-h*.2]) or np.any(points > [w*1.2,h*1.2]):
        return None
    if not .3*h*w < cv2.contourArea(points) < 1.3*h*w:
        return None
    # Only a small part may lie outside the photograph.
    frame=np.float32([[0,0],[w-1,0],[w-1,h-1],[0,h-1]])
    visible,_=cv2.intersectConvexConvex(points,frame)
    if visible/cv2.contourArea(points) < .9:
        return None
    return points
