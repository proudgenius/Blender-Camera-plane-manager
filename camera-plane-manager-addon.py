bl_info = {
    "name": "Camera Plane Manager",
    "author": "Cristian Omar Jimenez",
    "version": (1, 1, 0),
    "blender": (4, 0, 0),
    "location": "Properties > Object > Camera Plane",
    "description": "Import and manage camera-aligned image planes with distance controls",
    "warning": "",
    "doc_url": "https://github.com/proudgenius/Blender-Camera-plane-manager",
    "category": "Camera",
}

import bpy
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, CollectionProperty, FloatProperty, BoolProperty
import os


def update_distance(self, context):
    # Update the empty's position if it exists
    if "distance_empty" in self:
        empty = self["distance_empty"]
        if empty:
            empty.location.y = self["camera_plane_distance"]


def ensure_addon_enabled():
    """Make sure the 'Import Images as Planes' addon is enabled"""
    import addon_utils
    addon_name = "io_import_images_as_planes"
    
    # Try to enable the addon
    loaded_default, loaded_state = addon_utils.check(addon_name)
    if not loaded_state:
        addon_utils.enable(addon_name, default_set=True)


class CAMERA_OT_Simple_Camera_Plane(bpy.types.Operator, ImportHelper):
    """Import images as camera-aligned planes"""
    bl_idname = "camera.simple_camera_plane"
    bl_label = "Import Camera Plane"
    bl_options = {'REGISTER', 'UNDO'}

    # File selection properties
    files: CollectionProperty(
        type=bpy.types.OperatorFileListElement,
        options={'HIDDEN', 'SKIP_SAVE'}
    )
    directory: StringProperty(
        maxlen=1024,
        subtype='FILE_PATH',
        options={'HIDDEN', 'SKIP_SAVE'}
    )

    # File filter properties
    filter_image: BoolProperty(default=True, options={'HIDDEN', 'SKIP_SAVE'})
    filter_movie: BoolProperty(default=True, options={'HIDDEN', 'SKIP_SAVE'})
    filter_folder: BoolProperty(default=True, options={'HIDDEN', 'SKIP_SAVE'})

    # Add empty object control
    use_empty_control: BoolProperty(
        name='Use Empty for Distance',
        description='Create an empty object to control distance visually',
        default=False
    )

    scale: FloatProperty(
        name='Scale',
        description='Scale applied after calculation',
        default=100.0,
        soft_min=0,
        soft_max=500,
        min=0,
        subtype='PERCENTAGE'
    )
    
    distance: FloatProperty(
        name='Distance',
        description='Distance from camera to plane',
        default=10.0,
        soft_max=1000,
        min=0,
        subtype='DISTANCE',
        unit='LENGTH'
    )

    @classmethod
    def poll(cls, context):
        if context.active_object is not None and context.active_object.type == 'CAMERA':
            return True
        cls.poll_message_set("Active object must be a camera")
        return False

    def execute(self, context):
        # Get active camera
        cam = context.active_object

        for f in self.files:
            # Import image as plane
            bpy.ops.image.import_as_mesh_planes(
                files=[{"name": f.name}],
                directory=self.directory,
                use_transparency=True,
                shader='SHADELESS',
                overwrite_material=False
            )
            
            plane = context.active_object

            # Move plane to camera's collections
            for coll in plane.users_collection:
                coll.objects.unlink(plane)
            for coll in cam.users_collection:
                coll.objects.link(plane)

            # Scale normalization
            scale_factor = plane.dimensions[0]
            for v in plane.data.vertices:
                v.co /= scale_factor

            # Setup plane
            plane.parent = cam
            plane.matrix_world = cam.matrix_world
            plane.show_wire = True
            plane.lock_location = (True,) * 3
            plane.lock_rotation = (True,) * 3
            plane.lock_scale = (True,) * 3

            # Create distance control empty if requested
            if self.use_empty_control:
                empty = bpy.data.objects.new(f"{plane.name}_distance", None)
                empty.empty_display_type = 'PLAIN_AXES'
                empty.empty_display_size = 0.5
                
                # Place empty at camera's current location
                empty.location = cam.matrix_world.translation.copy()
                
                # Link empty to same collections as camera
                for coll in cam.users_collection:
                    coll.objects.link(empty)
                
                # Store reference to empty in plane
                plane["distance_empty"] = empty
                
                # Add driver to update distance from empty
                driver = plane.driver_add('["camera_plane_distance"]')
                driver.driver.type = 'SCRIPTED'
                
                # Add camera location variable
                var = driver.driver.variables.new()
                var.name = "cam_loc"
                var.type = 'TRANSFORMS'
                var.targets[0].id = cam
                var.targets[0].transform_type = 'LOC_Y'
                var.targets[0].transform_space = 'WORLD_SPACE'
                
                # Add empty location variable
                var = driver.driver.variables.new()
                var.name = "empty_loc"
                var.type = 'TRANSFORMS'
                var.targets[0].id = empty
                var.targets[0].transform_type = 'LOC_Y'
                var.targets[0].transform_space = 'WORLD_SPACE'
                
                # Expression calculates distance between camera and empty
                driver.driver.expression = "abs(empty_loc - cam_loc)"
                
                # Move empty to achieve initial distance
                empty.location.y = cam.matrix_world.translation.y + self.distance

            # Add custom properties
            plane["camera_plane_distance"] = self.distance
            plane["camera_plane_scale"] = self.scale

            # Setup drivers
            # X and Y position drivers (for camera shift)
            for axis in range(2):
                driver = plane.driver_add('location', axis)
                driver.driver.type = 'SCRIPTED'

                # Distance variable
                var = driver.driver.variables.new()
                var.name = "distance"
                var.type = 'SINGLE_PROP'
                var.targets[0].id = plane
                var.targets[0].data_path = '["camera_plane_distance"]'

                # FOV variable
                var = driver.driver.variables.new()
                var.name = "FOV"
                var.type = 'SINGLE_PROP'
                var.targets[0].id = cam
                var.targets[0].data_path = 'data.angle'

                # Shift variable
                var = driver.driver.variables.new()
                var.name = "shift"
                var.type = 'SINGLE_PROP'
                var.targets[0].id = cam
                var.targets[0].data_path = f'data.shift_{"x" if axis == 0 else "y"}'

                # Expression for shift compensation
                driver.driver.expression = "tan(FOV/2) * distance*2 * shift"

            # Z position driver (distance from camera)
            driver = plane.driver_add('location', 2)
            driver.driver.type = 'SCRIPTED'
            
            var = driver.driver.variables.new()
            var.name = "distance"
            var.type = 'SINGLE_PROP'
            var.targets[0].id = plane
            var.targets[0].data_path = '["camera_plane_distance"]'
            
            driver.driver.expression = "-distance"

            # Scale drivers
            for axis in range(2):
                driver = plane.driver_add('scale', axis)
                driver.driver.type = 'SCRIPTED'

                # Distance variable
                var = driver.driver.variables.new()
                var.name = "distance"
                var.type = 'SINGLE_PROP'
                var.targets[0].id = plane
                var.targets[0].data_path = '["camera_plane_distance"]'

                # FOV variable
                var = driver.driver.variables.new()
                var.name = "FOV"
                var.type = 'SINGLE_PROP'
                var.targets[0].id = cam
                var.targets[0].data_path = 'data.angle'

                # Scale variable
                var = driver.driver.variables.new()
                var.name = "scale"
                var.type = 'SINGLE_PROP'
                var.targets[0].id = plane
                var.targets[0].data_path = '["camera_plane_scale"]'

                # Expression for scale
                driver.driver.expression = "tan(FOV/2) * distance*2 * scale/100.0"

        return {'FINISHED'}


