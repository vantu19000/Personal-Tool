"""Scratch check: repeated multipart parts + manual form parsing."""
from fastapi import FastAPI, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

app = FastAPI()


@app.post("/a")
async def a(request: Request):
    form = await request.form()
    return JSONResponse(
        {
            "text": str(form.get("text") or ""),
            "items": [
                {"key": str(k), "type": type(v).__name__, "mro": [c.__name__ for c in type(v).__mro__][:4]}
                for k, v in form.items()
            ],
        }
    )


c = TestClient(app)
B = "----smokeboundary"
parts = [("--%s\r\nContent-Disposition: form-data; name=\"text\"\r\n\r\nhello\r\n" % B).encode()]
for i, name in enumerate(("a.txt", "b.txt")):
    parts.append(
        (
            '--%s\r\nContent-Disposition: form-data; name="file_%d"; filename="%s"\r\n'
            "Content-Type: application/octet-stream\r\n\r\nfile-%s-content\r\n" % (B, i, name, name)
        ).encode()
    )
parts.append(("--%s--\r\n" % B).encode())
body = b"".join(parts)
r = c.post("/a", data=body, headers={"content-type": "multipart/form-data; boundary=%s" % B})
print(r.status_code, r.text)