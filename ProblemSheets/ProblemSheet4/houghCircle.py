import numpy as np
import cv2 as cv
import sys
import sobel
"""
TODO
- Thresholding
"""
def find_threshold_value(arr:np.ndarray):
    arr=arr.flatten(); arr.sort()
    arr=arr[arr!=0]
    if len(arr)==0:
        return 255
    """return arr[int(.97*len(arr))]"""
    T=arr[int(len(arr)/2)]
    before=T
    while True:
        G1=arr[np.where(arr<=T)]
        G2=arr[len(G1):len(arr)]
        if len(G2)==0: # All values are the same
            return T

        m1=np.mean(G1); m2=np.mean(G2)
        T=int(.5*(m1+m2))
        if T==before:
            return T
        before=T

def threshold_boxes(mag:np.ndarray,dir:np.ndarray,width=None,height=None,threshold=1):
    if width is None: width=int(mag.shape[1]/10)
    if height is None: height=int(mag.shape[0]/10)

    x=0; y=0
    while (x<mag.shape[1]-1):
        while (y<mag.shape[0]-1):
            end_x= (x+width) if (x+width)<mag.shape[1] else mag.shape[1]-1
            end_y= (y+height) if (y+height)<mag.shape[0] else mag.shape[0]-1

            box=mag[y:end_y,x:end_x]
            T=find_threshold_value(box)

            T=max(T,threshold)

            for i in range(y,end_y):
                for j in range(x,end_x):
                    if mag[i,j]>=T:
                        mag[i,j]=255
                    else:
                        mag[i,j]=0
                        dir[i,j]=0

            y+=height
        x+=width
        y=0
    return mag,dir

def thresholding(mag:np.ndarray,dir:np.ndarray,threshold=64) -> "np.ndarray,np.ndarray":
    mag_thres=np.zeros(mag.shape); dir_thres=np.zeros(dir.shape)
    for i in range(0,mag.shape[0]):
        for j in range(0,mag.shape[1]):
            if (mag[i,j]>threshold):
                mag_thres[i,j]=255
                dir_thres[i,j]=dir[i,j]
            else:
                dir_thres[i,j]=128
                mag_thres[i,j]=0
    return mag_thres,dir_thres

# magnitude should be thresholded
def hough(mag:np.ndarray,dir:np.ndarray,hough_threshold=100,min_radius=10,max_radius=100,psi_range=None)->[[]]:
    parameter_space=np.zeros((mag.shape[0],mag.shape[1],max_radius+1))
    for i in range(0,mag.shape[0]):
        for j in range(0,mag.shape[1]):
            if mag[i,j]==255:
                # increment all points on line of possible radia
                for r in range(min_radius,max_radius+1):

                    if not psi_range is None: # Consider a range of values around gradient
                        psis=np.linspace(dir[i,j]-abs(psi_range),dir[i,j]+abs(psi_range),num=5)
                        if dir[i,j] not in psis: np.append(psis,dir[i,j])
                    else:
                        psis=[dir[i,j]]

                    for psi in psis:
                        y_c=i-int(r*np.sin(psi))
                        x_c=j+int(r*np.cos(psi))
                        if (y_c>=0) and (y_c<parameter_space.shape[0]) and (x_c>=0) and (x_c<parameter_space.shape[1]):
                            parameter_space[y_c,x_c,r]+=1
                        else:
                            break
                    # Opposite direction (same line)
                    for psi in psis:
                        y_c=i+int(r*np.sin(psi))
                        x_c=j-int(r*np.cos(psi))
                        if (y_c>=0) and (y_c<parameter_space.shape[0]) and (x_c>=0) and (x_c<parameter_space.shape[1]):
                            parameter_space[y_c,x_c,r]+=1
                        else:
                            break

    # implement thresholding
    return parameter_space

# Create image to show intensity from hough space
# hough_space=[[x_c,y_c,r]]
def hough_magnitude(hough_space:np.ndarray, threshold=10):
    img=np.ndarray(hough_space.shape[0:2])
    max=-sys.maxsize; min=sys.maxsize
    for i in range(0,img.shape[0]):
        for j in range(0,img.shape[1]):
            n=np.sum(hough_space[i,j,:]) # sum of votes for all radia
            if (n<threshold): img[i,j]=0
            else: img[i,j]=n

            if (n>max): max=n
            if (n<min): min=n

    print(min,max)
    print(hough_space.max())

    return sobel.normalise(img)

