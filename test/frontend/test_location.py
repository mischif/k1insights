import pytest


@pytest.mark.parametrize("location", ["atlanta", "moscow"])
def test_index(location, test_client):
    with test_client as c:
        res = c.get(f"/locations/{location}")
        html = res.data.decode()

        if location == "atlanta":
            assert "200 OK" == res.status
            assert 5 <= html.count("/locations/atlanta/karts/")
            assert 15 == html.count("/td")
        else:
            assert "404 NOT FOUND" == res.status
