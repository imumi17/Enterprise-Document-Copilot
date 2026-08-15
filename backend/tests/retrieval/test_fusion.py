from uuid import UUID

from app.retrieval.fusion import reciprocal_rank_fusion


def test_reciprocal_rank_fusion_combines_lists():
    a = UUID("00000000-0000-0000-0000-000000000001")
    b = UUID("00000000-0000-0000-0000-000000000002")
    c = UUID("00000000-0000-0000-0000-000000000003")

    fused = reciprocal_rank_fusion([[a, b], [b, c]])

    assert fused[0][0] == b
    assert fused[0][1] > fused[1][1]
    assert {item[0] for item in fused} == {a, b, c}


def test_reciprocal_rank_fusion_empty_input():
    assert reciprocal_rank_fusion([]) == []
