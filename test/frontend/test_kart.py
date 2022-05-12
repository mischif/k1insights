import pytest


@pytest.mark.parametrize(
    "location, valid_kart", [["atlanta", True], ["atlanta", False], ["moscow", False]]
)
def test_index(location, valid_kart, test_client):
    with test_client as c:
        if not valid_kart:
            res = c.get(f"/locations/{location}/karts/-1")
            assert "404 NOT FOUND" == res.status
        else:
            res = c.get(f"/locations/{location}")
            html = res.data.decode()
            kart = int(html.split("<td>")[1][0])

            res = c.get(f"/locations/{location}/karts/{kart}")
            html = res.data.decode()

            assert "200 OK" == res.status
            assert 1 <= html.count("/td")
