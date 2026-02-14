import unittest

from pytopmod.geometry.converter import manifold_to_mesh
from pytopmod.geometry.mesh import SimpleMesh
from pytopmod.topology.dcel.backend import DCELBackend
from pytopmod.topology.dlfl.backend import DLFLBackend
from pytopmod.topology.manifold import Manifold


class TestManifoldExport(unittest.TestCase):
  def test_dcel_export(self) -> None:
    backend = DCELBackend()
    manifold = Manifold(backend)

    # Create a Triangle
    v1 = manifold.create_vertex()
    v2 = manifold.create_vertex()
    v3 = manifold.create_vertex()

    coords = {
      v1: (0.0, 0.0, 0.0),
      v2: (1.0, 0.0, 0.0),
      v3: (0.0, 1.0, 0.0),
    }

    f1 = manifold.create_face()  # front
    f2 = manifold.create_face()  # back

    # Helper to creating edges via backend directly because Manifold doesn't expose low-level edge creation yet?
    # Manifold only exposes `insert_edge`.
    # To bootstrap valid topology in DCEL, we often need manual wiring or a "make_triangle" primitive.
    # But `insert_edge` is high-level Euler op.
    # Let's use backend-specific bootstrapping for test.
    # But we want to test MANIFOLD export.

    # Bootstrapping via backend internal access for speed
    # e1: v1->v2
    # e2: v2->v3
    # e3: v3->v1

    # e1 (v1, v2, f1, f2)
    # e2 (v2, v3, f1, f2)
    # e3 (v3, v1, f1, f2)

    # Using IDs 1, 2, 3
    # backend._create_edge_node(...)

    from pytopmod.topology.types import EdgeID

    backend._create_edge_node(v1, v2, f1, f2, EdgeID(3), EdgeID(2))  # e1
    backend._create_edge_node(v2, v3, f1, f2, EdgeID(1), EdgeID(3))  # e2
    backend._create_edge_node(v3, v1, f1, f2, EdgeID(2), EdgeID(1))  # e3

    mesh = manifold_to_mesh(manifold, coords)

    self.assertIsInstance(mesh, SimpleMesh)
    self.assertEqual(len(mesh.vertices), 3)
    self.assertEqual(len(mesh.faces), 2)

    # Verify positions
    self.assertIn((0, 0, 0), mesh.vertices)

    # Verify face content (indices)
    # We don't know the order of vertices in mesh.vertices (depends on dict order/hash)
    # But we can check that mapped points form a triangle.

  def test_dlfl_export(self) -> None:
    backend = DLFLBackend()
    manifold = Manifold(backend)

    v1 = manifold.create_vertex()
    v2 = manifold.create_vertex()
    v3 = manifold.create_vertex()
    v4 = manifold.create_vertex()

    coords = {
      v1: (0.0, 0.0, 0.0),
      v2: (1.0, 0.0, 0.0),
      v3: (1.0, 1.0, 0.0),
      v4: (0.0, 1.0, 0.0),
    }

    f1 = manifold.create_face()
    backend._face_vertices[f1] = [v1, v2, v3, v4]

    mesh = manifold_to_mesh(manifold, coords)

    self.assertEqual(len(mesh.vertices), 4)
    self.assertEqual(len(mesh.faces), 1)
    self.assertEqual(len(mesh.faces[0]), 4)


if __name__ == "__main__":
  unittest.main()
