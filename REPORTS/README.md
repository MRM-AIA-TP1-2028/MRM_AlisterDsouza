Approach: The task is to detect and track blue objects and a tennis ball simultaneously using the webcam.
Both objects are treated as separate targets, with independent detection techniques based on their colour and shape.
The blue object is tracked using its contour, bounding box and centroid, without assuming its a circle or like a circle.
The tennis ball is detected separately, and its centre, radius and area are calculated using scale estimation.

Methods used to solve this problem: OpenCV's VideoCapture() function is used to access the webcam and process frames simultaneously.
Each frame is converted from BGR to HSV colour space while HSV thresholding and color masks are used to segregate the blue objects and the yellow-green tennis balls.
Contours are taken from the blue colour mask. The largest valid contour is chosen and its bounding rectangle and centroid are computed. The centroid is tracked across consecutive frames using a tracking line.
The tennis ball is identified using colour segmentation and contour-based circularity checks. Its centre and radius are calculated and displayed using a circular boundary.
An ArUco marker is used as a reference to calculate the pixel-to-centimetre conversion ratio. This ratio needs to be computed so i can use it to estimate the area of both the targets in cm².
When both targets are detected, the difference between their centroid coordinates is calculated to determine the blue object's position relative to the yellow-green tennis ball.
The camera feed shows the desired output.

Other possible methods: A pre-trained (can even get custom ones too) YOLO model can be used to detect and track both objects simultaneously.
Background subtraction can be used to separate moving objects from a stationary background.
 You can also even identify objects by comparing them with predefined image templates.
