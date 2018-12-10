# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>

# ----------------------------------------------------------
# support routines for render measures in final image
# Author: Antonio Vazquez (antonioya)
#
# ----------------------------------------------------------
# noinspection PyUnresolvedReferences
import bpy
# noinspection PyUnresolvedReferences
import bgl
# noinspection PyUnresolvedReferences
import blf
from os import path, remove
from sys import exc_info
# noinspection PyUnresolvedReferences
import bpy_extras.image_utils as img_utils
# noinspection PyUnresolvedReferences
import bpy_extras.object_utils as object_utils
# noinspection PyUnresolvedReferences
from bpy_extras import view3d_utils
from math import ceil
from .measureit_geometry import *


# -------------------------------------------------------------
# Render image main entry point
#
# -------------------------------------------------------------
def render_main(self, context, animation=False):
    # Save old info
    settings = bpy.context.scene.render.image_settings
    depth = settings.color_depth
    settings.color_depth = '8'
    # noinspection PyBroadException
   # Get object list
    scene = context.scene
    objlist = context.scene.objects
    # --------------------
    # Get resolution
    # --------------------
    render_scale = scene.render.resolution_percentage / 100
    width = int(scene.render.resolution_x * render_scale)
    height = int(scene.render.resolution_y * render_scale)

    # --------------------------------------
    # Loop to draw all lines in Offsecreen
    # --------------------------------------
    offscreen = gpu.types.GPUOffScreen(width, height)
    view_matrix = Matrix([
        [2 / width, 0, 0, -1],
        [0, 2 / height, 0, -1],
        [0, 0, 1, 0],
        [0, 0, 0, 1]])

    with offscreen.bind():
        bgl.glClear(bgl.GL_COLOR_BUFFER_BIT)
        gpu.matrix.reset()
        gpu.matrix.load_matrix(view_matrix)
        gpu.matrix.load_projection_matrix(Matrix.Identity(4))

        # -----------------------------
        # Loop to draw all objects
        # -----------------------------
        for myobj in objlist:
            if myobj.visible_get() is True:
                if 'MeasureGenerator' in myobj:
                    op = myobj.MeasureGenerator[0]
                    draw_segments(context, myobj, op, None, None)
        # -----------------------------
        # Loop to draw all debug
        # -----------------------------
        if scene.measureit_debug is True:
            selobj = bpy.context.selected_objects
            for myobj in selobj:
                if scene.measureit_debug_objects is True:
                    draw_object(context, myobj, None, None)
                elif scene.measureit_debug_object_loc is True:
                    draw_object(context, myobj, None, None)
                if scene.measureit_debug_vertices is True:
                    draw_vertices(context, myobj, None, None)
                elif scene.measureit_debug_vert_loc is True:
                    draw_vertices(context, myobj, None, None)
                if scene.measureit_debug_edges is True:
                    draw_edges(context, myobj, None, None)
                if scene.measureit_debug_faces is True or scene.measureit_debug_normals is True:
                    draw_faces(context, myobj, None, None)
        # -----------------------------
        # Draw a rectangle frame
        # -----------------------------
        if scene.measureit_rf is True:
            rfcolor = scene.measureit_rf_color
            rfborder = scene.measureit_rf_border
            rfline = scene.measureit_rf_line

            bgl.glLineWidth(rfline)
            x1 = rfborder
            x2 = width - rfborder
            y1 = int(ceil(rfborder / (width / height)))
            y2 = height - y1
            draw_rectangle((x1, y1), (x2, y2))

        buffer = bgl.Buffer(bgl.GL_BYTE, width * height * 4)
        bgl.glReadBuffer(bgl.GL_COLOR_ATTACHMENT0)
        bgl.glReadPixels(0, 0, width, height, bgl.GL_RGBA, bgl.GL_UNSIGNED_BYTE, buffer)

    offscreen.free()

    # -----------------------------
    # Create image
    # -----------------------------
    image_name = "measureit_output"
    if not image_name in bpy.data.images:
        bpy.data.images.new(image_name, width, height)

    image = bpy.data.images[image_name]
    image.scale(width, height)
    image.pixels = [v / 255 for v in buffer]

    # Saves image
    if image is not None and (scene.measureit_render is True or animation is True):
        ren_path = bpy.context.scene.render.filepath
        filename = "mit_frame"
        if len(ren_path) > 0:
            if ren_path.endswith(path.sep):
                initpath = path.realpath(ren_path) + path.sep
            else:
                (initpath, filename) = path.split(ren_path)

        ftxt = "%04d" % scene.frame_current
        outpath = path.realpath(path.join(initpath, filename + ftxt + ".png"))
        save_image(self, outpath, image)

    # restore default value
    settings.color_depth = depth


# --------------------------------------------------------------------
# Get the final render image and return as image object
#
# return None if no render available
# --------------------------------------------------------------------
def get_render_image(outpath):
    saved = False
    # noinspection PyBroadException
    try:
        # noinspection PyBroadException
        try:
            result = bpy.data.images['Render Result']
            if result.has_data is False:
                # this save produce to fill data image
                result.save_render(outpath)
                saved = True
        except:
            print("No render image found")
            return None

        # Save and reload
        if saved is False:
            result.save_render(outpath)

        img = img_utils.load_image(outpath)

        return img
    except:
        print("Unexpected render image error")
        return None


# -------------------------------------
# Save image to file
# -------------------------------------
def save_image(self, filepath, myimage):
    # noinspection PyBroadException
    try:

        # Save old info
        settings = bpy.context.scene.render.image_settings
        myformat = settings.file_format
        mode = settings.color_mode
        depth = settings.color_depth

        # Apply new info and save
        settings.file_format = 'PNG'
        settings.color_mode = "RGBA"
        settings.color_depth = '8'
        myimage.save_render(filepath)
        print("MeasureIt: Image " + filepath + " saved")

        # Restore old info
        settings.file_format = myformat
        settings.color_mode = mode
        settings.color_depth = depth
    except:
        print("Unexpected error:" + str(exc_info()))
        self.report({'ERROR'}, "MeasureIt: Unable to save render image")
        return
