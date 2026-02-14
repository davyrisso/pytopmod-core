import dataclasses
from pytopmod.geometry.primitives import Point3D


@dataclasses.dataclass
class SimpleMesh:
  """A simple mesh representation using integer IDs and lists."""

  vertices: list[Point3D]
  faces: list[list[int]]  # Indices into vertices list

  def to_obj(self) -> str:
    """Converts the mesh to OBJ format."""
    obj_lines = []

    # Vertices
    for v in self.vertices:
      obj_lines.append(f"v {v[0]} {v[1]} {v[2]}")

    # Faces
    # OBJ indices are 1-based
    for face in self.faces:
      indices = [str(i + 1) for i in face]
      obj_lines.append(f"f {' '.join(indices)}")

    return "\n".join(obj_lines)
