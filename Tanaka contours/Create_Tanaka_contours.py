# -- geo1015.2024.hw01
# -- [Heiko Rotteveel]
# -- [5480787]

import argparse
import json
import sys
import time
import itertools

import math

import numpy as np
import rasterio
import startinpy

def create_TIN(filename, thinning = 0.1):
    """
    Creates a TIN based on a .tif file with a desired resolution (based on the thinning factor)
    :param filename: a .tif filetype
    :param thinning: a value in range [0,1], determines percentage of points to pick
    :return: a startinpy.DT
    """

    # -- load in memory the input GeoTIFF
    try:
        # -- this gives you a Rasterio dataset
        # -- https://rasterio.readthedocs.io/en/latest/quickstart.html
        d = rasterio.open(filename)
    except Exception as e:
        print(e)
        sys.exit()

    # -- Reads the .tif file and filters all the invalid data types
    d = rasterio.open(filename)
    band1 = d.read(1)
    t = d.transform
    pts = []
    for i in range(band1.shape[0]):
        for j in range(band1.shape[1]):
            x = t[2] + (j * t[0]) + (t[0] / 2)
            y = t[5] + (i * t[4]) + (t[4] / 2)
            z = band1[i][j]
            if z != d.nodatavals:
                pts.append([x, y, z])

    # -- If there are less valid data points than the wanted thinning factor expects, pick the maximum amount of points
    if not(len(pts) <= thinning*band1.shape[0]*band1.shape[1]):
        choice_indices = np.random.choice(len(pts), int(thinning * band1.shape[0] * band1.shape[1]), replace=False)
        pts = [pts[i] for i in choice_indices]

    # -- Create Delaunay triangulation and write to PLY file
    dt = startinpy.DT()
    dt.insert(pts, insertionstrategy="BBox")
    dt.write_ply("mydt.ply")
    return dt

def determine_line_segment(pt1, pt2, height):
    """
    Looks at a line between points and determines if the height value is somewhere on that line.

    :param pt1: a point [x,y,z]
    :param pt2: a point [x,y,z]
    :param height: a height value (int or float)
    :return [pt], [pt1, pt2] or None
    """

    x1, y1, z1 = pt1
    x2, y2, z2 = pt2

    # -- Check if the line is parallel to the height value
    if z1 == z2:
        if z1 == height:
            # -- If z1 == z2 == n, the whole segment lies on the desired height
            return [[x1, y1, height], [x2, y2, height]]
        else:
            # -- No intersection with height
            return None

    # -- Find the parameter t where z(t) = height
    # -- z(t) = z1 + t * (z2 - z1), solve for t when z = height
    t = (height - z1) / (z2 - z1)

    # -- Check if t is within the range [0, 1] (line segment bounds)
    if 0 <= t <= 1:
        # -- Calculate the corresponding x and y
        x = x1 + t * (x2 - x1)
        y = y1 + t * (y2 - y1)
        return [[x, y, height]]

    else:
        # -- No valid t in the range [0, 1], so no intersection
        return None

def create_isoline(dt, height):
    """
    Creates an isoline of a certain height based on a Delaunay Triangulation
    :param dt: a starinpy.DT
    :param height: a height value (int or float)
    :return: a list of line segments
    """
    isoline = []

    # -- Visit all triangles in the Delaunay triangulation
    for triangle in dt.points[dt.triangles]:
        line_segment = []

        # -- If all points of the triangle are either higher or lower, you can skip this triangle
        if all(z > height for (_, _, z) in triangle) or all(z < height for (_, _, z) in triangle):
            continue

        # -- Visit all edges in the triangle and check if the desired height value is somewhere on the edge
        for segment in itertools.combinations(triangle, 2):
            result = determine_line_segment(segment[0], segment[1], height)

            # -- If result is None, then no point has been found and the next edge can be visited
            if result is None:
                continue

            # -- If a result has been found, add the point to the new line segment
            else:
                line_segment.extend(result)

        else:
            # -- Remove all points that have been identified more than once
            line_segment = ([list(x) for x in set(tuple(x) for x in line_segment)])

            # -- If the line segment does not have 2 points in it, then it can be ignored
            # -- This will happen if there is one point, with two higher/lower points in the triangle
            # -- Or if the triangle is flat the adjacent triangles will identify the edge as a line segment
            if len(line_segment) != 2:
                continue
            else:

                # -- If the line segment already occurs in the isoline, then it does not need to be added
                if line_segment not in isoline:
                    isoline.append(line_segment)
    return isoline

