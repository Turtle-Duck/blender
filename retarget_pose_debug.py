import bpy
from mathutils import Matrix, Vector
from math import acos


#########################################
## "Visual Transform" helper functions ##
#########################################

def get_pose_matrix_in_other_space(mat, pose_bone):
    """ Returns the transform matrix relative to pose_bone's current
        transform space.  In other words, presuming that mat is in
        armature space, slapping the returned matrix onto pose_bone
        should give it the armature-space transforms of mat.
        TODO: try to handle cases with axis-scaled parents better.
    """
    rest = pose_bone.bone.matrix_local.copy()
    rest_inv = rest.inverted()
    if pose_bone.parent:
        par_mat = pose_bone.parent.matrix.copy()
        par_inv = par_mat.inverted()
        par_rest = pose_bone.parent.bone.matrix_local.copy()
    else:
        par_mat = Matrix()
        par_inv = Matrix()
        par_rest = Matrix()

    # Get matrix in bone's current transform space
    smat = rest_inv @ (par_rest @ (par_inv @ mat))

    # Compensate for non-local location
    #if not pose_bone.bone.use_local_location:
    #    loc = smat.to_translation() * (par_rest.inverted() * rest).to_quaternion()
    #    smat.translation = loc

    return smat


def get_local_pose_matrix(pose_bone):
    """ Returns the local transform matrix of the given pose bone.
    """
    return get_pose_matrix_in_other_space(pose_bone.matrix, pose_bone)


def set_pose_translation(pose_bone, mat):
    """ Sets the pose bone's translation to the same translation as the given matrix.
        Matrix should be given in bone's local space.
    """
    if pose_bone.bone.use_local_location == True:
        pose_bone.location = mat.to_translation()
    else:
        loc = mat.to_translation()

        rest = pose_bone.bone.matrix_local.copy()
        if pose_bone.bone.parent:
            par_rest = pose_bone.bone.parent.matrix_local.copy()
        else:
            par_rest = Matrix()

        q = (par_rest.inverted() * rest).to_quaternion()
        pose_bone.location = q * loc


def set_pose_rotation(pose_bone, mat):
    """ Sets the pose bone's rotation to the same rotation as the given matrix.
        Matrix should be given in bone's local space.
    """
    q = mat.to_quaternion()

    if pose_bone.rotation_mode == 'QUATERNION':
        pose_bone.rotation_quaternion = q
    elif pose_bone.rotation_mode == 'AXIS_ANGLE':
        pose_bone.rotation_axis_angle[0] = q.angle
        pose_bone.rotation_axis_angle[1] = q.axis[0]
        pose_bone.rotation_axis_angle[2] = q.axis[1]
        pose_bone.rotation_axis_angle[3] = q.axis[2]
    else:
        pose_bone.rotation_euler = q.to_euler(pose_bone.rotation_mode)


def set_pose_scale(pose_bone, mat):
    """ Sets the pose bone's scale to the same scale as the given matrix.
        Matrix should be given in bone's local space.
    """
    pose_bone.scale = mat.to_scale()


def match_pose_translation(pose_bone, target_bone):
    """ Matches pose_bone's visual translation to target_bone's visual
        translation.
        This function assumes you are in pose mode on the relevant armature.
    """
    mat = get_pose_matrix_in_other_space(target_bone.matrix, pose_bone)
    set_pose_translation(pose_bone, mat)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.mode_set(mode='POSE')


def match_pose_rotation(pose_bone, target_bone):
    """ Matches pose_bone's visual rotation to target_bone's visual
        rotation.
        This function assumes you are in pose mode on the relevant armature.
    """
    mat = get_pose_matrix_in_other_space(target_bone.matrix, pose_bone)
    set_pose_rotation(pose_bone, mat)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.mode_set(mode='POSE')


def match_pose_scale(pose_bone, target_bone):
    """ Matches pose_bone's visual scale to target_bone's visual
        scale.
        This function assumes you are in pose mode on the relevant armature.
    """
    mat = get_pose_matrix_in_other_space(target_bone.matrix, pose_bone)
    set_pose_scale(pose_bone, mat)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.mode_set(mode='POSE')



##############
## Operator ##
##############


