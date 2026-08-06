import json
from database import unwrap_duplicati_json, JobResult

sample = {"Data": '{"DeletedFiles": 0, "ModifiedFiles": 5, "ExaminedFiles": 13465, "OpenedFiles": 28, "AddedFiles": 23, "SizeOfModifiedFiles": 2596352, "SizeOfAddedFiles": 558783791, "SizeOfExaminedFiles": 58043169278, "Warnings": ["Backend manager queue runner did not stop"]}'}

res = unwrap_duplicati_json(sample)
print("Unwrapped dict:", res)

jr = JobResult(raw_payload=json.dumps(sample))
stats = jr.extract_detailed_stats()
print("Extracted stats:", stats)