def hough_img(colour_img:np.ndarray,hough_space:np.ndarray,threshold=5,max_centre_proximity=20):
    overlay=np.zeros((colour_img.shape[0],colour_img.shape[1],3))
    centres=np.zeros((colour_img.shape[0],colour_img.shape[1]))

    to_plot=[]

    for i in range(0,hough_space.shape[0]):
        for j in range(0,hough_space.shape[1]):
            for k in range(0,hough_space.shape[2]):
                if (hough_space[i,j,k]>=threshold):
                    to_plot.append([hough_space[i,j,k],i,j,k])
                    centres[i,j]=255
                else:
                    overlay[i,j]=colour_img[i,j]

    to_plot.sort(key=lambda x:x[0], reverse=True)
    plotted=[]
    for (s,i,j,k) in to_plot:
        min_dist=sys.maxsize
        for (i0,j0,k0) in plotted:
            dist=np.sqrt((i-i0)**2+(j-j0)**2)
            min_dist=min(min_dist,dist)

        # Out of range, or no overlap
        if min_dist>max_centre_proximity or (min_dist>k):
            cv.circle(overlay, (j,i), k, (0,0,255), 2)
            plotted.append([i,j,k])
    print("{}/{}".format(len(plotted),len(to_plot)))

    return overlay, centres

# Returns threshold for a point in the hough space to be plotted as a likely circle
def circle_threshold_value(hough_space:np.ndarray,min_n=30,max_n=1000) -> int:
    flat=hough_space.flatten()
    flat=flat[flat!=0]
    flat.sort()
    percentile=int(.995*len(flat))
    if len(flat[percentile:])<=min_n:
        return flat[-min_n]
    elif len(flat[percentile:])>=max_n:
        return flat[-max_n]

    return flat[percentile]

def run(path):
    img=cv.imread(path,0)
    colour_img=cv.imread(path,1)
    dx=np.matrix([[-1,0,1],[-2,0,2],[-1,0,1]])
    dy=np.matrix([[1,2,1],[0,0,0],[-1,-2,-1]])

    img_dx=sobel.convolution(img,dx)
    cv.imwrite("img/dx.png",img_dx)
    print("DX done")
    img_dy=sobel.convolution(img,dy)
    cv.imwrite("img/dy.png",img_dy)
    print("DY done")

    magnitude=sobel.magnitude(img_dx,img_dy)
    print("Magnitude done")
    magnitude=sobel.normalise(magnitude)
    cv.imwrite("img/magnitude.png",magnitude)
    print("Magnitude normalised")

    direction=sobel.direction(img_dx,img_dy)
    direction_normalised=sobel.normalise(direction,min=-np.pi,max=np.pi)
    cv.imwrite("img/direction.png",direction_normalised)
    print("Direction done")

    magnitude_threshold,direction_threshold=threshold_boxes(magnitude,direction_normalised,width=int(magnitude.shape[1]/5),height=int(magnitude.shape[0]/5),threshold=50)
    """
    T=find_threshold_value(img)
    print("T:{}".format(T))
    magnitude_threshold,direction_threshold=thresholding(magnitude,direction_normalised,threshold=T)
    """
    cv.imwrite("img/magnitude_threshold.png",magnitude_threshold)
    cv.imwrite("img/direction_threshold.png",direction_threshold)
    print("Magnitude & Direction Thresholded")

    hough_space=hough(magnitude_threshold,direction,min_radius=30,max_radius=80,psi_range=np.pi/10)
    print("hough done")
    print(hough_space.shape)
    hough_image=hough_magnitude(hough_space,threshold=0)
    print("hough image")
    cv.imwrite("img/hough_img.png",hough_image)

    circle_threshold=circle_threshold_value(hough_space,max_n=200)
    print(circle_threshold)
    overlay,centres=hough_img(colour_img,hough_space,threshold=circle_threshold,max_centre_proximity=30)
    print("overlay done")
    cv.imwrite("img/centres.png",centres)
    cv.imwrite("img/overlay.png",overlay)

run(input())
