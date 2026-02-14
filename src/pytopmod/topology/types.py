import dataclasses
from typing import NewType

# -----------------------------------------------------------------------------
# IDs
# -----------------------------------------------------------------------------
VertexID = NewType("VertexID", int)
FaceID = NewType("FaceID", int)
EdgeID = NewType("EdgeID", int)


# -----------------------------------------------------------------------------
# Handles
# -----------------------------------------------------------------------------
@dataclasses.dataclass(slots=True)
class Corner:
  """A Corner represents a handle to a specific part of the topology.

  It is defined by a vertex, a face, and the two edges incident to the vertex
  in that face.
  """

  vertex_id: VertexID
  face_id: FaceID
  edge_1_id: EdgeID
  edge_2_id: EdgeID

  def __repr__(self) -> str:
    return (
      f"Corner(v={self.vertex_id}, f={self.face_id}, "
      f"e1={self.edge_1_id}, e2={self.edge_2_id})"
    )