class CAMERA_OT_Add_Empty_Control(bpy.types.Operator):
    """Add an empty object to control the plane's distance"""
    bl_idname = "camera.add_empty_control"
    bl_label = "Add Empty Control"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        plane = context.active_object
        cam = plane.parent

        if not cam or cam.type != 'CAMERA':
            self.report({'ERROR'}, "Selected object must be a camera plane")
            return {'CANCELLED'}

        # Create empty
        empty = bpy.data.objects.new(f"{plane.name}_distance", None)
        empty.empty_display_type = 'PLAIN_AXES'
        empty.empty_display_size = 0.5

        # Get the camera's world position accounting for full hierarchy
        cam_world_pos = cam.matrix_world.translation.copy()
        
        # Place empty at camera's world position
        empty.location = cam_world_pos
        
        # Link empty to same collections as camera
        for coll in cam.users_collection:
            coll.objects.link(empty)

        # Store reference to empty in plane
        plane["distance_empty"] = empty
        
        # Add driver to update distance from empty
        driver = plane.driver_add('["camera_plane_distance"]')
        driver.driver.type = 'SCRIPTED'
        
        # Get full camera world matrix
        var = driver.driver.variables.new()
        var.name = "cam_mat"
        var.type = 'TRANSFORMS'
        var.targets[0].id = cam
        var.targets[0].transform_type = 'LOC_Y'
        var.targets[0].transform_space = 'WORLD_SPACE'

        # Add empty location variable
        var = driver.driver.variables.new()
        var.name = "empty_loc"
        var.type = 'TRANSFORMS'
        var.targets[0].id = empty
        var.targets[0].transform_type = 'LOC_Y'
        var.targets[0].transform_space = 'WORLD_SPACE'

        # Add camera scale variable
        var = driver.driver.variables.new()
        var.name = "cam_scale"
        var.type = 'TRANSFORMS'
        var.targets[0].id = cam
        var.targets[0].transform_type = 'SCALE_Y'
        var.targets[0].transform_space = 'WORLD_SPACE'
        
        # Expression accounts for camera scale when calculating distance
        driver.driver.expression = "abs(empty_loc - cam_mat) * (1/cam_scale)"
        
        # Move empty to achieve initial distance, accounting for camera scale
        empty.location.y = cam_world_pos.y + (plane["camera_plane_distance"] * cam.scale.y)

        return {'FINISHED'}


