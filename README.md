Additional scripts extending the functionality of the moniQue QGIS plugin. Why this separate repository? While developing a QGIS plugin has several benefits, it comes with one certain limitation: One is limited / constrained to the provided QGIS Python version. Especially for some libraries with additional dependencies (C++ etc.) it gets quite tricky. Therefore we decided to move some functionalities from the core plugin to this auxiliary repository.

## Installation
On Windows, installing via Conda is strongly recommended:
```
conda create -n venv_name
conda activate venv_name
conda install -c conda-forge pydelatin gdal typer pillow pyproj pip pandas imageio
pip install open3d
```
While all packages are installed using conda we need to use pip for open3d as open3d does not maintain a recent version on conda. Now you can clone this repository to your local machine
```
cd to/your/dir
git clone https://github.com/smfloery/moniQue-helper.git
```
With the previously created environment activated in the Anaconda prompt you can now run 
```
python PATH/TO/moniQue-helper\main.py --help
```
to see an overview over all available funcions. If you want help for a specific funtion run
```
python PATH/TO/moniQue-helper\main.py create-mesh --help
```

### Create tiled mesh from a digital terrain model (create-mesh)
With this tool you can create simplified mesh tiles from a digital terrain model (DTM). This is the basic requirement for moniQue to represent the terrain in 3D. 
```
python PATH/TO/main.py create-mesh DTM_PATH OUT_DIR OUT_NAME MAX_ERROR --tile-size 1000 --extent None None None None
```

``DTM_PATH`` is the path to the raster file representing your DTM: Any GDAL suuported raster format is provided. ``OUT_DIR`` is the output directory. Within this directory a ``OUT_NAME``.json will be created which is required by moniQue. Furthermore, a subfolder ``mesh`` will be created where the individual tiles are stored in the .ply format.  The last argument ``MAX_ERROR`` is used to defined the simplification of the mesh. This is the maximum deviation in meters of the final mesh from the original DTM. Accordingly, high values will lead to much more decimeted meshes. Per default, a tile size of 1000px will be used. This can be manually adjusted with the ``--tile-size`` option. Furthermore, the input DTM can be clipped to a subregion before the tiles are created. For that the extent must be specifified as ``--extent minx miny maxx maxy``. If no extent is provided, the whole DTM will be used.

We tested moniQue with a DTM of 1m x 1m resolution up to extents of 25km x 25km with a tilesize of 1000px x 1000px. Above 15km performance slowly decreases, especially with an orthophoto of 1m x 1m as texture.

### Create orthophoto tiles (add-ortho)
In many cases you want to add an orthophoto as texture onto the mesh. Accordingly, its necessary to split the available orthophoto into the same tiles as the mesh. This can be done with the add-ortho tool:
```
python PATH/TO/main.py add-ortho OP_PATH JSON_PATH
```
``OP_PATH`` is the path to the orthophoto. AS for the DTM, all GDAL supported raster formates are supported. ``JSON_PATH`` is the path to the .json file created with ``create-mesh``. Per default, the resulting tiles will have a resolution of 1 meter. This can be changed with the optional ``--op-res`` argument. The output of this tool will be in the same directory as the mesh tiles within a new directory called ``op``. We tested moniQue with an OP of 1 meter. Below that, depending on the extent of the DTM, performance might drop.

### Render scene from JSON (render-json)
moniQue offerts the functionality to store the current 3D camera view as .json. This .json can be used to render the visible scene as RGB image as well as with the xyz-coordinates of the scene. 
```shell
python PATH/TO/main.py render-json CAMERA_JSON TILES_JSON OUT_DIR
```
``CAMERA_JSON`` is the path to the .json file created with monique and contains the camera parameters. ``TILES_JSON`` is the path to the .json file created with ``create-mesh`` and contains information on the mesh as well as orthophoto tiles. ``OUT_DIR`` is the directory where the results shall be stored. By default also an additional images containing the xyz-coordinates of the scene will be created. To avoid this the optional argument ``--no-xyz`` can be passed. The ``CAMERA_JSON`` must have the following format

```json
{
    "NAME": {
        "project": "path/to/gpkg",
        "X0": 4530483.3,
        "Y0": 2666130.4,
        "Z0": 2436.0,
        "alpha": 0.0,
        "zeta": 1.656633,
        "kappa": 1.56895,
        "fov": 0.763068,
        "img_w": 1682,
        "img_h": 1070
    }
}
```
``X0``, ``Y0`` and ``Z0`` are the coordinates of the projection center in the same coordinates system as the mesh. ``alpha``, ``zeta`` and ``kappa``define the rotation of the camera. ``fov`` is the field of view of the camera. ``img_w`` and ``img_h`` are the dimensions of the output image. 

### Render scene (with oriented image) from GKPG (render-gkpg)
Similar to the previous function (render-json) it is possible to render the 3D scene with and without the oriented image directly from the .gpkg used by monique. 

```shell
main.py render-gpkg [OPTIONS] GPKG_PATH OUT_DIR
```

If the path to the .gpkg is provided (``GPKG_PATH``) and a output directory specified (``OUT_DIR``), two images will be created: One image showing only the rendered 3D scene and a second image containing the orientied image. The padding around the historical image is defined with the ``--padding`` option and is given in degrees. Accordingly, using 5 means that 2.5° are added equally around the historical image. The position of the historical image in the object space is defined with the ``--hist-dist`` option and referes to the distance of the image from the projection center in meter. If the additional rendering with the historical image shall not be created, the option ``--no-hist`` must be provided. If the output renderings shall have other image dimensions the respective with and heigth can be set with ``--width`` and ``--height``.

### Render animated scene from GKPG (animate-gkpg)
```shell
main.py animate-gpkg [OPTIONS] GPKG_PATH GIF_DIR 
```
With this function a MP4 animation of a selected historical image can be directly generated from the .gpkg. The main difference to the previous function is the ``--dist-range`` option, which specifies the position of the historical image in each frame. ``--dist-range start stop min_step max_step``. This will create an animation where the historical image in the first frame is ``start`` meters aways from the camera. This distance is increased in each frame by an exponentially growing value between ``min_step`` and ``max_step`` until it reaches ``stop``. These frames are afterwards reversed, creating a looped animation, where the historical image ends up, back at a distance of ``start`` meters from the camera. Additionally name-tags can be added to the scene at a user-definded position and hight above ground, using the ``--name-tag`` option. This can be done by specifying the location and name as follows: ``--name-tag lat,lon,hight,name``.
