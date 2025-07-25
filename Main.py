import cv2
import fitz  # PyMuPDF
import numpy as np
import math
from collections import defaultdict
import Preprocessors.Grey_box_detector2 as Grey_box_detector
import Preprocessors.Void_box_detector as Void_box_detector
import optimal_lines as OL
import Preprocessors.Rectangle_subtraction as RS
import Box_grouper2 as  BG
import draw_arrows as DA

pdf_path = "./unprocessed_pdfs/131101-WIP12-DR-S-5123 & 5124_commented_20250414.pdf"

# Load rectangles and void boxes
rectangles = Grey_box_detector.find_bounding_boxes(pdf_path)


def get_enclosing_bounding_box(lines):
    points = np.array([[x, y] for line in lines for x, y in [(line[0], line[1]), (line[2], line[3])]])
    min_x, min_y = points.min(axis=0)
    max_x, max_y = points.max(axis=0)
    return (min_x, min_y), (max_x, max_y)

roi = get_enclosing_bounding_box(rectangles)
img = cv2.imread("page1.png")

#should only find void boxes within the part where the floor plan lies in.
void_boxes = Void_box_detector.find_voids(img, roi)

#convert rectangles to corner points
bounding_rects = rectangles #in the form of 4 (x1, y1, x2, y2)
void_rects = void_boxes #in the form of 4 (x1, y1, x2, y2)



# Sort rectangles by top-left position
def sortingkey(banded = True):
    def top_left_sort_key(box):
        x1, y1, x2, y2 = box
        top_y = min(y1, y2)
        left_x = min(x1, x2)
        row_band = round(top_y / 100) if banded else top_y
        return (row_band, left_x)
    return top_left_sort_key

# rectangles.sort(key=sortingkey())
void_boxes.sort(key=sortingkey(banded=False))

# Do rectangular substraction
remaining_rects = RS.rectangle_subtraction(bounding_rects, void_rects, 20, 20, 500)


# Group threshold for similar top y positions
Y_THRESHOLD = 20
boxes = remaining_rects

# groups = defaultdict(list) #maps the groups to the (box index, box)
# for idx, box in enumerate(boxes):
#     top_y = min(point[1] for point in box)
#     key = round(top_y / Y_THRESHOLD)
#     groups[key].append((idx + 1, box)) #box index, box
groups = BG.group_boxes(remaining_rects, void_rects)

# Find horizontal span
x_leftbound = min(min(x1, x2) for (x1, _, x2, _) in rectangles)
x_rightbound = max(max(x1, x2) for (x1, _, x2, _) in rectangles)



# Load the image to get dimensions

image = img
img_height, img_width = image.shape[:2]

# Open the PDF and get page dimensions
output_pdf_path = "annotated.pdf"
doc = fitz.open(pdf_path)
page = doc[0]
pdf_width, pdf_height = page.rect.width, page.rect.height

# Coordinate scaling function
def scale_coords(x, y):
    return (x / img_width) * pdf_width, (y / img_height) * pdf_height

# Draw lines on PDF
MAX_LEN = 2500
Y_OFFSET = 6
X_OVERLAP = 40

def get_rect_x_range(rects): #find the lowest and highest x values for the boxes
    x_values = [x for rect in rects for x in (rect[0], rect[2])]
    return min(x_values), max(x_values)

x_min, x_max = get_rect_x_range(bounding_rects) #the minimum x and max x for the rectangles

print("\nAnnotating diagram....")
last_percent = -1 #initialize variable for progress printing

for key, group in groups.items():

    #percentage completion tracking
    percent = (100*key//len(groups))
    if percent % 20 == 0 and percent != last_percent:
        print(f"Progress: {percent}% complete")
        last_percent = percent
    

    lines, arrows = OL.find_optimal_lines(group, Y_OFFSET, X_OVERLAP, x_rightbound, x_leftbound, x_min, x_max, MAX_LEN)

    for line in lines:
        (x1, y), (x2, y) = line
        sx1, sy1 = scale_coords(x1, y)
        sx2, sy2 = scale_coords(x2, y)
        line = page.add_line_annot((sx1, sy1), (sx2, sy2))
        line.set_colors(stroke=(0.4, 0.4, 0.8))
        line.set_border(width=2)
        line.update()
        # note = page.insert_text((0.5*(sx1 + sx2), 0.5*(sy1+sy2)), str(key), fontsize = 6, color = (0, 0 ,1))

    
    for arrow in arrows:
        (x, y1), (_, y2) = arrow
        sx, sy1 = scale_coords(x, y1)
        _, sy2 = scale_coords(x, y2)

        DA.draw_vertical_arrow(page, sx, sy1, sy2, (0.4, 0.4, 0.8))



    
    # # Label box indices
    # for idx, box in group:
    #     x1, y1, x2, y2 = box
    #     center_x = int((x1 + x2) / 2)
    #     center_y = int((y1 + y2) / 2)
    #     sx, sy = scale_coords(center_x, center_y)
        
    #     note = page.insert_text((sx, sy), f"{idx},{key}", fontsize=8, color=(1, 0, 0))
        # Writes the idx and group key

        # # Draw rectangle
        # sx1, sy1 = scale_coords(x1, y1)
        # sx2, sy2 = scale_coords(x2, y2)
        # rect = fitz.Rect(sx1, sy1, sx2, sy2)
        
        # shape = page.new_shape()
        # shape.draw_rect(rect)
        # shape.finish(color=(0, 0, 1), fill=None, width=0.5)
        # shape.commit()



# # Draw rectangles around all void_rects
# for x1, y1, x2, y2 in void_rects:
#     sx1, sy1 = scale_coords(x1, y1)
#     sx2, sy2 = scale_coords(x2, y2)
#     rect = fitz.Rect(sx1, sy1, sx2, sy2)
#     shape = page.new_shape()
#     shape.draw_rect(rect)
#     shape.finish(color=(1, 0, 0), fill=None, width=0.5)  # Red outline for voids
#     shape.commit()



# Save the annotated PDF
doc.save(output_pdf_path)
doc.close()

print(f"\nAnnotated PDF saved as {output_pdf_path}")
