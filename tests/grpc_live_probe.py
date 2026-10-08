"""Probe the running service with bindings freshly generated from its public proto."""
import importlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

import grpc


def main():
    try:
        with tempfile.TemporaryDirectory(prefix='grpc-client-') as tmp:
            subprocess.run([sys.executable, '-I', '-m', 'grpc_tools.protoc', '-I/app',
                '--python_out=' + tmp, '--grpc_python_out=' + tmp, '/app/kv-store.proto'],
                check=True, capture_output=True, timeout=10)
            sys.path.insert(0, tmp)
            messages = importlib.import_module('kv_store_pb2')
            binding = importlib.import_module('kv_store_pb2_grpc')
            key = 'evaluation-' + uuid.uuid4().hex
            with grpc.insecure_channel('127.0.0.1:5328') as channel:
                client = binding.KVStoreStub(channel)
                values = [client.SetVal(messages.SetValRequest(key=key, value=41), timeout=3).val,
                          client.GetVal(messages.GetValRequest(key=key), timeout=3).val,
                          client.SetVal(messages.SetValRequest(key=key, value=73), timeout=3).val,
                          client.GetVal(messages.GetValRequest(key=key), timeout=3).val]
            if values != [41, 41, 73, 73]:
                raise ValueError(f'Unexpected RPC results: {values}')
            print(json.dumps({'status': 'pass', 'values': values}))
            return 0
    except Exception as exc:
        print(json.dumps({'status': 'fail', 'error': str(exc)}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
