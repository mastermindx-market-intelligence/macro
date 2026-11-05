import base64, hashlib, json, pathlib

def verify_proof(proof, release):
    assert proof['release'] == release, 'Wrong release'
    chain = proof['chain']
    assert chain and chain[0]['oid'] == proof['head'], 'Wrong installed head'
    assert chain[-1]['oid'] == release, 'Incomplete ancestry'
    for i, item in enumerate(chain):
        raw = base64.b64decode(item['raw_base64'], validate=True)
        oid = hashlib.sha1(b'commit ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        assert oid == item['oid'], 'Invalid commit object identity'
        parents = [line.split()[1].decode() for line in raw.split(b'\n\n', 1)[0].splitlines() if line.startswith(b'parent ')]
        if i + 1 < len(chain):
            assert parents and parents[0] == chain[i+1]['oid'], 'Broken parent edge'
    return proof

def load_proof(release):
    return verify_proof(json.loads(pathlib.Path(__file__).with_name('mmx-9041-installed-ancestry.json').read_text()), release)
