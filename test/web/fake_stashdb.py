from test.web.parrot_webserver import ParrotWebServer


def make_fake_stashdb() -> ParrotWebServer:
    server = ParrotWebServer()

    # Single sample scene payload reused across handlers
    def sample_scene(base_url: str):
        return {
            "id": "s1",
            "title": "Sample Scene",
            "date": "2022-01-01",
            "urls": [{"url": "https://example.com/scene/s1"}],
            "details": "This is a sample StashDB fake scene.",
            "duration": 600,
            "images": [{"url": f"{base_url}/poster.png"}],
            "studio": {
                "name": "Sample Studio",
                "parent": {"name": "Sample Network"},
            },
            "performers": [
                {"name": "Actor One", "gender": "FEMALE"},
                {"name": "Actor Two", "gender": "MALE"},
            ],
            "tags": [{"name": "Tag1"}, {"name": "Tag2"}],
            "fingerprints": [
                {"hash": "abcdef123456", "algorithm": "PHASH", "duration": 600}
            ],
        }

    def handle_graphql_request():
        try:
            import orjson
            from flask import request as flask_request

            req = orjson.loads(flask_request.get_data())
            query: str = req.get("query", "") or ""
            variables = req.get("variables", {}) or {}

            # Determine response shape
            base_url = server.get_url()
            scene = sample_scene(base_url)

            if "searchScene" in query:
                return orjson.dumps({
                    "data": {
                        "searchScene": [scene]
                    }
                }).decode("utf-8")

            if "findScene" in query:
                scene_id = variables.get("id", "")
                return orjson.dumps({
                    "data": {
                        "findScene": scene if scene_id in ("s1", "1678283") else None
                    }
                }).decode("utf-8")

            if "findSceneByFingerprint" in query or "SearchByFingerprint" in query:
                fp = variables.get("fingerprint") or {}
                hash_val = fp.get("hash") or variables.get("hash")
                data = [scene] if hash_val == "abcdef123456" else []
                return orjson.dumps({
                    "data": {
                        "findSceneByFingerprint": data
                    }
                }).decode("utf-8")

            if "me" in query:
                return orjson.dumps({
                    "data": {
                        "me": {"id": "u1", "name": "stash-user", "roles": ["USER"]}
                    }
                }).decode("utf-8")

            return orjson.dumps({"data": None}).decode("utf-8")
        except Exception as e:
            import orjson
            return orjson.dumps({
                "errors": [{"message": f"GraphQL error: {str(e)}"}]
            }).decode("utf-8")

    # Register GraphQL endpoint
    server.set_response("/graphql", handle_graphql_request)
    server.set_response("/graphql?", handle_graphql_request)

    # Static poster asset used by tests
    try:
        from pathlib import Path
        test_dir = Path(__file__).resolve().parent
        poster_bytes = (test_dir / "poster.png").read_bytes()
        server.set_response("/poster.png", bytearray(poster_bytes))
    except Exception:
        pass

    return server
