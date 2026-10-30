import hashlib
import json

from ML.readiness import public_datasets


def test_public_dataset_status_verifies_files_and_reports_missing_labels(tmp_path):
    data = tmp_path / 'DATA'
    data.mkdir()
    sample = data / 'sample.txt'
    sample.write_text('human reference', encoding='utf-8')
    entry = {'path': 'DATA/sample.txt', 'bytes': sample.stat().st_size,
             'sha256': hashlib.sha256(sample.read_bytes()).hexdigest()}
    source = {'id': 'reference', 'role': 'External reference; not support routing',
              'status': 'DOWNLOADED_VERIFIED_HASHES', 'files': [entry]}
    (data / 'public_sources.json').write_text(json.dumps({'sources': [source]}), encoding='utf-8')

    result = public_datasets(tmp_path)
    assert result['sources'][0]['ready'] is True
    assert result['bundled_routing_labels_available'] is False

    sample.write_text('changed', encoding='utf-8')
    result = public_datasets(tmp_path)
    assert result['sources'][0]['ready'] is False
    assert 'differs from pinned source' in result['sources'][0]['problems'][0]
