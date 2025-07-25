import numpy as np
from collections import defaultdict


def box_bounds(box):
    if isinstance(box, np.ndarray):
        x_coords = box[:, 0]
        y_coords = box[:, 1]
    elif isinstance(box, list) and all(isinstance(pt, tuple) and len(pt) == 2 for pt in box):
        x_coords = [pt[0] for pt in box]
        y_coords = [pt[1] for pt in box]
    elif isinstance(box, tuple) and len(box) == 4:
        return box  # Already in (x1, y1, x2, y2) format
    else:
        raise ValueError(f"Unsupported box format: {box}")
    
    return min(x_coords), min(y_coords), max(x_coords), max(y_coords)





def compute_overlap(a_min, a_max, b_min, b_max):
        return max(0, min(a_max, b_max) - max(a_min, b_min))

def is_horizontally_aligned(box1, box2, threshold=30): #two boxes are aligned approximately on the x-axis
    _, y1_min, _, y1_max = box_bounds(box1)
    _, y2_min, _, y2_max = box_bounds(box2)
    return abs(y1_min - y2_min) <= threshold and abs(y1_max - y2_max) <= threshold

def is_horizontally_between(box1, box2, boxMiddle): #boxmiddle is in the middle of box1 and box2
    x1_min, y1_min, x1_max, y1_max = box_bounds(box1)
    x2_min, y2_min, x2_max, y2_max = box_bounds(box2)
    xM_min, yM_min, xM_max, yM_max = box_bounds(boxMiddle)

    if compute_overlap(x1_min, x1_max, x2_min, x2_max) > 0:  #box1 and box2 overlap vertically
        return False
    
    if compute_overlap(y1_min, y1_max, y2_min, y2_max) == 0: #box1 and box2 are not at all horizontally aligned
        return False
    

    #there is some horizontal alignment between middle box and other boxes
    middlebox_overlap = compute_overlap(y1_min, y1_max, yM_min, yM_max) > 0 and compute_overlap(yM_min, yM_max, y2_min, y2_max) > 0
    middlebox_between = min(x1_max, x2_max) <= xM_min and xM_max <= max(x1_min, x2_min)

    if middlebox_overlap and middlebox_between:
        return True
    else:
        return False

    
def check_void_between_horizontal(current_box, next_box, void_boxes): #ASSUME THAT VOID BOXES ARE ALREADY SORTED BY MIN X 
    curr_x1 = current_box[0]
    next_x2 = next_box[2]

    for void_box in void_boxes:
        void_x1, void_y1, void_x2, void_y2 = void_box

        # Skip void boxes that start before current box ends
        if void_x1 < curr_x1:
            continue
        # If void box ends after next box starts, it's not between
        if void_x2 > next_x2:
            continue

        # Check vertical overlap with current_box
        curr_y1, curr_y2 = min(current_box[1], current_box[3]), max(current_box[1], current_box[3])
        void_y_min, void_y_max = min(void_y1, void_y2), max(void_y1, void_y2)
        overlap_curr = compute_overlap(void_y_min, void_y_max, curr_y1, curr_y2)

        # Check vertical overlap with next_box
        next_y1, next_y2 = min(next_box[1], next_box[3]), max(next_box[1], next_box[3])
        overlap_next = compute_overlap(void_y_min, void_y_max, next_y1, next_y2)

        if overlap_curr > 0 and overlap_next > 0:
            return True

    return False


def check_void_between_vertical(current_box, next_box, void_boxes):
    curr_y1 = current_box[1]
    next_y2 = next_box[3]

    for void_box in void_boxes:
        void_x1, void_y1, void_x2, void_y2 = void_box

        # Skip void boxes that start before current box ends
        if void_y1 < curr_y1:
            continue
        # If void box ends after next box starts, it's not between
        if void_y2 > next_y2:
            continue

        # Check vertical overlap with current_box
        curr_x1, curr_x2 = min(current_box[0], current_box[2]), max(current_box[0], current_box[2])
        void_x_min, void_x_max = min(void_x1, void_x2), max(void_x1, void_x2)
        overlap_curr = compute_overlap(void_x_min, void_x_max, curr_x1, curr_x2)

        # Check vertical overlap with next_box
        next_x1, next_x2 = min(next_box[0], next_box[2]), max(next_box[0], next_box[2])
        overlap_next = compute_overlap(void_x_min, void_x_max, next_x1, next_x2)

        if overlap_curr > 0 and overlap_next > 0:
            return True

    return False


def is_vertically_adjacent(box1, box2, threshold=30):
    x1_min, y1_min, x1_max, y1_max = box_bounds(box1)
    x2_min, y2_min, x2_max, y2_max = box_bounds(box2)

    vertical_alignment = abs(x1_min - x2_min) <= threshold and abs(x1_max - x2_max) <= threshold
    vertical_gap = min(abs(y2_min - y1_max), abs(y1_min - y2_max))

    return vertical_alignment and vertical_gap <= threshold






