# Tanaka Contours
This project was created as an assignment for the Digital Terrain Modelling course (GEO1015) of the Geomatics program at the TU Delft. Hugo Ledoux, the course coordinator, provided a lot of information, some code, and the dem_01.tif data file. Parts of the information in this file were directly copied from his course [website](https://3d.bk.tudelft.nl/courses/geo1015/) and his [book](https://tudelft3d.github.io/terrainbook/), both of which I highly recommend to look at when you are interested in Digital Terrain Modelling. Hugo also took inspiration from two blog posts ([1](https://anitagraser.com/2015/05/24/how-to-create-illuminated-contours-tanaka-style/),[2](https://landscapearchaeology.org/2018/tanaka-contour-lines/)), which illustrate how to create Tanaka contours with QGIS. These are however quite complex and require many steps; that is why this Python program will automate most of the work. 

Professor Kitiro Tanaka invented the Relief Contour Method method in 1950, though the method quickly became synonymous with his name. Tanaka Contours, sometimes also known as illuminated contours, give the isolines of a map the appearance of three-dimensionality. The lines are illuminated/white when facing the source of light, and shaded/black when not. As is usually the case with the visualisation of terrains, we use the northwest direction as the source of light. If you want to know why take a look [here](https://ramblemaps.com/why-does-sunlight-come-from-north). 

![image](https://github.com/user-attachments/assets/e98ff8aa-86fd-44bc-ab2f-0b9efa9cf876)


# How does Create_Tanaka_Contours.py work?
The Python program reads a gridded DTM in GeoTIFF format and filters out all the NaN values. It then randomly picks a certain amount of points from the raster and constructs a Delaunay Triangulation (DT). This Triangular irregular network (TIN) is then exported as mydt in PLY format and can be used to visualise the terrain in 2.5D (with one possible Z value per coordinate). The program then uses this DT to construct isolines. It visits each of the triangles and determines if the plane of the triangle intersects with the Z value of the isoline and if so, where. It then takes two points intersection points to form a line segment. All the line segments next to each other will form an isoline. To be able to create Tanaka contours, we need to orient the isolines consistently. In our case, this means that each line segment in an isoline needs to be oriented counter-clockwise and thus that higher ground is on the left side of the line. The program visits each of the line segments which we extracted and determines the height value in the DT on the right side. If the height value is higher than the height of the isoline, the two points of the line segment are switched (i.e. rotated). 

![image](https://github.com/user-attachments/assets/64bf5baa-c34a-4160-9309-3883df3b3b16)


There are still two other attributes we need to add to each line segment: the azimuth and the lightness. The azimuth of the line segment is the angle (in degrees) between the North and the line segment, measured clockwise in the horizontal plane (North=0; East=90; South=180; West=270). This angle is then used to determine the lightness value (in the range [0,100]) to correctly shade the line segments. 

![image](https://github.com/user-attachments/assets/12988426-6c14-4af2-91f3-46403a73e5cf)

All the line segments are then exported to a GeoJSON file to be visualised and used in QGIS in combination with mydt.ply file to visualise the Tanaka contour. 

# How to use Create_Tanaka_contours.py?
To run the code you first need to install the following libraries:

```
pip install -U startinpy
pip install -U rasterio
pip install -U numpy
```

And then use the command prompt (or input the parameters):

```
python Create_Tanaka_contours.py myinput.tiff 0.1 '(100, 500, 50)'
```

The arguments are as follows:
1. The input GeoTIFF file;
2. The percentage of input cells (including the no-data values) that should be inserted (should be in the range [0,1]);
3. A Python range that defines which contours need to be extracted. It is given as a string: (100, 500, 100) which means 4 contour heights will be extract: 100, 200, 300, and 400.

The program then writes in the same folder mycontours.geojson and mydt.ply. These files need to be inserted into QGIS to create the final map. Make sure the Coordinate Reference System for the view is disabled, as the CRS of the GeoTIFF file is (WGS84) might differ from the CRS of the input file. At the moment there is no coordinate transformation between the two. Based on the “lightness” attribute in the GeoJSON file, simply change the styling of the lines in QGIS to obtain Tanaka contours (the expression is color_hsl(0, 0, lightness), which will use the value of the attribute in the dataset) and change the colours of mydt.ply to 'Discrete' and input the same range as the isolines.

![image](https://github.com/user-attachments/assets/04bc209a-1f30-470c-96b5-5ba4e84c25b9)

![image](https://github.com/user-attachments/assets/7f28e572-3c9c-4246-a14c-161dce41836d)

![image](https://github.com/user-attachments/assets/fa921c84-2ea4-409f-9da0-cc36d2e471d8)

# The current limits of Create_Tanaka_contours.py [26-11-2024]
The current Create_Tanaka_contours.py file still has some limitations. The code will be updated to improve and remove these limitations:
* For “real” Tanaka contours, the width of the contours should also be modified based on their orientation;
* The input file can still only be completly square, since there is no constrained Delaunay Triangulation available in startinpy which can accept the concave hull of the valid data as border;
* Technically GeoJSON can only have geometries stored in WGS84, but the CRS of the input file is used.

