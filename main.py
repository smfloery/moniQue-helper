import typer
from typing_extensions import Annotated
from rich.progress import track
import os
from enum import Enum
from monique_helper.terramesh import MeshGrid
from monique_helper.io import load_tile_json, load_terrain, save_tif, save_png
from monique_helper.transforms import alzeka2rot, R_ori2cv
from osgeo import gdal, osr
import json
import string
import numpy as np
import pygfx as gfx
from wgpu.gui.offscreen import WgpuCanvas
import open3d as o3d

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
def add_ortho(op_path:Annotated[str, typer.Argument(help="Parth to the original orthophoto.")],
              json_path:Annotated[str, typer.Argument(help="Path to the *.json created by create-mesh.")],
              op_res:Annotated[int, typer.Option(help="Output resolution of the orthophoto tiles.")] = 1
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

@app.command()
def render_json(camera_json:Annotated[str, typer.Argument(help="Path to the *.json containing the camera parameters.")],
                tiles_json:Annotated[str, typer.Argument(help="Path to the *.json created with create-mesh.")],
                out_dir:Annotated[str, typer.Argument(help="Path to the directory where the outputs shall be stored.")],
                xyz:Annotated[bool, typer.Option(help="If additional image with the xyz-coordinates of the scene shall be created.")] = True):
           
    gfx_scene = gfx.Scene()
    bg = gfx.Background(None, gfx.BackgroundMaterial([1, 1, 1, 1]))
    gfx_scene.add(bg)
    
    print("Loading terrain...")
    tiles_data = load_tile_json(tiles_json)
    gfx_terrain, o3d_scene = load_terrain(tiles_data)
    gfx_scene.add(gfx_terrain)
      
    with open(camera_json, "r") as json_file:
        cam_data = json.load(json_file)   
    
    for name, data in cam_data.items():
        
        print("...rendering %s." % (name))
        
        cam_w = data["img_w"]
        cam_h = data["img_h"]
        
        offscreen_canvas = WgpuCanvas(size=(cam_w, cam_h), pixel_ratio=1)
        offscreen_renderer = gfx.WgpuRenderer(offscreen_canvas, pixel_ratio=1)            
        
        euler = np.array([data["alpha"], data["zeta"], data["kappa"]])
        rmat = alzeka2rot(euler)
        rmat_gfx = np.zeros((4,4))
        rmat_gfx[3, 3] = 1
        rmat_gfx[:3, :3] = rmat
        
        # we adjust the fov of the camera the the larger side of the image matches the fov
        if cam_h > cam_w:
            cam_fov = data["fov"]
            gfx_camera = gfx.PerspectiveCamera(fov=np.rad2deg(cam_fov), 
                                               depth_range=(1, 100000))
        else:
            cam_fov = data["fov"] * (cam_h / cam_w)
            gfx_camera = gfx.PerspectiveCamera(fov=np.rad2deg(cam_fov), #we adjust the vfov of the camera that it matches the extent of the image
                                               depth_range=(1, 100000))
        
        prc_local = np.array([data["X0"], data["Y0"], data["Z0"]]) - np.array(tiles_data["min_xyz"])
        gfx_camera.local.position = prc_local
        gfx_camera.local.rotation_matrix = rmat_gfx
            
        offscreen_canvas.request_draw(offscreen_renderer.render(gfx_scene, gfx_camera))    
        img_scene_arr = np.asarray(offscreen_canvas.draw())[:,:,:3]
        
        save_png(img_scene_arr, os.path.join(out_dir, name + ".png"))
                
        if xyz:
            
            print("...generating depth image.")
            
            # I HAVE NO IDEA WHY? Otherwise, using the same focal lenght, for images in portrait mode the depth image is completely off
            if cam_h > cam_w:
                cam_f = (cam_w/2.)/np.tan(cam_fov/2.)   #we use height as fov of pygfx equals the vertical field of view
            else:
                cam_f = (cam_h/2.)/np.tan(cam_fov/2.)
            
            cam_rot_cv = R_ori2cv(rmat)
            cam_tvec = np.matmul(cam_rot_cv*(-1), prc_local.reshape(3, 1))
            cam_rot_cv_tvec = np.vstack((np.concatenate([cam_rot_cv, cam_tvec], axis=-1), np.array([0, 0, 0, 1])))
            cam_o3d_extrinsic = o3d.core.Tensor(cam_rot_cv_tvec.astype(np.float32))

            cam_o3d_intrinsic = o3d.camera.PinholeCameraIntrinsic(cam_w, cam_h, 
                                                                  cam_f, cam_f,
                                                                  cam_w/2., cam_h/2.)
        
    
            rays = o3d_scene.create_rays_pinhole(intrinsic_matrix=cam_o3d_intrinsic.intrinsic_matrix, 
                                                 extrinsic_matrix=cam_o3d_extrinsic, 
                                                 width_px=cam_w, 
                                                 height_px=cam_h)
            rays = rays.reshape((cam_w*cam_h, 6))
            
            ans = o3d_scene.cast_rays(rays)
            ans_coord = rays[:,:3] + rays[:,3:]*ans['t_hit'].reshape((-1,1))
            ans_coord = ans_coord.numpy().reshape(-1, 3)
            ans_coord += np.array(tiles_data["min_xyz"])
            
            coord_arr = np.reshape(ans_coord, (cam_h, cam_w, 3))
            save_tif(coord_arr, os.path.join(out_dir, name + "_xyz.tif"))
            
if __name__ == "__main__":
    app()