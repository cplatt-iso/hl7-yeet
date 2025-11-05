# Async Order Fan-Out Template

Use this reference template when you want a simulator run to emit HL7 orders synchronously and fan out the remaining work to RabbitMQ workers. Adjust IDs to match resources in your environment before posting to `/api/simulator/templates`.

```json
{
  "name": "Async ORM Fan-Out",
  "description": "Generates ORM orders and delegates DICOM work to workers via RabbitMQ.",
  "steps": [
    {
      "step_order": 1,
      "step_type": "GENERATE_HL7",
      "parameters": {
        "generator_template_id": 101,
        "accession_field": "OBR.3",
        "queue_async": true,
        "queue_metadata": {
          "priority": "STAT",
          "campaign": "nightly-load-test"
        }
      }
    },
    {
      "step_order": 2,
      "step_type": "GENERATE_DICOM",
      "parameters": {
        "count": 32,
        "generate_pixels": true,
        "burn_patient_info": false
      }
    },
    {
      "step_order": 3,
      "step_type": "SEND_DICOM",
      "parameters": {
        "endpoint_id": 17
      }
    },
    {
      "step_order": 4,
      "step_type": "WAIT",
      "parameters": {
        "duration_seconds": 2
      }
    }
  ]
}
```

## Notes

- `generator_template_id` should reference an existing ORM generator template that populates accession numbers.
- When the run executes, step 1 queues a job with the latest patient and order context. The Python runner stops there and marks the run `WAITING_ON_WORKERS`.
- Steps 2–4 are included in the queued payload so worker processes can regenerate DICOM, send it, and perform any throttling without blocking the main runner.
- Add or remove follow-on steps as needed; workers should respect the order shown in the `remaining_steps` array that is emitted with each job.
