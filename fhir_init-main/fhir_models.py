"""
FHIR Models for AYUSH Medical Lookup System
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class ResourceType(str, Enum):
    PATIENT = "Patient"
    CONDITION = "Condition"
    OBSERVATION = "Observation"
    PRACTITIONER = "Practitioner"
    MEDICATION_REQUEST = "MedicationRequest"
    ENCOUNTER = "Encounter"


class Identifier(BaseModel):
    system: Optional[str] = None
    value: str
    type: Optional[str] = None


class HumanName(BaseModel):
    use: Optional[str] = None
    family: Optional[str] = None
    given: List[str] = Field(default_factory=list)
    prefix: List[str] = Field(default_factory=list)
    suffix: List[str] = Field(default_factory=list)


class Address(BaseModel):
    use: Optional[str] = None
    type: Optional[str] = None
    line: List[str] = Field(default_factory=list)
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None


class ContactPoint(BaseModel):
    system: Optional[str] = None  # phone, email, etc.
    value: str
    use: Optional[str] = None
    rank: Optional[int] = None


class CodeableConcept(BaseModel):
    coding: List[Dict[str, Any]] = Field(default_factory=list)
    text: Optional[str] = None

    def add_coding(self, system: str, code: str, display: str):
        self.coding.append({
            "system": system,
            "code": code,
            "display": display
        })


class Quantity(BaseModel):
    value: Optional[float] = None
    unit: Optional[str] = None
    system: Optional[str] = None
    code: Optional[str] = None


class Period(BaseModel):
    start: Optional[datetime] = None
    end: Optional[datetime] = None


class Reference(BaseModel):
    reference: str
    type: Optional[str] = None
    identifier: Optional[Identifier] = None
    display: Optional[str] = None


# Base FHIR Resource
class FHIRResource(BaseModel):
    resourceType: str
    id: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    identifier: List[Identifier] = Field(default_factory=list)


# Patient Resource
class FHIRPatient(FHIRResource):
    resourceType: str = "Patient"
    identifier: List[Identifier] = Field(default_factory=list)
    active: Optional[bool] = True
    name: List[HumanName] = Field(default_factory=list)
    telecom: List[ContactPoint] = Field(default_factory=list)
    gender: Optional[str] = None
    birthDate: Optional[str] = None
    address: List[Address] = Field(default_factory=list)
    managingOrganization: Optional[Reference] = None


# Condition Resource
class FHIRCondition(FHIRResource):
    resourceType: str = "Condition"
    identifier: List[Identifier] = Field(default_factory=list)
    clinicalStatus: Optional[CodeableConcept] = None
    verificationStatus: Optional[CodeableConcept] = None
    category: List[CodeableConcept] = Field(default_factory=list)
    severity: Optional[CodeableConcept] = None
    code: CodeableConcept
    bodySite: List[CodeableConcept] = Field(default_factory=list)
    subject: Reference  # Reference to Patient
    encounter: Optional[Reference] = None
    onsetDateTime: Optional[datetime] = None
    onsetString: Optional[str] = None
    recordedDate: Optional[datetime] = None
    recorder: Optional[Reference] = None
    asserter: Optional[Reference] = None
    note: List[Dict[str, Any]] = Field(default_factory=list)


# Observation Resource
class FHIRObservation(FHIRResource):
    resourceType: str = "Observation"
    identifier: List[Identifier] = Field(default_factory=list)
    status: str = "final"
    category: List[CodeableConcept] = Field(default_factory=list)
    code: CodeableConcept
    subject: Reference  # Reference to Patient
    encounter: Optional[Reference] = None
    effectiveDateTime: Optional[datetime] = None
    effectivePeriod: Optional[Period] = None
    issued: Optional[datetime] = None
    performer: List[Reference] = Field(default_factory=list)
    valueQuantity: Optional[Quantity] = None
    valueString: Optional[str] = None
    valueCodeableConcept: Optional[CodeableConcept] = None
    interpretation: List[CodeableConcept] = Field(default_factory=list)
    note: List[Dict[str, Any]] = Field(default_factory=list)
    bodySite: Optional[CodeableConcept] = None
    method: Optional[CodeableConcept] = None
    referenceRange: List[Dict[str, Any]] = Field(default_factory=list)


# Practitioner Resource
class FHIRPractitioner(FHIRResource):
    resourceType: str = "Practitioner"
    identifier: List[Identifier] = Field(default_factory=list)
    active: Optional[bool] = True
    name: List[HumanName] = Field(default_factory=list)
    telecom: List[ContactPoint] = Field(default_factory=list)
    address: List[Address] = Field(default_factory=list)
    gender: Optional[str] = None
    birthDate: Optional[str] = None
    qualification: List[Dict[str, Any]] = Field(default_factory=list)


# MedicationRequest Resource
class FHIRMedicationRequest(FHIRResource):
    resourceType: str = "MedicationRequest"
    identifier: List[Identifier] = Field(default_factory=list)
    status: str = "active"
    intent: str = "order"
    medicationCodeableConcept: Optional[CodeableConcept] = None
    medicationReference: Optional[Reference] = None
    subject: Reference  # Reference to Patient
    encounter: Optional[Reference] = None
    authoredOn: Optional[datetime] = None
    requester: Optional[Reference] = None
    reasonCode: List[CodeableConcept] = Field(default_factory=list)
    reasonReference: List[Reference] = Field(default_factory=list)
    note: List[Dict[str, Any]] = Field(default_factory=list)
    dosageInstruction: List[Dict[str, Any]] = Field(default_factory=list)


# Bundle Resource for search results
class FHIRBundleEntry(BaseModel):
    fullUrl: Optional[str] = None
    resource: FHIRResource
    search: Optional[Dict[str, Any]] = None


class FHIRBundle(BaseModel):
    resourceType: str = "Bundle"
    id: Optional[str] = None
    type: str = "searchset"
    total: Optional[int] = None
    entry: List[FHIRBundleEntry] = Field(default_factory=list)
    meta: Optional[Dict[str, Any]] = None


# Request/Response models for API
class FHIRSearchRequest(BaseModel):
    resource_type: str
    patient_id: Optional[str] = None
    identifier: Optional[str] = None
    code: Optional[str] = None
    limit: int = 10
    offset: int = 0


class FHIRCreateRequest(BaseModel):
    resource_type: str
    resource_data: Dict[str, Any]


class FHIRUpdateRequest(BaseModel):
    resource_type: str
    resource_id: str
    resource_data: Dict[str, Any]


class FHIRDeleteRequest(BaseModel):
    resource_type: str
    resource_id: str
