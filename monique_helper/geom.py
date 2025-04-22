import numpy as np
import pygfx as gfx
from monique_helper.transforms import alzeka2rot
from PIL import Image

def plane_from_camera(cam, img, dist_plane=100, min_xyz = None):
    cmat = np.array([[1, 0, -cam["img_x0"]], 
                    [0, 1, -cam["img_y0"]],
                    [0, 0, -cam["f"]]])
    
    rmat = alzeka2rot([cam["alpha"], cam["zeta"], cam["kappa"]])
    prc_local = np.array([cam["obj_x0"], cam["obj_y0"], cam["obj_z0"]]) - min_xyz

    plane_pnts_img = np.array([[0, 0, 1],
                        [cam["img_w"], 0, 1],
                        [cam["img_w"], cam["img_h"]*(-1), 1],
                        [0, cam["img_h"]*(-1), 1]]).T
    
    plane_pnts_dir = (rmat@cmat@plane_pnts_img).T
    plane_pnts_dir = plane_pnts_dir / np.linalg.norm(plane_pnts_dir, axis=1).reshape(-1, 1)
    
    plane_pnts_obj = prc_local + dist_plane * plane_pnts_dir
    plane_faces = np.array([[3, 1, 0], [3, 2, 1]]).astype(np.uint32)
    plane_uv = np.array([[0, 0], [1, 0], [1, 1], [0, 1]]).astype(np.uint32)
    
    plane_geom = gfx.geometries.Geometry(indices=plane_faces, 
                                        positions=plane_pnts_obj.astype(np.float32),
                                        texcoords=plane_uv.astype(np.float32))
    
    # img_array = np.asarray(img)
    tex = gfx.Texture(img, dim=2)
    
    plane_material = gfx.MeshBasicMaterial(map=tex, side="FRONT")
    plane_mesh = gfx.Mesh(plane_geom, plane_material, visible=True)
    return plane_mesh

def img2square(pil_img, background_color):
    width, height = pil_img.size
    if width == height:
        return pil_img
    elif width > height:
        result = Image.new(pil_img.mode, (width, width), background_color)
        result.paste(pil_img, (0, (width - height) // 2))
        return result
    else:
        result = Image.new(pil_img.mode, (height, height), background_color)
        result.paste(pil_img, ((height - width) // 2, 0))
        return result