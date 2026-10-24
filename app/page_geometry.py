"""Conservative continuation of four visible paper edges beyond the photo frame."""
import cv2
import numpy as np

def neutral_page_quad(image):
    """Find a neutral sheet by colour separation; reject frame/background contours."""
    h,w=image.shape[:2]
    hsv=cv2.cvtColor(image,cv2.COLOR_BGR2HSV)
    lab=cv2.cvtColor(image,cv2.COLOR_BGR2LAB)
    candidates=[]
    for saturation in (0,20,35,55):
        for brightness in ((128,) if saturation==0 else (120,155,185,210)):
            selection=(lab[:,:,2]<brightness)&(hsv[:,:,1]<55)&(hsv[:,:,2]>95) if saturation==0 else (hsv[:,:,1]<saturation)&(hsv[:,:,2]>brightness)
            mask=np.uint8(selection)*255
            mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((9,9),np.uint8))
            contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                area=cv2.contourArea(contour)
                if not .23*h*w<area<.9*h*w:continue
                poly=cv2.approxPolyDP(contour,.02*cv2.arcLength(contour,True),True)
                if len(poly)!=4 or not cv2.isContourConvex(poly):continue
                points=poly.reshape(4,2).astype(np.float32)
                if np.any(points<3) or np.any(points[:,0]>w-4) or np.any(points[:,1]>h-4):continue
                if area/cv2.contourArea(points)<.96:continue
                center=points.mean(axis=0)
                points=points[np.argsort(np.arctan2(points[:,1]-center[1],points[:,0]-center[0]))]
                points=np.roll(points,-np.argmin(points.sum(axis=1)),axis=0)
                # A real boundary needs consistent colour contrast along all four sides.
                contrasts=[]
                for a,b in zip(points,np.roll(points,-1,axis=0)):
                    mid=a[None,:]+np.linspace(.15,.85,25)[:,None]*(b-a)
                    direction=center-mid;direction/=np.linalg.norm(direction,axis=1)[:,None]
                    inside=np.rint(mid+direction*8).astype(int);outside=np.rint(mid-direction*8).astype(int)
                    inside[:,0]=np.clip(inside[:,0],0,w-1);inside[:,1]=np.clip(inside[:,1],0,h-1)
                    outside[:,0]=np.clip(outside[:,0],0,w-1);outside[:,1]=np.clip(outside[:,1],0,h-1)
                    delta=image[inside[:,1],inside[:,0]].astype(float)-image[outside[:,1],outside[:,0]].astype(float)
                    contrasts.append(np.median(np.linalg.norm(delta,axis=1)))
                if min(contrasts)<12:continue
                candidates.append((area,points))
    return max(candidates,key=lambda item:item[0])[1] if candidates else None
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
