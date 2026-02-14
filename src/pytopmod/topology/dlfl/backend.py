import itertools
from typing import Optional, Tuple

from pytopmod.topology.manifold import TopologyBackend
from pytopmod.topology.types import EdgeID, FaceID, VertexID


class DLFLBackend(TopologyBackend):
  def __init__(self) -> None:
    # Face -> primary list of vertices (boundary)
    self._face_vertices: dict[FaceID, list[VertexID]] = {}
    # Vertex -> set of faces it belongs to
    self._vertex_faces: dict[VertexID, set[FaceID]] = {}
    self._active_vertices: set[VertexID] = set()

    # ID Generators
    self._vertex_counter = itertools.count(1)
    self._face_counter = itertools.count(1)
    # Edge registry to support EdgeID in unified interface
    self._edge_registry: dict[EdgeID, Tuple[VertexID, VertexID, FaceID]] = {}
    self._reverse_edge_registry: dict[
      Tuple[VertexID, VertexID, FaceID], EdgeID
    ] = {}
    self._edge_counter = itertools.count(1)

  def _get_or_create_edge_id(
    self, v1: VertexID, v2: VertexID, face_id: FaceID
  ) -> EdgeID:
    key = (v1, v2, face_id)
    if key in self._reverse_edge_registry:
      return self._reverse_edge_registry[key]

    edge_id = EdgeID(next(self._edge_counter))
    self._edge_registry[edge_id] = key
    self._reverse_edge_registry[key] = edge_id
    return edge_id

  def _get_edge_info(
    self, edge_id: EdgeID
  ) -> Tuple[VertexID, VertexID, FaceID]:
    if edge_id not in self._edge_registry:
      raise ValueError(f"Edge {edge_id} not found in registry")
    return self._edge_registry[edge_id]

  # -------------------------------------------------------------------------
  # Core CRUD
  # -------------------------------------------------------------------------
  def create_vertex(self) -> VertexID:
    vertex_id = VertexID(next(self._vertex_counter))
    self._vertex_faces[vertex_id] = set()
    self._active_vertices.add(vertex_id)
    return vertex_id

  def delete_vertex(self, vertex_id: VertexID) -> None:
    if vertex_id in self._vertex_faces:
      del self._vertex_faces[vertex_id]
    self._active_vertices.discard(vertex_id)

  def create_face(self) -> FaceID:
    face_id = FaceID(next(self._face_counter))
    self._face_vertices[face_id] = []
    return face_id

  def delete_face(self, face_id: FaceID) -> None:
    del self._face_vertices[face_id]

  # -------------------------------------------------------------------------
  # Edge Emulation
  # -------------------------------------------------------------------------
  # -------------------------------------------------------------------------
  # Trace
  # -------------------------------------------------------------------------
  def vertex_trace(self, vertex_id: VertexID) -> list[EdgeID]:
    """Returns list of outgoing EdgeIDs around vertex in sequence."""
    if not self._vertex_faces.get(vertex_id):
      return []

    # 1. Pick arbitrary start face and successor
    start_face = next(iter(self._vertex_faces[vertex_id]))
    v_next = self._next_in_face(start_face, vertex_id)

    start_edge = self._get_or_create_edge_id(vertex_id, v_next, start_face)
    result = [start_edge]

    curr_v = v_next
    while True:
      # Pivot: Find face containing twin edge (curr_v, vertex_id)
      try:
        face = self._find_face_containing_edge(curr_v, vertex_id)
      except ValueError:
        # Boundary or broken topology (should not happen in manifold)
        break

      # In this new face, find successor of vertex_id
      v_next = self._next_in_face(face, vertex_id)
      edge = self._get_or_create_edge_id(vertex_id, v_next, face)

      if edge == start_edge:
        break
      result.append(edge)
      curr_v = v_next

    return result

  def face_trace(self, face_id: FaceID) -> list[EdgeID]:
    vertices = self._face_vertices[face_id]
    L = len(vertices)
    return [
      self._get_or_create_edge_id(vertices[i], vertices[(i + 1) % L], face_id)
      for i in range(L)
    ]

  def _next_in_face(self, face_id: FaceID, current_v: VertexID) -> VertexID:
    verts = self._face_vertices[face_id]
    idx = verts.index(current_v)
    return verts[(idx + 1) % len(verts)]

  def _assign_face_vertices(
    self,
    face_id: FaceID,
    vertices: list[VertexID],
    old_face_id: Optional[FaceID] = None,
  ) -> None:
    """Assigns vertices to a face and updates vertex-face mapping."""
    self._face_vertices[face_id] = vertices
    for v in vertices:
      faces = self._vertex_faces[v]
      if old_face_id and old_face_id in faces:
        faces.remove(old_face_id)
      faces.add(face_id)

  # -------------------------------------------------------------------------
  # Iterators
  # -------------------------------------------------------------------------
  def get_vertices(self) -> list[VertexID]:
    return list(self._active_vertices)

  def get_faces(self) -> list[FaceID]:
    return list(self._face_vertices.keys())

  def get_face_vertices(self, face_id: FaceID) -> list[VertexID]:
    return self._face_vertices[face_id]

  # -------------------------------------------------------------------------
  # Operators
  # -------------------------------------------------------------------------
  def insert_edge(
    self,
    vertex_1_id: VertexID,
    face_1_id: FaceID,
    vertex_2_id: VertexID,
    face_2_id: FaceID,
  ) -> Tuple[FaceID, FaceID]:
    if face_1_id == face_2_id:
      return self._insert_edge_cofacial(vertex_1_id, face_1_id, vertex_2_id)
    else:
      return self._insert_edge_non_cofacial(
        vertex_1_id, face_1_id, vertex_2_id, face_2_id
      )

  def _insert_edge_cofacial(
    self, verbose_1_id: VertexID, old_face_id: FaceID, vertex_2_id: VertexID
  ) -> Tuple[FaceID, FaceID]:
    # Split old_face into new_face_1 and new_face_2
    vertices = self._face_vertices[old_face_id]

    # Calculate split logic

    try:
      r_verts = self._circulated_to(vertices, vertex_2_id)
      p1, p2 = self._split_at(r_verts, verbose_1_id)
    except ValueError:
      raise ValueError(
        f"Vertices {verbose_1_id} or {vertex_2_id} not in face {old_face_id}"
      )

    new_face_1_vertices = p1 + [vertex_2_id]
    new_face_2_vertices = p2 + [verbose_1_id]

    new_face_1_id = self.create_face()
    new_face_2_id = self.create_face()

    self._assign_face_vertices(new_face_1_id, new_face_1_vertices, old_face_id)
    self._assign_face_vertices(new_face_2_id, new_face_2_vertices, old_face_id)

    # Migrate Edge IDs
    self._migrate_edges(new_face_1_id, old_face_id)
    self._migrate_edges(new_face_2_id, old_face_id)

    # Delete old face
    self.delete_face(old_face_id)

    return (new_face_1_id, new_face_2_id)

  def _insert_edge_non_cofacial(
    self,
    vertex_1_id: VertexID,
    face_1_id: FaceID,
    vertex_2_id: VertexID,
    face_2_id: FaceID,
  ) -> Tuple[FaceID, FaceID]:
    # Merge logic
    f1_verts = self._face_vertices[face_1_id]
    f2_verts = self._face_vertices[face_2_id]

    v2_prev = f2_verts[(f2_verts.index(vertex_2_id) - 1) % len(f2_verts)]

    part1 = self._circulated_to(f1_verts, vertex_1_id)
    part2 = self._circulated_to(f2_verts, v2_prev)

    new_verts = part1 + part2
    if len(f2_verts) > 1:
      new_verts.append(vertex_2_id)
    if len(f1_verts) > 1:
      new_verts.append(vertex_1_id)

    new_face_id = self.create_face()
    self._assign_face_vertices(new_face_id, new_verts)

    # Update vertex faces (removing both old faces)
    for v in new_verts:
      faces = self._vertex_faces[v]
      if face_1_id in faces:
        faces.remove(face_1_id)
      if face_2_id in faces:
        faces.remove(face_2_id)

    self._migrate_edges(new_face_id, face_1_id)
    self._migrate_edges(new_face_id, face_2_id)

    self.delete_face(face_1_id)
    self.delete_face(face_2_id)

    return (new_face_id, new_face_id)

  def delete_edge(self, edge_id: EdgeID) -> None:
    try:
      u, v, f1 = self._get_edge_info(edge_id)
    except ValueError:
      return

    # Find twin (v, u)
    try:
      f2 = self._find_face_containing_edge(v, u)
    except ValueError:
      raise ValueError(f"Twin edge ({v}, {u}) not found for edge {edge_id}")

    if f1 != f2:
      self._delete_edge_non_cofacial(u, f1, v, f2)
    else:
      self._delete_edge_cofacial(u, f1, v)

    if (u, v, f1) in self._reverse_edge_registry:
      eid = self._reverse_edge_registry.pop((u, v, f1))
      if eid in self._edge_registry:
        del self._edge_registry[eid]

    if (v, u, f2) in self._reverse_edge_registry:
      eid = self._reverse_edge_registry.pop((v, u, f2))
      if eid in self._edge_registry:
        del self._edge_registry[eid]

  def _delete_edge_non_cofacial(
    self,
    vertex_1_id: VertexID,
    face_1_id: FaceID,
    vertex_2_id: VertexID,
    face_2_id: FaceID,
  ) -> None:
    f1_verts = self._face_vertices[face_1_id]
    f2_verts = self._face_vertices[face_2_id]

    part1 = self._circulated_to(f1_verts, vertex_1_id)[:-1]
    part2 = self._circulated_to(f2_verts, vertex_2_id)[:-1]

    new_verts = part1 + part2
    new_face_id = self.create_face()
    self._assign_face_vertices(new_face_id, new_verts)

    # Manually remove old faces since we have two sources
    for v in new_verts:
      faces = self._vertex_faces[v]
      if face_1_id in faces:
        faces.remove(face_1_id)
      if face_2_id in faces:
        faces.remove(face_2_id)

    self._migrate_edges(new_face_id, face_1_id)
    self._migrate_edges(new_face_id, face_2_id)

    self.delete_face(face_1_id)
    self.delete_face(face_2_id)

  def _delete_edge_cofacial(
    self, vertex_1_id: VertexID, face_id: FaceID, vertex_2_id: VertexID
  ) -> None:
    vertices = self._face_vertices[face_id]

    idx_v1 = -1
    L = len(vertices)
    for i in range(L):
      if vertices[i] == vertex_1_id and vertices[(i + 1) % L] == vertex_2_id:
        idx_v1 = i
        break

    if idx_v1 == -1:
      raise ValueError("Edge not found in face")

    r_verts = self._circulated_to(vertices, vertex_2_id)

    idx_v2 = -1
    L2 = len(r_verts)
    for i in range(L2):
      if r_verts[i] == vertex_2_id and r_verts[(i + 1) % L2] == vertex_1_id:
        idx_v2 = i
        break

    if idx_v2 == -1:
      raise ValueError("Edge is not a bridge/double-edge")

    split_idx = idx_v2 + 2
    p1 = r_verts[:split_idx]
    p2 = r_verts[split_idx:]

    new_face_1_vertices = p1[:-1]
    new_face_2_vertices = p2[:-1]

    id1 = self.create_face()
    id2 = self.create_face()

    self._assign_face_vertices(id1, new_face_1_vertices, face_id)
    self._assign_face_vertices(id2, new_face_2_vertices, face_id)

    self._migrate_edges(id1, face_id)
    self._migrate_edges(id2, face_id)

    self.delete_face(face_id)

  def _find_face_containing_edge(self, u: VertexID, v: VertexID) -> FaceID:
    for f in self._vertex_faces[u]:
      verts = self._face_vertices[f]
      L = len(verts)
      for i in range(L):
        if verts[i] == u and verts[(i + 1) % L] == v:
          return f
    raise ValueError(f"No face contains edge ({u}, {v})")

  # -------------------------------------------------------------------------
  # Helpers
  # -------------------------------------------------------------------------
  def _circulated_to(
    self, lst: list[VertexID], item: VertexID
  ) -> list[VertexID]:
    idx = lst.index(item)
    i = (idx + 1) % len(lst)
    return lst[i:] + lst[:i]

  def _split_at(
    self, lst: list[VertexID], item: VertexID
  ) -> Tuple[list[VertexID], list[VertexID]]:
    idx = lst.index(item) + 1
    return lst[:idx], lst[idx:]

  def _migrate_edges(self, new_face_id: FaceID, old_face_id: FaceID) -> None:
    # Scan pairs in new_face. If pair existed in old_face, update registry.
    verts = self._face_vertices[new_face_id]
    L = len(verts)
    for i in range(L):
      u, v = verts[i], verts[(i + 1) % L]
      old_key = (u, v, old_face_id)
      if old_key in self._reverse_edge_registry:
        eid = self._reverse_edge_registry.pop(old_key)
        new_key = (u, v, new_face_id)
        self._reverse_edge_registry[new_key] = eid
        self._edge_registry[eid] = new_key
