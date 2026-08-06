import sys
sys.path.insert(0, '.')
import json
from database import JobResult, unwrap_duplicati_json

# Payload real capturado do MySQL ID 47
payload_id47 = {"Data": "{\"DeletedFiles\": 0, \"DeletedFolders\": 0, \"ModifiedFiles\": 5, \"ExaminedFiles\": 13465, \"OpenedFiles\": 28, \"AddedFiles\": 23, \"SizeOfModifiedFiles\": 2596352, \"SizeOfAddedFiles\": 558783791, \"SizeOfExaminedFiles\": 58043169278, \"SizeOfOpenedFiles\": 561380143, \"NotProcessedFiles\": 0}"}

jr = JobResult(raw_payload=json.dumps(payload_id47))
stats = jr.extract_detailed_stats()

print("Payload ID 47 - Unwrapped:")
print(json.dumps(unwrap_duplicati_json(payload_id47), indent=2))
print("\nExtracted Stats:")
print(stats)
