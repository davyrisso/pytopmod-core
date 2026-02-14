from pytopmod.geometry.converter import manifold_to_mesh
from pytopmod.geometry.mesh import SimpleMesh
from pytopmod.topology.dlfl.backend import DLFLBackend
from pytopmod.topology.manifold import Manifold


def make_triangle() -> SimpleMesh:
  backend = DLFLBackend()
  manifold = Manifold(backend)

  v1 = manifold.create_vertex()
  v2 = manifold.create_vertex()
  v3 = manifold.create_vertex()

  positions = {
    v1: (0.0, 0.0, 0.0),
    v2: (1.0, 0.0, 0.0),
    v3: (0.0, 1.0, 0.0),
  }

  f1 = manifold.create_face()
  backend._face_vertices[f1] = [v1, v2, v3]

  return manifold_to_mesh(manifold, positions)


def main() -> None:
  print("Generating DLFL Triangle...")
  mesh = make_triangle()
  with open("dlfl_triangle.obj", "w", encoding="utf-8") as f:
    f.write(mesh.to_obj())
  print("Done.")


if __name__ == "__main__":
  main()
