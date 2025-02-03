from trakt.api import HttpClient
from trakt.core import api
from trakt.tv import TVShow


def test_api_singleton():
    """Test that api() returns the same HttpClient instance when called multiple times."""
    api1 = api()
    api2 = api()
    assert isinstance(api1, HttpClient), "api() should return an HttpClient instance"
    assert api1 == api2, "Multiple calls to api() should return the same instance"


def test_tvshow_properties():
    show = TVShow("Game of Thrones")
    assert show.title == "Game of Thrones"
    assert show.certification == "TV-MA"
