Additional scripts extending the functionality of the moniQue QGIS plugin. Why this separate repository? While developing a QGIS plugin has several benefits, it comes with one certain limitation: One is limited / constrained to the provided QGIS Python version. Especially for some libraries with additional dependencies (C++ etc.) it gets quite tricky. Therefore we decided to move some functionalities from the core plugin to this auxiliary repository.

## Installation
On Windows, installing via Conda is strongly recommended:
```
conda create -n venv_name
conda activate venv_name
conda install -c conda-forge pydelatin gdal typer pip
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

We tested moniQue with a DTM of 1m x 1m resolution up to extents of 25km x 25km with a tilesize of 1000px x 1000px. Even with an orthophoto of 1m x 1m as texture a solid performance on a regular desktop PC could be achieved.

### Create orthophoto tiles (add-ortho)
In many cases you want to add an orthophoto as texture onto the mesh. Accordingly, its necessary to split the available orthophoto into the same tiles as the mesh. This can be done with the add-ortho tool:
```
python PATH/TO/main.py add-ortho OP_PATH JSON_PATH
```
``OP_PATH`` is the path to the orthophoto. AS for the DTM, all GDAL supported raster formates are supported. ``JSON_PATH`` is the path to the .json file created with ``create-mesh``. Per default, the resulting tiles will have a resolution of 1 meter. This can be changed with the optional ``--op-res`` argument. The output of this tool will be in the same directory as the mesh tiles within a new directory called ``op``. We tested moniQue with an OP of 1 meter. Below that, depending on the extent of the DTM, performance might drop.
