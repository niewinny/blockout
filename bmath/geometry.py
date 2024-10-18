'''Geometry functions'''

def distance_point_to_segment(p, v1, v2) -> float:
    '''Calculate the distance between a point and a segment
    
    Args:
        p (Vector): Point
        v1 (Vector): Segment start
        v2 (Vector): Segment end

    '''

    v = v2 - v1
    w = p - v1

    c1 = w.dot(v)
    if c1 <= 0:
        return (p - v1).length

    c2 = v.dot(v)
    if c2 <= c1:
        return (p - v2).length

    b = c1 / c2
    pb = v1 + b * v
    return (p - pb).length
