from sqlalchemy.orm import Session

from onboardflow.adapters.persistence.database import OnboardingRunRecord, touch_record
from onboardflow.domain.models import OnboardingRun


class SqlAlchemyRunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save(self, run: OnboardingRun) -> None:
        payload = self._to_record_payload(run)
        record = self.session.get(OnboardingRunRecord, run.run_id)
        if record is None:
            record = OnboardingRunRecord(**payload)
            self.session.add(record)
        else:
            for key, value in payload.items():
                setattr(record, key, value)
            touch_record(record)
        self.session.commit()

    def get(self, run_id: str) -> OnboardingRun | None:
        record = self.session.get(OnboardingRunRecord, run_id)
        if record is None:
            return None
        return OnboardingRun.model_validate(
            {
                "runId": record.run_id,
                "status": record.status,
                "message": record.message,
                "inputData": record.input_data,
                "validationResult": record.validation_result,
                "result": record.result,
                "markdown": record.markdown,
                "errorMessage": record.error_message,
                "actionHistory": record.action_history,
                "dispatchReceipts": record.dispatch_receipts,
                "revisionNumber": record.revision_number,
                "createdAt": record.created_at,
                "updatedAt": record.updated_at,
            }
        )

    def _to_record_payload(self, run: OnboardingRun) -> dict:
        data = run.model_dump(mode="json", by_alias=True)
        return {
            "run_id": data["runId"],
            "status": data["status"],
            "message": data["message"],
            "input_data": data["inputData"],
            "validation_result": data.get("validationResult"),
            "result": data.get("result"),
            "markdown": data.get("markdown"),
            "error_message": data.get("errorMessage"),
            "action_history": data["actionHistory"],
            "dispatch_receipts": data["dispatchReceipts"],
            "revision_number": data["revisionNumber"],
            "created_at": run.created_at,
            "updated_at": run.updated_at,
        }
