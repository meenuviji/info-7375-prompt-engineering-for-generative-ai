
def test_no_credentials_sent_from_netrc(tmp_path, monkeypatch):
    import requests
    import requests.adapters
    import requests.models
    from src.fetch import RequestsTransport

    # Create a fake netrc file with credentials
    netrc_file = tmp_path / "netrc"
    netrc_file.write_text(
        "machine boards-api.greenhouse.io login fakeuser password fakepass"
    )
    monkeypatch.setenv("NETRC", str(netrc_file))

    # Capture the request without actually sending it
    sent = []

    def fake_send(self, request, **kwargs):
        sent.append(request)

        resp = requests.models.Response()
        resp.status_code = 200
        resp._content = b'{"jobs": [], "meta": {"total": 0}}'
        resp.url = request.url
        resp.request = request
        return resp

    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", fake_send)

    # Make the request through the transport
    RequestsTransport().get(
        "https://boards-api.greenhouse.io/v1/boards/cloudflare/jobs",
        timeout=5
    )

    # Check that only one request was made
    assert len(sent) == 1

    # Make sure credentials were not added to the request
    assert "Authorization" not in sent[0].headers, (
        f"Authorization header leaked: {dict(sent[0].headers)}"
    )
