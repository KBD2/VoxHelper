class Voxel:
    x: int
    y: int
    z: int
    i: int

    def __init__(self, pos: tuple[int, int, int], paletteIndex: int):
        self.x = pos[0]
        self.y = pos[1]
        self.z = pos[2]
        self.i = paletteIndex + 1

    def compile(self):
        return bytearray([self.x, self.y, self.z, self.i])

class Extent:
    xMin: int
    xMax: int
    yMin: int
    yMax: int

    def __init__(self):
        self.xMin = 0
        self.xMax = 0
        self.yMin = 0
        self.yMax = 0

    def __str__(self):
        return f"{self.xMin}, {self.xMax}, {self.yMin}, {self.yMax}"

class BuiltShape:
    sizeChunk: bytearray
    indexesChunk: bytearray
    transformChunk: bytearray
    shapeChunk: bytearray
    transformId: int

class VoxModel:
    def __init__(self):
        self.nextNodeId = 2 # IDs 0 and 1 are for the base transform node and the group node
        self.extent = Extent()

        self.colours: dict[int, tuple[int, int, int]] = {}
        self.materials: dict[int, dict] = {}
        self.shapes: list[BuiltShape] = []
        self.notes = {}

    def setMaterial(self, paletteIndex: int, properties: dict):
        self.materials[paletteIndex + 1] = properties

    def setNote(self, row: int, note: str):
        self.notes[row] = note

    def setColour(self, index, colour: tuple[int, int, int]):
        self.colours[index] = colour

    def addShape(self, voxels: list[Voxel], offset: tuple = (0, 0, 0)):
        width = 0
        length = 0
        height = 0

        built = BuiltShape()

        indexesSize = len(voxels)
        chunkSize = 4 * indexesSize + 4
        indexesChunk = bytearray([
            0x58, 0x59, 0x5a, 0x49, # "XYZI"
            chunkSize & 0xff, (chunkSize >> 8) & 0xff, (chunkSize >> 16) & 0xff, (chunkSize >> 24) & 0xff, # Content size
            0x0, 0x0, 0x0, 0x0, # Child content size
            indexesSize & 0xff, (indexesSize >> 8) & 0xff, (indexesSize >> 16) & 0xff, (indexesSize >> 24) & 0xff # Number of indices
        ])
        concatenatedIndices = bytearray()
        for voxel in voxels:
            concatenatedIndices.extend(voxel.compile())
            width = max(width, voxel.x + 1)
            length = max(length, voxel.y + 1)
            height = max(height, voxel.z + 1)

        indexesChunk.extend(concatenatedIndices)

        self.extent.xMin = min(self.extent.xMin, offset[0] - width // 2)
        self.extent.xMax = max(self.extent.xMax, offset[0] + width // 2)
        self.extent.yMin = min(self.extent.yMin, offset[1] - length // 2)
        self.extent.yMax = max(self.extent.yMax, offset[1] + length // 2)

        sizeChunk = bytearray([
            0x53, 0x49, 0x5a, 0x45, # "SIZE"
            0x0c, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, # Size (12, 0)
            width & 0xff, (width >> 8), 0x0, 0x0,
            length & 0xff, (length >> 8), 0x0, 0x0,
            height & 0xff, (height >> 8), 0x0, 0x0
        ])
        

        transformNodeId = self.nextNodeId
        self.nextNodeId += 1
        shapeNodeId = self.nextNodeId
        self.nextNodeId += 1

        transform = {
            "_t": f"{offset[0]} {offset[1]} {offset[2] + height // 2}"
        }
        compiledTransform = compileDict(transform)
        chunkSize = 24 + len(compiledTransform)
        shapeTransformChunk = bytearray([
            0x6e, 0x54, 0x52, 0x4e, # "nTRN"
            chunkSize & 0xff, (chunkSize >> 8) & 0xff, (chunkSize >> 16) & 0xff, (chunkSize >> 24) & 0xff, # Content size
            0x00, 0x00, 0x00, 0x00, # Child content size (0)
            transformNodeId & 0xff, (transformNodeId >> 8) & 0xff, (transformNodeId >> 16) & 0xff, (transformNodeId >> 24) & 0xff, # Node ID
            0x00, 0x00, 0x00, 0x00, # Empty attribute dict
            shapeNodeId & 0xff, (shapeNodeId >> 8) & 0xff, (shapeNodeId >> 16) & 0xff, (shapeNodeId >> 24) & 0xff, # Child node ID
            0xff, 0xff, 0xff, 0xff, # Reserved
            0x00, 0x00, 0x00, 0x00, # Layer ID
            0x01, 0x00, 0x00, 0x00, # Number of frames
        ])
        shapeTransformChunk.extend(compiledTransform)

        modelId = len(self.shapes)
        shapeChunk = bytearray([
            0x6e, 0x53, 0x48, 0x50, # "nSHP"
            0x14, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, # Size (20, 0)
            shapeNodeId & 0xff, (shapeNodeId >> 8) & 0xff, (shapeNodeId >> 16) & 0xff, (shapeNodeId >> 24) & 0xff, # Node ID
            0x00, 0x00, 0x00, 0x00, # Empty dict
            0x01, 0x00, 0x00, 0x00, # Number of models

            modelId & 0xff, (modelId >> 8) & 0xff, (modelId >> 16) & 0xff, (modelId >> 24) & 0xff, # Model ID
            0x00, 0x00, 0x00, 0x00 # Empty dict
        ])

        built.sizeChunk = sizeChunk
        built.indexesChunk = indexesChunk
        built.transformChunk = shapeTransformChunk
        built.shapeChunk = shapeChunk
        built.transformId = transformNodeId

        self.shapes.append(built)
    
    def write(self, filename: str):
        shapesChunks = bytearray()
        for shape in self.shapes:
            shapesChunks.extend(shape.sizeChunk)
            shapesChunks.extend(shape.indexesChunk)

        offsetX = -(self.extent.xMin + (self.extent.xMax - self.extent.xMin) // 2)
        offsetY = -(self.extent.yMin + (self.extent.yMax - self.extent.yMin) // 2)
        transform = {
            "_t": f"{offsetX} {offsetY} 0"
        }
        compiledTransform = compileDict(transform)
        chunkSize = 24 + len(compiledTransform)
        baseTransformChunk = bytearray([
            0x6e, 0x54, 0x52, 0x4e, # "nTRN"
            chunkSize & 0xff, (chunkSize >> 8) & 0xff, (chunkSize >> 16) & 0xff, (chunkSize >> 24) & 0xff, # Content size
            0x00, 0x00, 0x00, 0x00, # Child content size (0)
            0x00, 0x00, 0x00, 0x00, # Node ID
            0x00, 0x00, 0x00, 0x00, # Empty attribute dict
            0x01, 0x00, 0x00, 0x00, # Child node ID
            0xff, 0xff, 0xff, 0xff, # Reserved
            0xff, 0xff, 0xff, 0xff, # Layer ID
            0x01, 0x00, 0x00, 0x00, # Number of frames
        ])
        baseTransformChunk.extend(compiledTransform)

        numChildren = len(self.shapes)
        contentSize = 12 + 4 * numChildren
        groupChunk = bytearray([
            0x6e, 0x47, 0x52, 0x50, # "nGRP"
            contentSize & 0xff, (contentSize >> 8) & 0xff, (contentSize >> 16) & 0xff, (contentSize >> 24) & 0xff, # Content size
            0x00, 0x00, 0x00, 0x00, # Child content size (0)
            0x01, 0x00, 0x00, 0x00, # Node ID
            0x00, 0x00, 0x00, 0x00, # Empty attribute dict
            numChildren & 0xff, (numChildren >> 8) & 0xff, (numChildren >> 16) & 0xff, (numChildren >> 24) & 0xff, # Number of children
        ])
        for shape in self.shapes:
            id = shape.transformId
            groupChunk.extend([id & 0xff, (id >> 8) & 0xff, (id >> 16) & 0xff, (id >> 24) & 0xff])
        
        nodeChunks = bytearray()
        for shape in self.shapes:
            nodeChunks.extend(shape.transformChunk)
            nodeChunks.extend(shape.shapeChunk)

        materialChunks = bytearray()
        
        for id in self.materials:
            properties = self.materials[id]
            numKeys = len(properties)
            compiled = bytearray([numKeys & 0xff, (numKeys >> 8) & 0xff, (numKeys >> 16) & 0xff, (numKeys >> 24) & 0xff])
            for name, value in properties.items():
                compiled.extend(compileString(name))
                compiled.extend(compileString(value))

            chunkSize = len(compiled) + 4
            materialChunk = bytearray([
                0x4d, 0x41, 0x54, 0x4c, # "MATL"
                chunkSize & 0xff, (chunkSize >> 8) & 0xff, (chunkSize >> 16) & 0xff, (chunkSize >> 24) & 0xff, # Content size
                0x0, 0x0, 0x0, 0x0, # Child content size
                id, 0x00, 0x00, 0x00, # Index
            ])
            materialChunk.extend(compiled)

            materialChunks.extend(materialChunk)

        paletteChunk = bytearray([
            0x52, 0x47, 0x42, 0x41, # "RGBA"
            0x0, 0x4, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0 # Size (1024, 0)
        ])

        for i in range(256):
            if i in self.colours:
                colour = self.colours[i]
                paletteChunk.extend([colour[0], colour[1], colour[2], 255])
            else:
                paletteChunk.extend([75, 75, 75, 255])

        notes = []
        for i in range(31, -1, -1):
            if i in self.notes:
                notes.append(self.notes.get(i))
            else:
                notes.append("")

        contentSize = 4 + sum(map(lambda x : len(x) + 4, notes))
        notesChunk = bytearray([
            0x4e, 0x4f, 0x54, 0x45, # "NOTE"
            contentSize & 0xff, (contentSize >> 8) & 0xff, (contentSize >> 16) & 0xff, (contentSize >> 24) & 0xff, # Content size
            0x00, 0x00, 0x00, 0x00, # Child content size
            0x20, 0x00, 0x00, 0x00 # Num notes (32)
        ])
        for note in notes:
            notesChunk.extend(compileString(note))
            

        mainChunkSize = len(shapesChunks) + len(baseTransformChunk) + len(groupChunk) + len(nodeChunks) + len(materialChunks) + len(paletteChunk) + len(notesChunk)
        mainChunk = bytearray([
            0x4d, 0x41, 0x49, 0x4e, # "MAIN"
            0x00, 0x00, 0x00, 0x00, # Content size (0)
            mainChunkSize & 0xff, (mainChunkSize >> 8) & 0xff, (mainChunkSize >> 16) & 0xff, (mainChunkSize >> 24) & 0xff # Child content size
        ])
        mainChunk.extend(shapesChunks)
        mainChunk.extend(baseTransformChunk)
        mainChunk.extend(groupChunk)
        mainChunk.extend(nodeChunks)
        mainChunk.extend(paletteChunk)
        mainChunk.extend(materialChunks)
        mainChunk.extend(notesChunk)

        with open(filename, "wb") as file:
            file.write(b'VOX ')
            file.write((200).to_bytes(4, 'little'))
            file.write(mainChunk)

def compileInt(value: int) -> bytearray:
    if value >= 0:
        return value.to_bytes(4, 'little')
    else:
        return value.to_bytes(4, 'little', signed=True)

def compileString(string: str) -> bytearray:
    return len(string).to_bytes(4, 'little') + string.encode('ascii')

def compileDict(dictionary: dict) -> bytearray:
    ret = compileInt(len(dictionary.keys()))
    for k, v, in dictionary.items():
        ret += compileString(k) + compileString(v)
    return ret