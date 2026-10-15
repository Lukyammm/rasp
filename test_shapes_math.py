import math

def is_point_inside_studio_shape(x, y, w, h, shape, invert=False):
    nx = (x - w / 2) / (w / 2)
    ny = (y - h / 2) / (h / 2)
    inside = True

    if shape == '16x9':
        inside = abs(nx) <= 0.94 and abs(ny) <= 0.94
    elif shape == '1x1':
        min_side = min(w, h)
        inside = abs(x - w / 2) <= (min_side * 0.46) and abs(y - h / 2) <= (min_side * 0.46)
    elif shape == '9x16':
        inside = abs(nx) <= 0.92 and abs(ny) <= 0.94
    elif shape == 'circle':
        inside = (nx * nx + ny * ny) <= 0.90
    elif shape == 'speech':
        body = abs(nx) <= 0.88 and -0.85 <= ny <= 0.52
        tail = -0.65 <= nx <= -0.15 and 0.52 <= ny <= 0.92 and (ny - 0.52) <= (0.40) * (1 - (nx + 0.65) / 0.50)
        inside = body or tail
    elif shape == 'heart':
        px = nx * 1.15
        py = -ny * 1.15 + 0.25
        inside = ((px * px + py * py - 1) ** 3 - px * px * py * py * py) <= 0
    elif shape == 'cloud':
        b1 = (nx / 0.85) ** 2 + ((ny - 0.1) / 0.45) ** 2 <= 1
        c1 = (nx / 0.45) ** 2 + ((ny + 0.2) / 0.45) ** 2 <= 1
        c2 = ((nx + 0.4) / 0.35) ** 2 + ((ny + 0.05) / 0.35) ** 2 <= 1
        c3 = ((nx - 0.45) / 0.38) ** 2 + ((ny + 0.08) / 0.38) ** 2 <= 1
        inside = b1 or c1 or c2 or c3
    elif shape == 'star':
        # 10 vertex star
        pts = []
        for i in range(10):
            ang = i * (math.pi / 5) - math.pi / 2
            r = 0.92 if (i % 2 == 0) else 0.58
            pts.append((r * math.cos(ang), r * math.sin(ang)))
        # Point in polygon
        c = False
        j = len(pts) - 1
        for i in range(len(pts)):
            if ((pts[i][1] > ny) != (pts[j][1] > ny)) and (nx < (pts[j][0] - pts[i][0]) * (ny - pts[i][1]) / (pts[j][1] - pts[i][1]) + pts[i][0]):
                c = not c
            j = i
        inside = c
    elif shape == 'shield':
        if ny < -0.88 or ny > 0.92 or abs(nx) > 0.85:
            inside = False
        elif ny <= 0.1:
            inside = True
        else:
            limit = 0.85 * (1.0 - ((ny - 0.1) / 0.82) ** 1.8)
            inside = abs(nx) <= limit
    elif shape == 'trophy':
        cup = abs(nx) <= 0.62 and -0.85 <= ny <= 0.05
        handles = 0.50 <= abs(nx) <= 0.88 and -0.75 <= ny <= -0.15 and not (0.62 <= abs(nx) <= 0.76 and -0.65 <= ny <= -0.25)
        stem = abs(nx) <= 0.18 and 0.05 <= ny <= 0.55
        base = abs(nx) <= 0.70 and 0.55 <= ny <= 0.88
        inside = cup or handles or stem or base
    elif shape == 'hexagon':
        inside = abs(nx) <= 0.85 and (abs(nx) * 0.5 + abs(ny) * 0.866) <= 0.82
    if invert:
        return not inside
    return inside

# Test all shapes with center point (should be inside)
shapes = ['16x9', '1x1', '9x16', 'circle', 'speech', 'heart', 'cloud', 'star', 'shield', 'trophy', 'hexagon']
for s in shapes:
    res = is_point_inside_studio_shape(300, 200, 600, 400, s)
    assert res == True, f"Shape {s} failed center test"
print("All 11 shapes passed center test successfully!")

# Test angle distribution
def get_angle(mode, index, seed=1):
    if index == 0:
        return 0
    if mode == 'horizontal':
        return 0
    if mode == 'pred_horiz':
        r = (index * 5 + seed) % 7
        return math.pi / 2 if r == 1 else 0
    return 0

assert get_angle('pred_horiz', 0) == 0, "Top word must be horizontal"
angles = [get_angle('pred_horiz', i) for i in range(1, 50)]
vert_count = sum(1 for a in angles if a > 0)
print(f"Pred_horiz test: {vert_count} of 49 words vertical (~{vert_count/49*100:.1f}%), remainder horizontal.")
assert vert_count > 0, "Should have some vertical words"
assert vert_count < 20, "Should remain predominantly horizontal"
print("Angle distribution test passed!")
