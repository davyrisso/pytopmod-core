import unittest

from pytopmod.topology.dlfl.backend import DLFLBackend


class TestDLFLBackend(unittest.TestCase):
  def test_square_split_merge(self) -> None:
    backend = DLFLBackend()

    # 1. Create Vertices
    v1 = backend.create_vertex()
    v2 = backend.create_vertex()
    v3 = backend.create_vertex()
    v4 = backend.create_vertex()

    # 2. Create Initial Face
    f1 = backend.create_face()

    # 3. Manually link (Bootstrapping)
    # DLFL represents face as CCW list of vertices
    backend._face_vertices[f1] = [
      v1,
      v4,
      v3,
      v2,
    ]  # v1->v4->v3->v2->v1 ... (Normal pointing down?)
    # Let's say v1(0,1)->v2(1,1)->v3(1,0)->v4(0,0)->v1. CCW.
    backend._face_vertices[f1] = [v1, v2, v3, v4]

    backend._vertex_faces[v1].add(f1)
    backend._vertex_faces[v2].add(f1)
    backend._vertex_faces[v3].add(f1)
    backend._vertex_faces[v4].add(f1)

    # 4. Verify Trace
    # trace v1: should find edge (v1, v2)
    print("Tracing v1...")
    edges_v1 = backend.vertex_trace(v1)
    print(f"Edges v1: {edges_v1}")
    # explicit check
    # edge (v1, v2) in f1.
    # Should be length 1 (only one face).
    self.assertEqual(len(edges_v1), 1)
    e_v1_v2 = edges_v1[0]

    # Check edge info
    info = backend._get_edge_info(e_v1_v2)
    self.assertEqual(info, (v1, v2, f1))

    # 5. Insert Edge (Split)
    # Split f1 by edge (v1, v3).
    # v1 and v3 are in f1.
    # This is Cofacial insertion.
    print("Inserting edge (v1, v3)...")
    new_f_ids = backend.insert_edge(v1, f1, v3, f1)
    f_a, f_b = new_f_ids
    print(f"Split into faces: {f_a}, {f_b}")

    # Verify vertices
    # Original: [v1, v2, v3, v4]
    # Split at (v1, v3).
    # Should get [v1, v2, v3] and [v1, v3, v4] (or similar permutation)
    verts_a = backend._face_vertices[f_a]
    verts_b = backend._face_vertices[f_b]
    print(f"Face A verts: {verts_a}")
    print(f"Face B verts: {verts_b}")

    # Check sizes
    # v1, v2, v3 -> 3
    # v1, v3, v4 -> 3
    self.assertEqual(len(verts_a), 3)
    self.assertEqual(len(verts_b), 3)

    # Check newly created edge exists in both?
    # The edge (v1, v3) is in f_a (or f_b) as (v1, v3) and in the other as (v3, v1)
    # Let's find edge (v1, v3)
    try:
      f_v1_v3 = backend._find_face_containing_edge(v1, v3)
      print(f"Edge (v1, v3) is in face {f_v1_v3}")
    except ValueError:
      self.fail("Edge (v1, v3) not found")

    try:
      f_v3_v1 = backend._find_face_containing_edge(v3, v1)
      print(f"Edge (v3, v1) is in face {f_v3_v1}")
    except ValueError:
      self.fail("Edge (v3, v1) not found")

    self.assertNotEqual(f_v1_v3, f_v3_v1)

    # 6. Delete Edge (Merge)
    # We want to delete the edge we just added.
    # We need its EdgeID using the Unified Interface delete_edge(id).
    # Problem: insert_edge returns FaceIDs, not the EdgeID.
    # But we can find it via trace or registry.
    # Let's use internal registry to find it for testing.

    # The edge ID for (v1, v3) in f_v1_v3.
    e_split_id = backend._get_or_create_edge_id(v1, v3, f_v1_v3)
    print(f"Deleting edge {e_split_id}...")

    backend.delete_edge(e_split_id)

    # Result should be one face?
    # But delete_edge logic creates A NEW FACE and deletes the old two.
    # So check active faces.
    active_faces = list(backend._face_vertices.keys())
    print(f"Active faces: {active_faces}")
    # There should be exactly 1 active face (plus potentially gaps in ID if we don't reuse)
    # Actually checking count.
    self.assertEqual(len(active_faces), 1)

    final_face = active_faces[0]
    final_verts = backend._face_vertices[final_face]
    print(f"Final verts: {final_verts}")

    # Should be length 4
    self.assertEqual(len(final_verts), 4)
    # Should contain v1, v2, v3, v4
    self.assertEqual(set(final_verts), {v1, v2, v3, v4})


if __name__ == "__main__":
  unittest.main()
