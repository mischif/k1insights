from k1stats.common.constants import LOCATIONS


def test_index(test_client):
    with test_client as c:
        res = c.get("/")
        assert "200 OK" == res.status
        html = res.data.decode()
        for loc in LOCATIONS:
            assert f'a href="/locations/{loc}"' in html
