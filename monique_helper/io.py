import os
import json
import numpy as np
import open3d as o3d
import pygfx as gfx
from osgeo import gdal, osr
import glob

def load_tile_json(json_path):
    
    with open(json_path, "r") as f:
        tiles_data = json.load(f)
        tiles_data["tile_dir"] = os.path.join(os.path.dirname(json_path), "mesh")
        tiles_data["op_dir"] = os.path.join(os.path.dirname(json_path), "op")
        
    return tiles_data

def load_gtif(path):
    ds = gdal.Open(path)
    
    ds_gt = ds.GetGeoTransform()
    ds_proj = ds.GetProjection()
    
    b1 = ds.GetRasterBand(1)
    b2 = ds.GetRasterBand(2)
    b3 = ds.GetRasterBand(3)
    b1_arr = b1.ReadAsArray()
    b2_arr = b2.ReadAsArray()
    b3_arr = b3.ReadAsArray()
    
    arr = np.dstack((b1_arr, b2_arr, b3_arr))
        
    return arr, ds_gt, ds_proj

def save_png(arr, path, proj=None, gt=None):
    arr_h, arr_w, arr_d = np.shape(np.atleast_3d(arr))
    
    driver = gdal.GetDriverByName("MEM")
    outdata = driver.Create(path, arr_w, arr_h, arr_d, gdal.GDT_Byte)
    
    if gt is not None:
        outdata.SetGeoTransform(gt) ##sets same geotransform as input
    
    if proj is not None:
        outdata.SetProjection(proj) ##sets same projection as input
        
    for b in range(arr_d):
        outdata.GetRasterBand(b+1).WriteArray(arr[:, :, b])
        # outdata.GetRasterBand(b+1).SetNoDataValue(nd) 
    
    png_driver = gdal.GetDriverByName('PNG')
    png_driver.CreateCopy(path, outdata)

    
    # outdata.FlushCache()
    # outdata = None

def save_tif(arr, path, proj=None, gt=None, nd=-9999):
    
    # https://borealperspectives.org/2014/01/16/data-type-mapping-when-using-pythongdal-to-write-numpy-arrays-to-geotiff/
    NP2GDAL_CONVERSION = {
        "uint8": 1,
        "int8": 1,
        "uint16": 2,
        "int16": 3,
        "uint32": 4,
        "int32": 5,
        "float32": 6,
        "float64": 7,
        "complex64": 10,
        "complex128": 11}
    
    arr = np.nan_to_num(arr, nan=nd, posinf=nd, neginf=nd)
    
    arr_h, arr_w, arr_d = np.shape(np.atleast_3d(arr))
    arr_gdaltype = NP2GDAL_CONVERSION[arr.dtype.name]
    
    driver = gdal.GetDriverByName("GTiff")
    outdata = driver.Create(path, arr_w, arr_h, arr_d, arr_gdaltype, options=['COMPRESS=DEFLATE'])
    
    if gt is not None:
        outdata.SetGeoTransform(gt) ##sets same geotransform as input
    
    if proj is not None:
        outdata.SetProjection(proj) ##sets same projection as input
        
    for b in range(arr_d):
        outdata.GetRasterBand(b+1).WriteArray(arr[:, :, b])
        outdata.GetRasterBand(b+1).SetNoDataValue(nd) 
    outdata.FlushCache()
    outdata = None

def load_terrain(tiles_data):
    
    o3d_scene = o3d.t.geometry.RaycastingScene()
    terrain = gfx.Group()
   
    for tile in tiles_data["tiles"]:
        tile["op"] = {}
        tile_path = os.path.join(tiles_data["tile_dir"], "%s.ply" % (tile["tid"]))
        tile_mesh = o3d.io.read_triangle_mesh(tile_path)

        verts = np.asarray(tile_mesh.vertices).astype(np.float32)
        
        u = (verts[:, 0] - tile["min_xyz"][0])/(tile["max_xyz"][0] - tile["min_xyz"][0])
        v = (verts[:, 1] - tile["min_xyz"][1])/(tile["max_xyz"][1] - tile["min_xyz"][1])
        uv = np.hstack((u.reshape(-1, 1), v.reshape(-1, 1)))
        
        # verts -= self.min_xyz
        faces = np.asarray(tile_mesh.triangles).astype(np.uint32)       
        verts -= np.array(tiles_data["min_xyz"])
        
        o3d_scene.add_triangles(verts, faces)
                         
        mesh_geom = gfx.geometries.Geometry(indices=faces, 
                                            positions=verts.astype(np.float32),
                                            texcoords=uv.astype(np.float32),
                                            tid=[int(tile["tid_int"])])
        

        # op_path = os.path.join(tiles_data["op_dir"], "%s.jpg" % (tile["tid"]))
        op_paths = glob.glob(os.path.normpath(os.path.join(tiles_data["op_dir"], "%s.*" % (tile["tid"]))))
        
        if len(op_paths) == 1:
            op_path = op_paths[0]            
            img_arr, _ , _ = load_gtif(op_path)   
            img_arr = np.flipud(img_arr)
            
            tex = gfx.Texture(img_arr, dim=2)
            mesh_material = gfx.MeshBasicMaterial(map=tex, side="FRONT")
        else:
            mesh_material = gfx.MeshNormalMaterial(side="FRONT")
            
        #add lowest resolution material to mesh at startup
        mesh = gfx.Mesh(mesh_geom, mesh_material, visible=True)
        terrain.add(mesh)
        
    return terrain, o3d_scene