def group_boxes_horizontal(boxes, void_boxes, min_lone_box_size=4000):
    # Sort boxes by their leftmost x value
    boxes = sorted(boxes, key=lambda b: b[0])
    grouped = defaultdict(list)
    used = set()

    def box_bounds(box):
        x1, y1, x2, y2 = box
        return min(x1,x2), min(y1, y2), max(x1,x2), max(y1, y2)
    
    group_id = 0

    for i, box in enumerate(boxes):
        if i in used:
            continue

        group = [(i,box)]
        used.add(i)
        current_box = box

        for j in range(i + 1, len(boxes)):
            if j in used:
                continue

            next_box = boxes[j]
            x_next1, _, x_next2, _ = box_bounds(next_box)
            x_curr2 = box_bounds(current_box)[2]

            if x_next1 < x_curr2:
                continue

            y1_min, y1_max = box_bounds(current_box)[1], box_bounds(current_box)[3]
            y2_min, y2_max = box_bounds(next_box)[1], box_bounds(next_box)[3]

            if compute_overlap(y1_min, y1_max, y2_min, y2_max) == 0:
                continue

            if not is_horizontally_aligned(current_box, next_box):
                break

            # Placeholder for void check
            if check_void_between_horizontal(current_box, next_box, void_boxes):
                break

            group.append((j, next_box))
            used.add(j)
            current_box = next_box

        #filter out small single member groups
        if len(group) == 1:
            lone_box = group[0][1]
            x1_min, y1_min, x1_max, y1_max = box_bounds(lone_box)
            area = (x1_max - x1_min) * (y1_max - y1_min)
            if area < min_lone_box_size:
                continue

        grouped[group_id] = group
        group_id+=1

    return grouped


# Helper function to compute bounding box of a group
def compute_group_bounds(group):
    x_min = min(box[0] for _, box in group)
    y_min = min(box[1] for _, box in group)
    x_max = max(box[2] for _, box in group)
    y_max = max(box[3] for _, box in group)
    return (x_min, y_min, x_max, y_max)

def group_box_vertical(grouped): #merge the groups by vertical alignment
    group_bounds = {gid: compute_group_bounds(group) for gid, group in grouped.items()}
    merged = defaultdict(list)
    used = set()
    new_group_id = 0

    group_ids = sorted(grouped.keys(), key=lambda gid: group_bounds[gid][1])  # sort by y_min

    for i in group_ids:
        if i in used:
            continue
        merged_group = grouped[i]
        used.add(i)
        for j in group_ids:
            if j in used or i == j:
                continue
            if is_vertically_adjacent(group_bounds[i], group_bounds[j]):
                merged_group.extend(grouped[j])
                used.add(j)
        merged[new_group_id] = merged_group
        new_group_id += 1

    return merged



def group_boxes(boxes, void_boxes, min_lone_box_size=4000):
    hor_grouped = group_boxes_horizontal(boxes, void_boxes, min_lone_box_size=4000)
    vert_grouped = group_box_vertical(hor_grouped)
    return vert_grouped




# def group_boxes(bounding_boxes, void_boxes, min_lone_box_size=6000):
#     sorted_boxes = sorted(enumerate(bounding_boxes), key=lambda x: box_bounds(x[1])[0])
#     visited = set()
#     groups = {}
#     group_id = 0

#     for i, box in sorted_boxes:
#         if i in visited:
#             continue
#         current_group = [(i, box)]
#         visited.add(i)
#         current_box = box

#         for j, candidate_box in sorted_boxes:
#             if j in visited or j == i:
#                 continue

#             # Check horizontal alignment and no void
#             if is_horizontally_aligned(current_box, candidate_box) and not is_void_between(current_box, candidate_box, void_boxes, direction='right'):
#                 # Check for intervening boxes
#                 x1, y1, x2, y2 = box_bounds(current_box)
#                 cx1, cy1, cx2, cy2 = box_bounds(candidate_box)
#                 left, right = min(x2, cx2), max(x1, cx1)

#                 has_intervening_box = False
#                 for k, other_box in sorted_boxes:
#                     if k in visited or k == i or k == j:
#                         continue
#                     ox1, oy1, ox2, oy2 = box_bounds(other_box)
#                     if left <= ox1 <= right and compute_overlap(oy1, oy2, cy1, cy2) > 0 and compute_overlap(y1, y2, oy1, oy2) > 0:
#                         has_intervening_box = True
#                         break

#                 if not has_intervening_box:
#                     current_group.append((j, candidate_box))
#                     visited.add(j)
#                     current_box = candidate_box
#                 else:
#                     break  # Stop grouping if blocked by another box
#             else:
#                 break

#         # Filter out small lone boxes
#         if len(current_group) == 1:
#             x1, y1, x2, y2 = box_bounds(current_group[0][1])
#             area = (x2 - x1) * (y2 - y1)
#             if area < min_lone_box_size:
#                 continue

#         groups[group_id] = current_group
#         group_id += 1

#     return groups


# def is_void_between(box1, box2, void_boxes, direction='right', overlap_threshold=20):
    

#     x1_min, y1_min, x1_max, y1_max = box_bounds(box1)
#     x2_min, y2_min, x2_max, y2_max = box_bounds(box2)

#     # Determine horizontal gap between boxes
#     gap_left = min(x1_max, x2_max)
#     gap_right = max(x1_min, x2_min)

#     for vb in void_boxes:
#         vx_min, vy_min, vx_max, vy_max = vb
#         vx_min, vx_max = min(vx_min, vx_max), max(vx_min, vx_max)
#         vy_min, vy_max = min(vy_min, vy_max), max(vy_min, vy_max)

#         if direction == 'right':
#             # Check if void is within horizontal gap
#             if vx_min >= gap_left - overlap_threshold and vx_max <= gap_right + overlap_threshold:
#                 # Check vertical overlap
#                 vertical_overlap = compute_overlap(y1_min, y1_max, vy_min, vy_max)
#                 if vertical_overlap > 0:
#                     return True

#         elif direction == 'below':
#             # Determine vertical gap between boxes
#             gap_top = min(y1_max, y2_max)
#             gap_bottom = max(y1_min, y2_min)

#             # Check if void is within vertical gap
#             if vy_min >= gap_top - overlap_threshold and vy_max <= gap_bottom + overlap_threshold:
#                 # Check horizontal overlap
#                 horizontal_overlap = compute_overlap(x1_min, x1_max, vx_min, vx_max)
#                 if horizontal_overlap > 0:
#                     return True

#     return False