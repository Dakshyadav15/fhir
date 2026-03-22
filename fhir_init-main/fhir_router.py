"""
FHIR REST API Router for AYUSH Medical Lookup System
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import json

from fastapi import APIRouter, HTTPException, Depends, Query, Path, Body
from sqlalchemy.orm import Session

from fhir_models import (
    FHIRPatient, FHIRCondition, FHIRObservation, FHIRPractitioner,
    FHIRMedicationRequest, FHIRBundle, FHIRSearchRequest, FHIRCreateRequest,
    FHIRUpdateRequest, FHIRDeleteRequest
)
from fhir_service import get_fhir_service, FHIRService
from db import get_db

# Create FHIR router
fhir_router = APIRouter(prefix="/fhir", tags=["FHIR"])


# Patient endpoints
@fhir_router.post("/Patient", response_model=FHIRPatient)
async def create_patient(
    patient_data: Dict[str, Any] = Body(...),
    fhir_service: FHIRService = Depends(get_fhir_service),
    db: Session = Depends(get_db)
):
    """Create a new Patient resource"""
    try:
        patient = fhir_service.create_patient(patient_data)
        fhir_service.log_fhir_operation("CREATE", "Patient", patient.id, {"patient_id": patient.id})
        return patient
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create patient: {str(e)}")


@fhir_router.get("/Patient/{patient_id}", response_model=FHIRPatient)
async def get_patient(
    patient_id: str = Path(..., description="Patient ID"),
    fhir_service: FHIRService = Depends(get_fhir_service)
):
    """Read a Patient resource"""
    patient = fhir_service.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@fhir_router.get("/Patient", response_model=FHIRBundle)
async def search_patients(
    identifier: Optional[str] = Query(None, description="Patient identifier"),
    family: Optional[str] = Query(None, description="Family name"),
    given: Optional[str] = Query(None, description="Given name"),
    fhir_service: FHIRService = Depends(get_fhir_service)
):
    """Search Patient resources"""
    return fhir_service.search_patients(identifier=identifier, name=f"{family} {given}" if family or given else None)


# Condition endpoints
@fhir_router.post("/Condition", response_model=FHIRCondition)
async def create_condition(
    condition_data: Dict[str, Any] = Body(...),
    fhir_service: FHIRService = Depends(get_fhir_service),
    db: Session = Depends(get_db)
):
    """Create a new Condition resource"""
    try:
        condition = FHIRCondition(**condition_data)
        fhir_service.log_fhir_operation("CREATE", "Condition", condition.id, {"patient_id": condition.subject.reference})
        return condition
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create condition: {str(e)}")


@fhir_router.get("/Condition/{condition_id}", response_model=FHIRCondition)
async def get_condition(
    condition_id: str = Path(..., description="Condition ID"),
    fhir_service: FHIRService = Depends(get_fhir_service)
):
    """Read a Condition resource"""
    # In a real implementation, this would retrieve from database
    raise HTTPException(status_code=404, detail="Condition not found")


@fhir_router.get("/Condition", response_model=FHIRBundle)
async def search_conditions(
    patient: Optional[str] = Query(None, description="Patient reference"),
    code: Optional[str] = Query(None, description="Condition code"),
    fhir_service: FHIRService = Depends(get_fhir_service)
):
    """Search Condition resources"""
    return fhir_service.search_conditions(patient_id=patient, code=code)


# Observation endpoints
@fhir_router.post("/Observation", response_model=FHIRObservation)
async def create_observation(
    observation_data: Dict[str, Any] = Body(...),
    fhir_service: FHIRService = Depends(get_fhir_service),
    db: Session = Depends(get_db)
):
    """Create a new Observation resource"""
    try:
        observation = FHIRObservation(**observation_data)
        fhir_service.log_fhir_operation("CREATE", "Observation", observation.id, {"patient_id": observation.subject.reference})
        return observation
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create observation: {str(e)}")


@fhir_router.get("/Observation/{observation_id}", response_model=FHIRObservation)
async def get_observation(
    observation_id: str = Path(..., description="Observation ID"),
    fhir_service: FHIRService = Depends(get_fhir_service)
):
    """Read an Observation resource"""
    # In a real implementation, this would retrieve from database
    raise HTTPException(status_code=404, detail="Observation not found")


@fhir_router.get("/Observation", response_model=FHIRBundle)
async def search_observations(
    patient: Optional[str] = Query(None, description="Patient reference"),
    code: Optional[str] = Query(None, description="Observation code"),
    fhir_service: FHIRService = Depends(get_fhir_service)
):
    """Search Observation resources"""
    # In a real implementation, this would search the database
    return FHIRBundle(id="search-results", total=0, entry=[])


# MedicationRequest endpoints
@fhir_router.post("/MedicationRequest", response_model=FHIRMedicationRequest)
async def create_medication_request(
    medication_request_data: Dict[str, Any] = Body(...),
    fhir_service: FHIRService = Depends(get_fhir_service),
    db: Session = Depends(get_db)
):
    """Create a new MedicationRequest resource"""
    try:
        medication_request = FHIRMedicationRequest(**medication_request_data)
        fhir_service.log_fhir_operation("CREATE", "MedicationRequest", medication_request.id, {"patient_id": medication_request.subject.reference})
        return medication_request
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create medication request: {str(e)}")


@fhir_router.get("/MedicationRequest/{medication_request_id}", response_model=FHIRMedicationRequest)
async def get_medication_request(
    medication_request_id: str = Path(..., description="MedicationRequest ID"),
    fhir_service: FHIRService = Depends(get_fhir_service)
):
    """Read a MedicationRequest resource"""
    # In a real implementation, this would retrieve from database
    raise HTTPException(status_code=404, detail="MedicationRequest not found")


@fhir_router.get("/MedicationRequest", response_model=FHIRBundle)
async def search_medication_requests(
    patient: Optional[str] = Query(None, description="Patient reference"),
    fhir_service: FHIRService = Depends(get_fhir_service)
):
    """Search MedicationRequest resources"""
    # In a real implementation, this would search the database
    return FHIRBundle(id="search-results", total=0, entry=[])


# Enhanced AYUSH-specific endpoints
@fhir_router.post("/ayush/lookup-to-fhir")
async def ayush_lookup_to_fhir(
    patient_id: str = Body(..., description="Patient ID for the lookup"),
    disease_text: str = Body(..., description="Disease or symptom description"),
    ayush_system: Optional[str] = Body("general", description="AYUSH system preference"),
    lookup_result: Dict[str, Any] = Body(..., description="AYUSH lookup result"),
    fhir_service: FHIRService = Depends(get_fhir_service),
    db: Session = Depends(get_db)
):
    """
    Convert AYUSH lookup results to FHIR resources

    This endpoint takes AYUSH lookup results and creates corresponding FHIR resources:
    - Condition resource for the disease/condition
    - Observation resource for symptoms
    - MedicationRequest resource for recommendations
    """
    try:
        # Create Condition from lookup result
        condition = fhir_service.create_condition_from_ayush_lookup(
            patient_id, disease_text, lookup_result
        )

        # Create Observation for symptoms (extract from disease text)
        symptoms = [disease_text]  # In a real implementation, extract symptoms from text
        observation = fhir_service.create_observation_from_symptoms(
            patient_id, symptoms, ayush_system
        )

        # Create MedicationRequest if recommendations exist
        medication_request = None
        if "recommendations" in lookup_result:
            medication_request = fhir_service.create_medication_request_from_ayush(
                patient_id, condition.id, lookup_result["recommendations"]
            )

        # Log the operation
        fhir_service.log_fhir_operation(
            "AYUSH_LOOKUP_CONVERSION",
            "Bundle",
            "ayush-conversion",
            {
                "patient_id": patient_id,
                "disease_text": disease_text,
                "resources_created": {
                    "condition": condition.id,
                    "observation": observation.id,
                    "medication_request": medication_request.id if medication_request else None
                }
            }
        )

        # Return bundle with created resources
        bundle = FHIRBundle(
            id=str(uuid.uuid4()),
            total=3 if medication_request else 2,
            entry=[
                FHIRBundleEntry(
                    fullUrl=f"urn:uuid:{condition.id}",
                    resource=condition
                ),
                FHIRBundleEntry(
                    fullUrl=f"urn:uuid:{observation.id}",
                    resource=observation
                )
            ]
        )

        if medication_request:
            bundle.entry.append(
                FHIRBundleEntry(
                    fullUrl=f"urn:uuid:{medication_request.id}",
                    resource=medication_request
                )
            )

        return bundle

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to convert AYUSH lookup to FHIR: {str(e)}")


@fhir_router.get("/ayush/capabilities")
async def get_ayush_fhir_capabilities():
    """Get AYUSH-specific FHIR capabilities"""
    return {
        "resourceType": "CapabilityStatement",
        "id": "ayush-fhir-capabilities",
        "status": "active",
        "date": datetime.now().isoformat(),
        "kind": "instance",
        "software": {
            "name": "AYUSH FHIR Server",
            "version": "1.0.0",
            "releaseDate": datetime.now().isoformat()
        },
        "implementation": {
            "description": "AYUSH Medical Lookup System with FHIR Integration",
            "url": "http://localhost:8000/fhir"
        },
        "fhirVersion": "4.0.1",
        "format": ["json", "xml"],
        "rest": [{
            "mode": "server",
            "resource": [
                {
                    "type": "Patient",
                    "interaction": [
                        {"code": "create"},
                        {"code": "read"},
                        {"code": "search-type"}
                    ]
                },
                {
                    "type": "Condition",
                    "interaction": [
                        {"code": "create"},
                        {"code": "read"},
                        {"code": "search-type"}
                    ]
                },
                {
                    "type": "Observation",
                    "interaction": [
                        {"code": "create"},
                        {"code": "read"},
                        {"code": "search-type"}
                    ]
                },
                {
                    "type": "MedicationRequest",
                    "interaction": [
                        {"code": "create"},
                        {"code": "read"},
                        {"code": "search-type"}
                    ]
                }
            ],
            "interaction": [
                {"code": "batch"},
                {"code": "search-system"}
            ]
        }],
        "ayush_extensions": {
            "supported_systems": ["Siddha", "Unani", "Ayurveda"],
            "traditional_medicine_codes": True,
            "symptom_analysis": True,
            "lookup_integration": True
        }
    }


# Error handlers
async def fhir_not_found_handler(request, exc):
    """Handle FHIR resource not found errors"""
    return {
        "resourceType": "OperationOutcome",
        "issue": [{
            "severity": "error",
            "code": "not-found",
            "details": {"text": str(exc.detail)},
            "expression": [request.url.path]
        }]
    }


async def fhir_bad_request_handler(request, exc):
    """Handle FHIR validation errors"""
    return {
        "resourceType": "OperationOutcome",
        "issue": [{
            "severity": "error",
            "code": "invalid",
            "details": {"text": str(exc.detail)},
            "expression": [request.url.path]
        }]
    }