class CreateRestPoseRig(bpy.types.Operator):
    """ Creates a new set of bones with current pose as rest pose
    """
    bl_idname = "anim.target_pose"
    bl_label = "New Rest Pose to Rig"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object != None)

    def execute(self, context):
        ###################################################
        # dupe rig
        # for copy
        # add prop to point to original bone
        # make current pose the rest pose
        # join to original
        ####################################################

        scene = context.scene

        # original bvh rig
        bvhrig = context.active_object

        bpy.ops.object.mode_set() # object mode
        bpy.ops.object.duplicate()
        ob = context.object
        print("DUPE", ob)
         
        #add a custom prop for each bone in the copy

        for bone in ob.pose.bones:
            bone['bvh'] = bone.name

        # apply the pose as rest pose
        bpy.ops.object.mode_set(mode='POSE')

        bpy.ops.pose.armature_apply()

        bpy.ops.object.mode_set(mode='OBJECT')
            
        # join back to original
        ob.select_set(True)
        context.view_layer.objects.active = bvhrig
        bvhrig.select_set(True)

        bpy.ops.object.join()

        return {'FINISHED'}




class UpdateAction(bpy.types.Operator):
    """ Creates a new set of bones with current pose as rest pose
    """
    bl_idname = "anim.update_action"
    bl_label = "BVH action to new restpose rig"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object != None)

    def execute(self, context):
        scene = context.scene
        TOL = 0.005
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        ###########################################
        # action part
        ###########################################
        
        bvhrig = context.view_layer.objects.active
        
        action = bvhrig.animation_data.action
        
        newbones = [bone for bone in bvhrig.pose.bones if bone.get('bvh') is None]
        oldbones = [bone for bone in bvhrig.pose.bones if bone.get('bvh') is not None]
        
        # bone groups.. slows it down 
        
        USEBONEGROUPS = False
        #USEBONEGROUPS = True
        
        if USEBONEGROUPS:
        
            # make a bone group
            bpy.ops.object.mode_set(mode='POSE')
            bpy.ops.pose.group_add()
            bvhgroup = bvhrig.pose.bone_groups.active
            bvhgroup.name = "bvh"
            bvhgroup.color_set = 'THEME04'
            
            # add to group
            
            
            for bone in newbones:
                bone.bone_group = bvhgroup           
        
        frame = action.frame_range[0]
        
        while frame <= action.frame_range[1]:
            #scene.update()
            for i in range(len(newbones)):
                scene.frame_set(frame)
                apb = oldbones[i]
                pb = newbones[i]
                
                r1 = apb.matrix.to_quaternion()
                r2 = pb.matrix.to_quaternion()    
                delta = r2 - r1
                
                if pb.parent is None:
                    match_pose_translation(pb, apb)
                    pb.keyframe_insert('location')
                    
                
                if delta.magnitude > TOL :   
                    
                    match_pose_rotation(pb, apb)
                    #bpy.ops.object.mode_set(mode='POSE')
                    if pb.rotation_mode == 'QUATERNION':
                        pb.keyframe_insert('rotation_quaternion')
                        
                    elif pb.rotation_mode == 'AXIS_ANGLE':
                        pb.keyframe_insert('rotation_axis_angle')
            
                    else:
                        pb.keyframe_insert('rotation_euler')
                              
                    #match_pose_translation(pb, apb)
                    #bpy.ops.object.mode_set()
                    #match_pose_scale(pb, apb) 
            frame = frame + 1
        context.preferences.edit.use_global_undo = use_global_undo
        return {'FINISHED'}    

class HelloWorldPanel(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "New Rest Pose from Pose"
    bl_idname = "OBJECT_PT_hello"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "data"

    def draw(self, context):
        layout = self.layout
        '''
        row = layout.row()
        row.operator("pose.snap_bones")
        '''
        row = layout.row()
        row.operator("anim.target_pose")
        row = layout.row()
        row.operator("anim.update_action")


class SnapPoseboneVisual(bpy.types.Operator):
    """ Snaps selected bones to the visual transforms of the active bone.
    """
    bl_idname = "pose.snap_bones"
    bl_label = "Snap Bones to Bone"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False
        try:
            apb = context.active_pose_bone
            bones_sorted = []
            for bone in context.selected_pose_bones:
                bones_sorted += [bone]
            bones_sorted.sort(key=lambda bone: len(bone.parent_recursive))
            for pb in context.selected_pose_bones:
                if pb != apb:
                    match_pose_translation(pb, apb)
                    match_pose_rotation(pb, apb)
                    match_pose_scale(pb, apb)
        finally:
            context.preferences.edit.use_global_undo = use_global_undo
        return {'FINISHED'}

    
def register():    
    bpy.utils.register_class(UpdateAction)
    bpy.utils.register_class(CreateRestPoseRig)
    bpy.utils.register_class(HelloWorldPanel)
    bpy.utils.register_class(SnapPoseboneVisual)
    
if __name__ == "__main__":
    register()