def point_right_of_line(pt1, pt2, offset = 0.000000001):
    """
    Takes two points of a line segment and identifies a point closely to the Right of the line
    :param pt1: a point [x,y,z]
    :param pt2: a point [x,y,z]
    :param offset: a float or int
    :return: x (float), y (float)
    """

    x1, y1, z1 = pt1
    x2, y2, z2 = pt2

    # -- Compute the midpoint of the line
    mid_x = (x1 + x2) / 2
    mid_y = (y1 + y2) / 2

    # -- Compute the direction vector of the line
    dx = x2 - x1
    dy = y2 - y1

    # --  Determine the perpendicular vector (rotated 90 degrees clockwise (to the right))
    perp_x = dy
    perp_y = -dx

    # -- Normalize the perpendicular vector
    length = math.sqrt(perp_x ** 2 + perp_y ** 2)
    perp_x /= length
    perp_y /= length

    # -- Offset the midpoint in the perpendicular direction
    x = mid_x + perp_x * offset
    y = mid_y + perp_y * offset

    return x, y

def orientate_isoline(dt, isoline):
    """
    Takes an isoline of a Delaunay Triangulation and orientates it Counter-clockwise
    :param dt: a startinpy.DT
    :param isoline: a list of line segments
    :return: a list of oriented line segments
    """
    for line_segment in isoline:
        # -- Determine for each line segment a point to the right of the line
        x, y = point_right_of_line(line_segment[0],line_segment[1])

        # -- If the point to the right of the line segment is higher than the height of the line segment: rotate
        if dt.interpolate({"method": "TIN"}, [[x,y]]) > line_segment[0][2]:
            line_segment[0], line_segment[1] = line_segment[1], line_segment[0]
    return isoline

def add_azimuth(isoline):
    """
    Add the azimuth of each line segment to an isoline list
    :param isoline: a list of line segments
    :return: a list of line segments: [pt1, pt2, azimuth]
    """

    for line_segment in isoline:
        ax, ay, az = line_segment[0]
        bx, by, bz = line_segment[1]
        Two_PI = math.pi * 2
        theta = math.atan2(ay - by, bx - ax)
        if theta < 0.0:
            theta += Two_PI
        line_segment.append(math.degrees(theta))
    return isoline

def determine_lightness(azimuth):
    """
    Determines a lightness value based on the azimuth
    :param azimuth: the angle in degrees between the North and the line segment measured clockwise
    :return: a value in the range [0,100]
    """
    lightness = abs(((azimuth-255) % 360 ) - 180)
    return lightness / 180 * 100

def write_geojson_file(l):
    """
    Takes as input a list of oriented isolines with azimuth values, and adds the lightness before writing it in a GeoJSON format
    :param l:
    :return: a dictionary in a GeoJSON format
    """
    mygeojson = {}
    mygeojson["type"] = "FeatureCollection"
    mygeojson["features"] = []
    for isoline in l:
        for LineString in isoline:
            lightness = determine_lightness(LineString[2])
            f = {}
            f["type"] = "Feature"
            f["geometry"] = {"type": "LineString", "coordinates": [LineString[0][:2], LineString[1][:2]]}
            f["properties"] = {"height": LineString[0][2], "azimuth": LineString[2], "lightness": lightness}
            mygeojson["features"].append(f)

    return mygeojson

def main():
    t0 = time.time()

    # -- Accept arguments from the terminal
    parser = argparse.ArgumentParser(description="My GEO1015.2024 hw01")
    parser.add_argument("inputfile", type=str, help="GeoTIFF")
    parser.add_argument(
        "thinning", type=float, help="Thinning factor (between 0 and 1)"
    )
    parser.add_argument(
        "range", type=str, help="a Python range for the contours, eg: (0, 1000, 100)"
    )

    args = parser.parse_args()

    # --  Validate thinning factor
    if not 0 <= args.thinning <= 1:
        parser.error("Thinning factor must be between 0 and 1")

    # -- Validate the range
    try:
        tmp = list(map(int, args.range.strip("() ").split(",")))
    except:
        parser.error("range invalid")

    myrange = range(tmp[0], tmp[1], tmp[2])

    # -- Create a TIN using Delaunay Triangulation
    dt = create_TIN(args.inputfile, args.thinning)
    print("Delaunay triangulation created")

    # -- Create a list of isolines
    isoline_list = []
    for height in myrange:
        isoline = create_isoline(dt, height)
        isoline = orientate_isoline(dt, isoline)
        isoline = add_azimuth(isoline)
        isoline_list.append(isoline)
        print("Isoline", height, "Complete")

    # -- Write isolines to GeoJSON format
    mygeojson = write_geojson_file(isoline_list)
    with open("mycontours.geojson", "w") as file:
        file.write(json.dumps(mygeojson, indent=2))

    print("File 'mycontour.geojson' created.")

    t1 = time.time()
    print("Program completed in:", t1-t0, "seconds")

if __name__ == "__main__":
    create_TIN("dem_01.tif", 1)
