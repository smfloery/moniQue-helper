import typer
from typing_extensions import Annotated
from rich.progress import track
import os
from enum import Enum
from monique_helper.terramesh import MeshGrid
from osgeo import gdal, osr
import json
import string

class MeshSimplification(str, Enum):
    delatin = "delatin"


app = typer.Typer()

@app.command()
def create_mesh(dtm_path:Annotated[str, typer.Argument()], 
                out_dir:Annotated[str, typer.Argument()],
                out_name:Annotated[str, typer.Argument()],
                max_error:Annotated[float, typer.Argument()],
                extent:Annotated[tuple[float, float, float, float], typer.Option(help="Clip input DTM to (minx, miny, maxx, maxy).")] = (None, None, None, None),
                method: Annotated[MeshSimplification, typer.Option(case_sensitive=False)] = MeshSimplification.delatin,
                tile_size:Annotated[int, typer.Option(help="Size of each tile in pixels.")] = 1000
                ):
    
    allowed_characters = string.ascii_letters + string.digits + "_\\/:"
        
    if not os.path.exists(dtm_path):
        raise typer.Exit("Not a valid path to the input DTM provided.")
    
    if not os.path.isfile(dtm_path):
        raise typer.Exit("Input path does appaer to be a valid file.")
    
    if os.path.exists(out_dir):
        raise typer.Exit("%s already exists." % (out_dir))
    
    spec_chars = list(set(out_dir).difference(allowed_characters))
    if len(spec_chars) > 0:
        raise typer.Exit("The output directory contains special characters: %s" % ",".join(spec_chars))
    
    spec_chars = list(set(out_name).difference(allowed_characters))
    if len(spec_chars) > 0:
        raise typer.Exit("The output name contains special characters: %s" % ",".join(spec_chars))
    
    print("Starting to create mesh tiles:")
    tile_grid = MeshGrid(path=dtm_path, tile_size=tile_size, max_error=max_error, method=method, extent=extent)
    
    print("...snapping vertices along tile boundaries.")
    tile_grid.snap_boundaries()
    
    out_dir = os.path.normpath(out_dir)
    
    print("...saving tiles to %s." % (out_dir))
    tile_grid.save_tiles(odir=out_dir, oname=out_name)
    
@app.command()
def add_ortho(op_path:Annotated[str, typer.Argument()],
              json_path:Annotated[str, typer.Argument()],
              op_res:Annotated[int, typer.Option()] = 1
              ):
    
    print("Starting to create orthophoto tiles:")
    print("...loading %s." % (op_path))
    op_data = gdal.Open(op_path)
    
    op_proj = osr.SpatialReference(wkt=op_data.GetProjection())
    op_epsg = op_proj.GetAttrValue('AUTHORITY', 1)
        
    with open(json_path, "r") as f:
        tiles_data = json.load(f)   
    tiles_epsg = tiles_data["epsg"]    
    
    op_dir = os.path.join(os.path.dirname(json_path), "op")
    if not os.path.exists(op_dir):
        os.makedirs(op_dir)    
    
    for tile in track(tiles_data["tiles"], description="Creating OP tiles..."):
        tid = tile["tid"]
        out_path = os.path.join(op_dir, "%s.jpg" % (tid))
        
        min_xyz = tile["min_xyz"]
        max_xyz = tile["max_xyz"]
        
        bbox = [min_xyz[0], min_xyz[1], max_xyz[0], max_xyz[1]]
        
        out_srs = osr.SpatialReference()
        out_srs.ImportFromEPSG(int(tiles_epsg))
        
        inp_srs = osr.SpatialReference()
        inp_srs.ImportFromEPSG(int(op_epsg))
        
        kwargs = {'format': 'JPEG', 
                'outputBounds':bbox,
                'outputBoundsSRS':out_srs,
                'srcSRS':inp_srs,
                'dstSRS':out_srs,
                'xRes':op_res, 
                'yRes':op_res,
                'resampleAlg':'bilinear'}
        ds = gdal.Warp(out_path, op_path, **kwargs)
        del ds    
    
if __name__ == "__main__":
    app()