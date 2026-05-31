from onboardflow.domain.models import EmployeeOnboardingInput


def test_employee_input_accepts_frontend_camel_case(employee_payload):
    employee = EmployeeOnboardingInput.model_validate(employee_payload)

    assert employee.full_name == "Ana Silva"
    assert employee.direct_manager == "Joaquim"
    assert employee.model_dump(mode="json", by_alias=True)["fullName"] == "Ana Silva"

