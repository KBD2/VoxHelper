from voxhelper import VoxModel, Voxel
import math

RED = 0
GREEN = 1

vox = VoxModel()

vox.setColour(RED, (128, 0, 0))
vox.setColour(GREEN, (0, 255, 128))

# Check https://github.com/ephtracy/voxel-model/blob/master/MagicaVoxel-file-format-vox-extension.txt
# for an (incomplete) list of material properties
glassMaterial = {
    "_type": "_glass",
    "_trans": "0.5"
}
vox.setMaterial(RED, glassMaterial)

voxels = []
for z in range(10):
    for y in range(10):
        for x in range(10):
            if (math.sqrt(math.pow(x - 4, 2) + math.pow(y - 4, 2) + math.pow(z - 4, 2)) < 5):
                # Palette index is automatically converted
                voxels.append(Voxel((x, y, z), RED))   
vox.addShape(voxels)

voxels = []
for z in range(15):
    for y in range(10):
        for x in range(10):
            voxels.append(Voxel((x, y, z), GREEN))
vox.addShape(voxels, offset=(12, 5, 0))

vox.setNote(0, "Note")

vox.write("example.vox")