# Approach: 

"""

* Both the objects are identified by color so i used HSV instead of BGR as HSV seperates color and intensity which is just there to find the blue object in either
brighter or darker rooms/places.

*Since i need the 2 objects to stay seperate from each other, each objects gets its own mask and contour pipeline. Thus, the blue object and the tennis ball
can never be mistaken for each other.

*The blue objects shape is determined by using area, bounding rectangle and centroid. Even the ball has to undergo a further circularity test.

"""

# Method used to solve the problem statement:

"""

*Gauss blue to reduce sensor noise.

*cv2.inRange for the blue range and the yellow-green range ---> 2 unique masks.

*Morphological operations to clean the masks.(opening removes specks while closing fills in holes)

*cv2.findContours to find the contours of the objects in the masks.

*Blue: keep contours above a minimum area & computes area with contourArea, boundingRect and centre with moments.

*Ball: keep contours above a minimum area & with circularity above the minimum threshold, takes the largest, gets the centre and radius from minEnclosingCircle.

*A simple nearest-centroid tracker gives each object a persistent ID & a short history of centres, drawn as the tracking line.

*If the ball is detected, draw a line from each blue centre to the ball centre and print the offset and distance.

"""
# Other possible methods:

"""

$ Kalman filter on top the tracker can be another nice method to smoothen tracking and predictions when something suddenly blocks the object from the camera's view for a 
moment or two.

$ Open CV trackers like CSRT or KCF are also a good way to track selected objects frame to frame.

$ Adaptive HSV thresholds handles different lighting muhc more efficiently than me typing a different threshold each and every single time when needed.

"""
