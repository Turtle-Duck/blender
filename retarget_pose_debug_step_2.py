import bpy

class SimpleOperator(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.simple_operator"
    bl_label = "Simple Object Operator"


    @classmethod
    def poll(cls, context):
        return context.active_object is not None


    def execute(self, context):
        #dupe the armature
        bpy.ops.object.mode_set(mode='OBJECT')
        # bpy.ops.object.duplicate()
        newarm = context.object
        # copy the action
        # newaction = newarm.animation_data.action.copy()
        # strip out the old fcurves
        # for fcurve in newaction.fcurves:
        #     if fcurve.data_path.find(".001") == -1:
        #         newaction.fcurves.remove(fcurve)
        #     else:
        #         fcurve.data_path = fcurve.data_path.replace(".001","")
        # newarm.animation_data.action = newaction
            
        bones = [bone.name for bone in newarm.pose.bones if bone.get('bvh') is not None]
        # remove original bones
        bpy.ops.object.mode_set(mode='EDIT')
        
        arm = newarm.data
        for name in bones:
            eb = arm.edit_bones.get(name)
            arm.edit_bones.remove(eb)
                
        # rename bones to original names        
        # bpy.ops.object.mode_set(mode='POSE')
        # for pb in newarm.pose.bones:
        #     pb.name = pb["bvh"]
            
        return {'FINISHED'}

def register():
    bpy.utils.register_class(SimpleOperator)

def unregister():
    bpy.utils.unregister_class(SimpleOperator)

if __name__ == "__main__":
    register()

    # test call
    bpy.ops.object.simple_operator()