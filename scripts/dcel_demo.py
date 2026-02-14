from pytopmod.geometry.converter import manifold_to_mesh
from pytopmod.geometry.mesh import SimpleMesh
from pytopmod.topology.dcel.backend import DCELBackend
from pytopmod.topology.manifold import Manifold
from pytopmod.topology.types import EdgeID


def make_triangle() -> SimpleMesh:
  backend = DCELBackend()
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
  f2 = manifold.create_face()

  # Bootstrap
  # v1->v2
  # v2->v3
  # v3->v1
  backend._create_edge_node(v1, v2, f1, f2, EdgeID(3), EdgeID(2))
  backend._create_edge_node(v2, v3, f1, f2, EdgeID(1), EdgeID(3))
  backend._create_edge_node(v3, v1, f1, f2, EdgeID(2), EdgeID(1))

  return manifold_to_mesh(manifold, positions)


def make_tetrahedron() -> SimpleMesh:
  # Placeholder for tetrahedron construction
  # Currently delegates to triangle for demo purposes
  return make_triangle()


def main() -> None:
  print("Generating DCEL Triangle...")
  mesh = make_triangle()
  with open("dcel_triangle.obj", "w", encoding="utf-8") as f:
    f.write(mesh.to_obj())
  print("Done.")


if __name__ == "__main__":
  main()
