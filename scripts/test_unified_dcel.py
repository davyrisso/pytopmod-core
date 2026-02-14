import unittest

from pytopmod.topology.dcel.backend import DCELBackend
from pytopmod.topology.manifold import Manifold
from pytopmod.topology.types import EdgeID, FaceID, VertexID


class TestDCELBackend(unittest.TestCase):
  def test_tetrahedron_construction(self) -> None:
    backend = DCELBackend()

    # Create Vertices (v1..v4)
    v1 = backend.create_vertex()
    v2 = backend.create_vertex()
    v3 = backend.create_vertex()
    v4 = backend.create_vertex()

    # Maintain coordinates externally for verification if needed
    # Maintain coordinates externally for verification if needed
    # (Coordinates removed as they were unused)

    # Create Faces (f1..f4)
    f1 = backend.create_face()
    f2 = backend.create_face()
    f3 = backend.create_face()
    f4 = backend.create_face()

    # Create Edges (e1..e6)
    # We manually assign IDs for next_pointers assuming sequential creation 1..6
    # This mirrors the logic in primitives.py where keys were "e1".."e6"

    # e1: v1 -> v2 (f_4, f_1) next: e6, e3 (if using original Next/Prev logic? Wait)
    # Original: mesh.create_edge(v_2, v_1, f_4, f_1, "e6", "e3")
    # WAIT: The original create_edge args were:
    # vertex_1_key, vertex_2_key, face_1_key, face_2_key, next_edge_1_key, next_edge_2_key
    # The primitives.py says: mesh.create_edge(v_2, v_1, f_4, f_1, "e6", "e3")
    # So v2 is v1_key, v1 is v2_key.
    # Edge 1 (in primitives, named implicitly by order? No, it doesn't return keys)
    # Actually primitives.py doesn't capture return values.
    # But it passes "e6", "e3" strings.
    # The key generation in KeyStore is sequential: e1, e2 ...

    # Let's blindly follow primitives.py logic but using IDs 1..6

    # Helper to bypass protected access for constructing the mesh
    def create_edge(
      v1: VertexID,
      v2: VertexID,
      f1: FaceID,
      f2: FaceID,
      n1_id: int,
      n2_id: int,
    ) -> EdgeID:
      return backend._create_edge_node(
        v1, v2, f1, f2, EdgeID(n1_id), EdgeID(n2_id)
      )

    # e1
    create_edge(v2, v1, f4, f1, 6, 3)
    # e2
    create_edge(v1, v3, f4, f2, 1, 5)
    # e3
    create_edge(v1, v4, f2, f1, 2, 4)
    # e4
    create_edge(v4, v2, f3, f1, 5, 1)
    # e5
    create_edge(v3, v4, f3, f2, 6, 3)
    # e6
    create_edge(v2, v3, f3, f4, 4, 2)

    # Verification
    # Check Vertex Trace for v1
    # v1 is in e1, e2, e3.
    # e1: v2->v1. v1 is v2_key. next_2 is e3.
    # e3: v1->v4. v1 is v1_key. next_1 is e2.
    # e2: v1->v3. v1 is v1_key. next_1 is e1.
    # Cycle: e1 -> e3 -> e2 -> e1. Correct.

    print("Checking vertex trace v1...")
    trace_v1 = backend.vertex_trace(v1)
    print(f"Trace v1: {trace_v1}")
    self.assertEqual(len(set(trace_v1)), 3)
    self.assertIn(EdgeID(1), trace_v1)
    self.assertIn(EdgeID(2), trace_v1)
    self.assertIn(EdgeID(3), trace_v1)

    # Check Face Trace for f1
    # f1 is in e1 (right), e3 (right), e4 (right)
    # e1 (v2, v1, f4, f1). f1 is face_2. next_2 is e3.
    # e3 (v1, v4, f2, f1). f1 is face_2. next_2 is e4.
    # e4 (v4, v2, f3, f1). f1 is face_2. next_2 is e1.
    # Cycle: e1 -> e3 -> e4 -> e1. Correct.
    print("Checking face trace f1...")
    trace_f1 = backend.face_trace(f1)
    print(f"Trace f1: {trace_f1}")
    self.assertEqual(len(set(trace_f1)), 3)
    self.assertIn(EdgeID(1), trace_f1)
    self.assertIn(EdgeID(3), trace_f1)
    self.assertIn(EdgeID(4), trace_f1)

  def test_insert_edge_split(self) -> None:
    backend = DCELBackend()
    # Simple Square: v1-v2-v3-v4
    v1 = backend.create_vertex()
    v2 = backend.create_vertex()
    v3 = backend.create_vertex()
    v4 = backend.create_vertex()

    f1 = backend.create_face()  # outer?
    f2 = backend.create_face()  # inner

    # e1: v1-v2
    # e2: v2-v3
    # e3: v3-v4
    # e4: v4-v1

    # Inner face f2. Outer f1.
    # e1: v1->v2 (f1, f2) next_1=e4, next_2=e2
    # e2: v2->v3 (f1, f2) next_1=e1, next_2=e3
    # e3: v3->v4 (f1, f2) next_1=e2, next_2=e4
    # e4: v4->v1 (f1, f2) next_1=e3, next_2=e1

    e1 = backend._create_edge_node(v1, v2, f1, f2, EdgeID(4), EdgeID(2))
    backend._create_edge_node(v2, v3, f1, f2, EdgeID(1), EdgeID(3))
    backend._create_edge_node(v3, v4, f1, f2, EdgeID(2), EdgeID(4))
    backend._create_edge_node(v4, v1, f1, f2, EdgeID(3), EdgeID(1))

    # Insert edge between v1 and v3 across f2 (split face)
    # vertex_1=v1, face_1=f2. vertex_2=v3, face_2=f2.

    # Check pre-conditions
    t_v1 = backend.vertex_trace(v1)
    print(f"Trace v1 sq: {t_v1}")

    new_faces = backend.insert_edge(v1, f2, v3, f2)
    print(f"New Faces: {new_faces}")

    # Should result in 2 new faces replacing f2
    self.assertNotEqual(new_faces[0], f2)
    self.assertNotEqual(new_faces[1], f2)
    self.assertNotEqual(new_faces[0], new_faces[1])

    # f2 should be "deleted" (effectively unused)
    # Edges should now point to new faces.

    # Check e1 face_2
    node_e1 = backend._edge_nodes[e1]
    self.assertIn(node_e1.face_2_id, new_faces)

    # Check newly created edge
    # It should satisfy Euler: V=4, E=5, F=2+1(outer)=3?
    # Originally F=2 (1 inner, 1 outer).
    # Split inner -> 2 inner. Total F=3.
    # E was 4. Now 5.
    # V is 4.
    # 4 - 5 + 3 = 2. Euler characteristic for sphere/plane is 2. Correct.


if __name__ == "__main__":
  unittest.main()
