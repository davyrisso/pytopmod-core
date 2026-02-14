import dataclasses
import itertools
from typing import Generator, Optional, Tuple

from pytopmod.topology.manifold import TopologyBackend
from pytopmod.topology.types import Corner, EdgeID, FaceID, VertexID


@dataclasses.dataclass(slots=True)
class EdgeNode:
  """An Edge Node in the DCEL structure (using integer IDs)."""

  vertex_1_id: VertexID
  vertex_2_id: VertexID
  face_1_id: FaceID
  face_2_id: FaceID
  next_edge_1_id: EdgeID
  next_edge_2_id: EdgeID


class DCELBackend(TopologyBackend):
  def __init__(self) -> None:
    self._edge_nodes: dict[EdgeID, EdgeNode] = {}
    self._active_faces: set[FaceID] = set()
    self._active_vertices: set[VertexID] = set()

    # Navigation caches (Vertex/Face -> Any incident EdgeID)
    self._vertex_incident_edge: dict[VertexID, EdgeID] = {}
    self._face_incident_edge: dict[FaceID, EdgeID] = {}

    # ID Generators
    self._vertex_counter = itertools.count(1)
    self._face_counter = itertools.count(1)
    self._edge_counter = itertools.count(1)

  # -------------------------------------------------------------------------
  # Core CRUD
  # -------------------------------------------------------------------------
  def create_vertex(self) -> VertexID:
    vertex_id = VertexID(next(self._vertex_counter))
    self._active_vertices.add(vertex_id)
    return vertex_id

  def delete_vertex(self, vertex_id: VertexID) -> None:
    self._active_vertices.discard(vertex_id)
    self._vertex_incident_edge.pop(vertex_id, None)

  def create_face(self) -> FaceID:
    face_id = FaceID(next(self._face_counter))
    self._active_faces.add(face_id)
    return face_id

  def delete_face(self, face_id: FaceID) -> None:
    self._active_faces.discard(face_id)
    self._face_incident_edge.pop(face_id, None)

  def _create_edge_node(
    self,
    vertex_1_id: VertexID,
    vertex_2_id: VertexID,
    face_1_id: FaceID,
    face_2_id: FaceID,
    next_edge_1_id: EdgeID,
    next_edge_2_id: EdgeID,
  ) -> EdgeID:
    edge_id = EdgeID(next(self._edge_counter))
    self._edge_nodes[edge_id] = EdgeNode(
      vertex_1_id,
      vertex_2_id,
      face_1_id,
      face_2_id,
      next_edge_1_id,
      next_edge_2_id,
    )
    # Optimistically cache incident edges if missing
    if vertex_1_id not in self._vertex_incident_edge:
      self._vertex_incident_edge[vertex_1_id] = edge_id
    if vertex_2_id not in self._vertex_incident_edge:
      self._vertex_incident_edge[vertex_2_id] = edge_id
    if face_1_id not in self._face_incident_edge:
      self._face_incident_edge[face_1_id] = edge_id
    if face_2_id not in self._face_incident_edge:
      self._face_incident_edge[face_2_id] = edge_id
    return edge_id

  def _delete_edge_node(self, edge_id: EdgeID) -> None:
    del self._edge_nodes[edge_id]

  # -------------------------------------------------------------------------
  # Navigation / Trace
  # -------------------------------------------------------------------------
  def vertex_trace(self, vertex_id: VertexID) -> list[EdgeID]:
    """Returns ordered list of edges incident to vertex."""
    return list(self._vertex_trace_generator(vertex_id))

  def face_trace(self, face_id: FaceID) -> list[EdgeID]:
    """Returns ordered list of edges bounding the face."""
    return list(self._face_trace_generator(face_id))

  def _corner_from_edge_vertex(
    self, edge_id: EdgeID, vertex_id: VertexID
  ) -> Corner:
    node = self._edge_nodes[edge_id]
    if vertex_id not in (node.vertex_1_id, node.vertex_2_id):
      raise ValueError(
        f"Vertex {vertex_id} is not an endpoint of edge {edge_id}"
      )

    return Corner(
      vertex_id=vertex_id,
      face_id=node.face_1_id
      if vertex_id == node.vertex_1_id
      else node.face_2_id,
      edge_1_id=edge_id,
      edge_2_id=node.next_edge_1_id
      if vertex_id == node.vertex_1_id
      else node.next_edge_2_id,
    )

  # -------------------------------------------------------------------------
  # Iterators
  # -------------------------------------------------------------------------
  # -------------------------------------------------------------------------
  def get_vertices(self) -> list[VertexID]:
    return list(self._active_vertices)

  def get_faces(self) -> list[FaceID]:
    return list(self._active_faces)

  def get_face_vertices(self, face_id: FaceID) -> list[VertexID]:
    edges = list(self._face_trace_generator(face_id))
    if not edges:
      return []

    vertices = []
    for edge_id in edges:
      node = self._edge_nodes[edge_id]
      if node.face_1_id == face_id:
        vertices.append(node.vertex_1_id)
      elif node.face_2_id == face_id:
        vertices.append(node.vertex_2_id)
      else:
        continue
    return vertices

  def _vertex_trace_generator(
    self, vertex_id: VertexID
  ) -> Generator[EdgeID, None, None]:
    # Find start edge
    if vertex_id not in self._vertex_incident_edge:
      return
    start_edge_id = self._vertex_incident_edge[vertex_id]
    start_corner = self._corner_from_edge_vertex(start_edge_id, vertex_id)

    yield start_corner.edge_1_id

    curr_corner = self._corner_from_edge_vertex(
      start_corner.edge_2_id, vertex_id
    )
    while curr_corner != start_corner:
      yield curr_corner.edge_1_id
      curr_corner = self._corner_from_edge_vertex(
        curr_corner.edge_2_id, vertex_id
      )

  def _face_trace_generator(
    self, face_id: FaceID
  ) -> Generator[EdgeID, None, None]:
    if face_id not in self._face_incident_edge:
      return
    start_edge_id = self._face_incident_edge[face_id]
    yield from self._face_trace_from_edge(face_id, start_edge_id)

  # -------------------------------------------------------------------------
  # Operators (Insert/Delete Edge)
  # -------------------------------------------------------------------------
  # -------------------------------------------------------------------------
  # Helpers
  # -------------------------------------------------------------------------
  def _set_next_edge_around_vertex(
    self, prev_edge_id: EdgeID, vertex_id: VertexID, new_next_edge_id: EdgeID
  ) -> None:
    """Updates the 'next' pointer of the edge preceding the vertex in the rotation."""
    node = self._edge_nodes[prev_edge_id]
    if node.vertex_1_id == vertex_id:
      node.next_edge_1_id = new_next_edge_id
    elif node.vertex_2_id == vertex_id:
      node.next_edge_2_id = new_next_edge_id
    else:
      # Should not happen if topology is consistent
      raise ValueError(f"Vertex {vertex_id} not in edge {prev_edge_id}")

  def _replace_face_in_loop(
    self,
    old_face_id: FaceID,
    new_face_id: FaceID,
    start_edge_id: Optional[EdgeID] = None,
  ) -> None:
    """Updates face ID for all edges in a face or partial loop."""
    if not start_edge_id:
      # Use full trace if no specific start
      if old_face_id not in self._face_incident_edge:
        return
      start_edge_id = self._face_incident_edge[old_face_id]

    for edge_id in self._face_trace_from_edge(old_face_id, start_edge_id):
      node = self._edge_nodes[edge_id]
      if node.face_1_id == old_face_id:
        node.face_1_id = new_face_id
      if node.face_2_id == old_face_id:
        node.face_2_id = new_face_id

  def _create_edge_and_link(
    self, c1: Corner, c2: Corner
  ) -> Tuple[EdgeID, EdgeNode]:
    """Creates edge and links it to previous edges in vertex rotation."""
    edge_id = EdgeID(next(self._edge_counter))
    node = EdgeNode(
      vertex_1_id=c1.vertex_id,
      vertex_2_id=c2.vertex_id,
      face_1_id=c1.face_id,  # Temporary, updated by caller
      face_2_id=c2.face_id,  # Temporary, updated by caller
      next_edge_1_id=c1.edge_2_id,
      next_edge_2_id=c2.edge_2_id,
    )
    self._edge_nodes[edge_id] = node

    # Link previous edges to this new one
    self._set_next_edge_around_vertex(c1.edge_1_id, c1.vertex_id, edge_id)
    self._set_next_edge_around_vertex(c2.edge_1_id, c2.vertex_id, edge_id)

    # Update vertex cache (optimistic)
    self._vertex_incident_edge[c1.vertex_id] = edge_id
    self._vertex_incident_edge[c2.vertex_id] = edge_id

    return edge_id, node

  def _get_prev_edge(self, vertex_id: VertexID, edge_id: EdgeID) -> EdgeID:
    """Finds the edge preceding the given edge in the vertex's trace."""
    trace = list(self._vertex_trace_generator(vertex_id))
    if edge_id not in trace:
      raise ValueError(f"Edge {edge_id} not incident to vertex {vertex_id}")
    idx = trace.index(edge_id)
    # Previous in list (which is ordered rotation)
    return trace[(idx - 1) % len(trace)]

  def _face_trace_from_edge(
    self, face_id: FaceID, start_edge_id: EdgeID
  ) -> Generator[EdgeID, None, None]:
    """Generates edge IDs forming the boundary of the face."""
    yield start_edge_id

    node = self._edge_nodes[start_edge_id]
    
    # Start traversing from vertex_2 (arbitrary choice of direction).
    # If the face is on the left, this follows the boundary.
    # We find the *next* edge at the current vertex that shares the face.
    curr_vertex_id = node.vertex_2_id
    prev_edge_id = start_edge_id

    while True:
      # Find the edge emerging from curr_vertex_id that shares face_id
      # and is NOT the prev_edge_id (unless loop size is 1).
      
      # We scan the vertex rotation starting from prev_edge_id.
      # The 'other' edge sharing the face should be adjacent in rotation
      # (or close to it) in a valid manifold.
      
      try:
        c = self._corner_from_edge_vertex(prev_edge_id, curr_vertex_id)
      except ValueError:
        # Should not happen in consistent topology
        break

      found_next = None
      search_corner = c
      
      # Traverse rotation until we find the other edge sharing the face
      while True:
        next_cand = search_corner.edge_2_id
        if next_cand == prev_edge_id:
           # Completed rotation without finding another edge?
           break
        
        cand_node = self._edge_nodes[next_cand]
        if cand_node.face_1_id == face_id or cand_node.face_2_id == face_id:
           found_next = next_cand
           break
        
        search_corner = self._corner_from_edge_vertex(next_cand, curr_vertex_id)

      if found_next is None:
        break

      if found_next == start_edge_id:
        break

      yield found_next

      # Advance to the other vertex of the found edge
      prev_edge_id = found_next
      n_node = self._edge_nodes[found_next]
      if n_node.vertex_1_id == curr_vertex_id:
        curr_vertex_id = n_node.vertex_2_id
      else:
        curr_vertex_id = n_node.vertex_1_id

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
    c1 = self._corner_from_face_vertex(face_1_id, vertex_1_id)
    c2 = self._corner_from_face_vertex(face_2_id, vertex_2_id)

    edge_id, node = self._create_edge_and_link(c1, c2)

    if c1.face_id != c2.face_id:
      # Merge Faces
      new_face_id = self.create_face()
      self._replace_face_in_loop(c1.face_id, new_face_id)
      self._replace_face_in_loop(c2.face_id, new_face_id)

      node.face_1_id = new_face_id
      node.face_2_id = new_face_id

      self.delete_face(c1.face_id)
      self.delete_face(c2.face_id)
      self._face_incident_edge[new_face_id] = edge_id
      return (new_face_id, new_face_id)
    else:
      # Split Face
      old_face_id = c1.face_id
      f1_new = self.create_face()
      f2_new = self.create_face()

      # Update faces using partial loops
      self._replace_face_in_loop(
        old_face_id, f1_new, start_edge_id=c1.edge_2_id
      )
      self._replace_face_in_loop(
        old_face_id, f2_new, start_edge_id=c2.edge_2_id
      )

      node.face_1_id = f1_new
      node.face_2_id = f2_new  # Note: Order might depend on orientation, but for toplogy splitting this assigns sides.

      self.delete_face(old_face_id)
      self._face_incident_edge[f1_new] = edge_id
      self._face_incident_edge[f2_new] = edge_id
      return (f1_new, f2_new)

  def _corner_from_face_vertex(
    self, face_id: FaceID, vertex_id: VertexID
  ) -> Corner:
    # Find edge in vertex rotation that borders face_id
    for edge_id in self._vertex_trace_generator(vertex_id):
      node = self._edge_nodes[edge_id]
      if node.face_1_id == face_id:
        return self._corner_from_edge_vertex(edge_id, node.vertex_1_id)
      if node.face_2_id == face_id:
        return self._corner_from_edge_vertex(edge_id, node.vertex_2_id)
    raise ValueError(f"Vertex {vertex_id} not found in face {face_id}")

  def delete_edge(self, edge_id: EdgeID) -> None:
    node = self._edge_nodes[edge_id]
    v1, v2 = node.vertex_1_id, node.vertex_2_id
    f1, f2 = node.face_1_id, node.face_2_id

    # 1. Update vertex rotation pointers (remove edge from linked lists)
    v1_prev = self._get_prev_edge(v1, edge_id)
    v2_prev = self._get_prev_edge(v2, edge_id)

    # Identify next edges to link to
    v1_next = (
      node.next_edge_1_id if v1 == node.vertex_1_id else node.next_edge_2_id
    )
    v2_next = (
      node.next_edge_1_id if v2 == node.vertex_1_id else node.next_edge_2_id
    )

    self._set_next_edge_around_vertex(v1_prev, v1, v1_next)
    self._set_next_edge_around_vertex(v2_prev, v2, v2_next)

    # 2. Handle Face updates
    if f1 != f2:
      # Merging two adjacent faces
      new_face_id = self.create_face()
      # Relink loops
      self._replace_face_in_loop(f1, new_face_id)
      self._replace_face_in_loop(f2, new_face_id)

      self.delete_face(f1)
      self.delete_face(f2)

      # Use v1_prev as a safe seed for the new face
      if v1_prev != edge_id:
        self._face_incident_edge[new_face_id] = v1_prev

    else:
      # Splitting one face into two (removing a bridge/internal edge)
      new_f1 = self.create_face()
      new_f2 = self.create_face()

      # The loop splits; traverse from the two cut points
      self._replace_face_in_loop(f1, new_f1, start_edge_id=v1_prev)
      self._replace_face_in_loop(f1, new_f2, start_edge_id=v2_prev)

      self.delete_face(f1)

      if v1_prev != edge_id:
        self._face_incident_edge[new_f1] = v1_prev
      if v2_prev != edge_id:
        self._face_incident_edge[new_f2] = v2_prev

    # 3. Cleanup
    self._delete_edge_node(edge_id)

    # Update vertex incident edges if they pointed to deleted edge
    if self._vertex_incident_edge.get(v1) == edge_id:
      self._vertex_incident_edge[v1] = v1_prev
    if self._vertex_incident_edge.get(v2) == edge_id:
      self._vertex_incident_edge[v2] = v2_prev
