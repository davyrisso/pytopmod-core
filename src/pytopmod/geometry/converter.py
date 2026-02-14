from pytopmod.geometry.mesh import SimpleMesh
from pytopmod.geometry.primitives import Point3D
from pytopmod.topology.manifold import Manifold
from pytopmod.topology.types import VertexID


def manifold_to_mesh(
  manifold: Manifold, vertex_positions: dict[VertexID, Point3D]
) -> SimpleMesh:
  """Exports the manifold to a simple mesh representation.

  Args:
      manifold: The topological manifold to export.
      vertex_positions: A dictionary mapping VertexID to geometric coordinates.
  """
  # Get all vertices
  v_ids = manifold.get_vertices()

  # Map VertexID -> Index
  v_map = {vid: i for i, vid in enumerate(v_ids)}

  try:
    vertices = [vertex_positions[vid] for vid in v_ids]
  except KeyError as e:
    raise ValueError(f"Missing geometric coordinates for vertex {e.args[0]}")

  # Get all faces
  faces = []
  for fid in manifold.get_faces():
    f_verts = manifold.get_face_vertices(fid)
    faces.append([v_map[vid] for vid in f_verts])

  return SimpleMesh(vertices, faces)
