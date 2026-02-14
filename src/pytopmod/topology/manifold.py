from abc import ABC, abstractmethod
from typing import Tuple

from pytopmod.topology.types import EdgeID, FaceID, VertexID



# -----------------------------------------------------------------------------
# Interface
# -----------------------------------------------------------------------------
class TopologyBackend(ABC):
  """Abstract base class for topology storage backends (e.g. DCEL, DLFL)."""

  @abstractmethod
  def create_vertex(self) -> VertexID:
    """Creates a new vertex."""

  @abstractmethod
  def delete_vertex(self, vertex_id: VertexID) -> None:
    """Deletes a vertex."""

  @abstractmethod
  def create_face(self) -> FaceID:
    """Creates a new face."""

  @abstractmethod
  def delete_face(self, face_id: FaceID) -> None:
    """Deletes a face."""

  @abstractmethod
  def insert_edge(
    self,
    vertex_1_id: VertexID,
    face_1_id: FaceID,
    vertex_2_id: VertexID,
    face_2_id: FaceID,
  ) -> Tuple[
    FaceID, FaceID
  ]:  # Returns new/modified faces? Or just generic outcome?
    # The return signature might need refinement based on exact operator needs
    # For now, let's assume it matches the logic of "split face" or "merge faces"
    # and returns the resulting face IDs.
    pass

  @abstractmethod
  def delete_edge(self, edge_id: EdgeID) -> None:
    """Deletes an edge."""

  # Trace methods are crucial for navigation
  @abstractmethod
  def vertex_trace(self, vertex_id: VertexID) -> list[EdgeID]:  # Or generator
    """Returns edges incident to vertex."""

  @abstractmethod
  def face_trace(self, face_id: FaceID) -> list[EdgeID]:
    """Returns edges bounding the face."""

  # -------------------------------------------------------------------------
  # Iterators
  # -------------------------------------------------------------------------
  @abstractmethod
  def get_vertices(self) -> list[VertexID]:
    """Returns all vertex IDs."""

  @abstractmethod
  def get_faces(self) -> list[FaceID]:
    """Returns all face IDs."""

  @abstractmethod
  def get_face_vertices(self, face_id: FaceID) -> list[VertexID]:
    """Returns vertices of a face in order."""


class Manifold:
  """The main topological object, representing a 2-manifold.

  It delegates storage and topological operations to a TopologyBackend.
  """

  def __init__(self, backend: TopologyBackend):
    self._backend = backend

  def create_vertex(self) -> VertexID:
    return self._backend.create_vertex()

  def delete_vertex(self, vertex_id: VertexID) -> None:
    self._backend.delete_vertex(vertex_id)

  def create_face(self) -> FaceID:
    return self._backend.create_face()

  def delete_face(self, face_id: FaceID) -> None:
    self._backend.delete_face(face_id)

  def insert_edge(
    self,
    vertex_1_id: VertexID,
    face_1_id: FaceID,
    vertex_2_id: VertexID,
    face_2_id: FaceID,
  ) -> Tuple[FaceID, FaceID]:
    return self._backend.insert_edge(
      vertex_1_id, face_1_id, vertex_2_id, face_2_id
    )

  def delete_edge(self, edge_id: EdgeID) -> None:
    self._backend.delete_edge(edge_id)

  def vertex_trace(self, vertex_id: VertexID) -> list[EdgeID]:
    return self._backend.vertex_trace(vertex_id)

  def face_trace(self, face_id: FaceID) -> list[EdgeID]:
    return self._backend.face_trace(face_id)



  def get_vertices(self) -> list[VertexID]:
    return self._backend.get_vertices()

  def get_faces(self) -> list[FaceID]:
    return self._backend.get_faces()

  def get_face_vertices(self, face_id: FaceID) -> list[VertexID]:
    return self._backend.get_face_vertices(face_id)