class CAMERA_OT_Remove_Empty_Control(bpy.types.Operator):
    """Remove the empty object controlling the plane's distance"""
    bl_idname = "camera.remove_empty_control"
    bl_label = "Remove Empty Control"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        plane = context.active_object
        
        if "distance_empty" in plane and plane["distance_empty"]:
            empty = plane["distance_empty"]
            
            # Remove driver
            if plane.animation_data:
                plane.driver_remove('["camera_plane_distance"]')
            
            # Remove empty
            bpy.data.objects.remove(empty, do_unlink=True)
            del plane["distance_empty"]
        
        return {'FINISHED'}


class CAMERA_PT_Simple_Camera_Plane(bpy.types.Panel):
    """Panel for camera plane operations"""
    bl_label = "Camera Plane"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    @classmethod
    def poll(cls, context):
        # Only show panel for cameras or camera-aligned planes
        obj = context.active_object
        if obj is None:
            return False
        return (obj.type == "CAMERA" or 
                (obj.parent is not None and 
                 obj.parent.type == "CAMERA" and 
                 "camera_plane_distance" in obj))

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        # Import button for cameras
        if obj.type == "CAMERA":
            layout.operator("camera.simple_camera_plane", icon='FILE_IMAGE')
        
        # Distance and scale controls for planes
        elif "camera_plane_distance" in obj:
            col = layout.column(align=True)
            col.use_property_split = True
            col.use_property_decorate = False
            
            # Empty control toggle
            row = col.row(align=True)
            if "distance_empty" in obj and obj["distance_empty"]:
                row.operator("camera.remove_empty_control", text="Remove Empty Control", icon='X')
            else:
                row.operator("camera.add_empty_control", text="Add Empty Control", icon='EMPTY_AXIS')
            
            col.separator()
            
            # Distance and scale properties
            col.prop(obj, "camera_plane_distance")
            col.prop(obj, "camera_plane_scale")


classes = (
    CAMERA_OT_Simple_Camera_Plane,
    CAMERA_OT_Add_Empty_Control,
    CAMERA_OT_Remove_Empty_Control,
    CAMERA_PT_Simple_Camera_Plane,
)


def register():
    # Ensure required addon is enabled
    ensure_addon_enabled()
    
    # Register custom properties
    bpy.types.Object.camera_plane_distance = bpy.props.FloatProperty(
        name="Distance",
        description="Distance from the camera",
        default=10.0,
        min=0,
        soft_max=1000,
        subtype='DISTANCE',
        unit='LENGTH',
        update=update_distance
    )
    
    bpy.types.Object.camera_plane_scale = bpy.props.FloatProperty(
        name="Scale",
        description="Scale applied after distance calculation",
        default=100.0,
        min=0,
        soft_max=500,
        subtype='PERCENTAGE'
    )

    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Object.camera_plane_distance
    del bpy.types.Object.camera_plane_scale


if __name__ == "__main__":
    register()
