"""
FHIR Service Layer for AYUSH Medical Lookup System
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from sqlalchemy.orm import Session
from fastapi import Depends
from cryptography.fernet import Fernet
import json
import os

from fhir_models import (
    FHIRPatient, FHIRCondition, FHIRObservation, FHIRPractitioner,
    FHIRMedicationRequest, FHIRBundle, FHIRBundleEntry, FHIRResource,
    Identifier, HumanName, ContactPoint, Address, CodeableConcept, Reference
)
from db import LookupLog, get_db


# Encryption setup
ENCRYPTION_KEY = os.getenv("FHIR_ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    # Generate a key for development - in production, use a secure key management system
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    print(f"WARNING: Using generated encryption key. Set FHIR_ENCRYPTION_KEY environment variable for production.")

cipher = Fernet(ENCRYPTION_KEY.encode())


class FHIRService:
    def __init__(self, db: Session):
        self.db = db

    def _encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive patient data"""
        return cipher.encrypt(data.encode()).decode()

    def _decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive patient data"""
        return cipher.decrypt(encrypted_data.encode()).decode()

    def _create_identifier(self, system: str, value: str) -> Identifier:
        """Create a FHIR identifier"""
        return Identifier(system=system, value=value)

    def _create_reference(self, resource_type: str, resource_id: str, display: str = None) -> Reference:
        """Create a FHIR reference"""
        return Reference(
            reference=f"{resource_type}/{resource_id}",
            type=resource_type,
            display=display
        )

    def _create_codeable_concept(self, system: str, code: str, display: str) -> CodeableConcept:
        """Create a FHIR codeable concept"""
        concept = CodeableConcept()
        concept.add_coding(system, code, display)
        return concept

    # Patient operations
    def create_patient(self, patient_data: Dict[str, Any]) -> FHIRPatient:
        """Create a new patient resource"""
        # Encrypt sensitive fields
        if 'name' in patient_data and patient_data['name']:
            for name in patient_data['name']:
                if 'family' in name:
                    name['family'] = self._encrypt_sensitive_data(name['family'])
                if 'given' in name:
                    name['given'] = [self._encrypt_sensitive_data(g) for g in name['given']]

        if 'address' in patient_data and patient_data['address']:
            for addr in patient_data['address']:
                if 'line' in addr:
                    addr['line'] = [self._encrypt_sensitive_data(line) for line in addr['line']]

        patient = FHIRPatient(
            id=str(uuid.uuid4()),
            **patient_data
        )

        # Add AYUSH-specific identifier
        ayush_id = self._create_identifier(
            system="http://ayush.gov.in/identifier/patient",
            value=f"AYUSH-{patient.id}"
        )
        patient.identifier.append(ayush_id)

        return patient

    def get_patient(self, patient_id: str) -> Optional[FHIRPatient]:
        """Retrieve a patient by ID"""
        # In a real implementation, this would query the database
        # For now, return None as we don't have patient storage yet
        return None

    def search_patients(self, identifier: str = None, name: str = None) -> FHIRBundle:
        """Search for patients"""
        # In a real implementation, this would search the database
        # For now, return empty bundle
        return FHIRBundle(
            id=str(uuid.uuid4()),
            total=0,
            entry=[]
        )

    # Condition operations
    def create_condition_from_ayush_lookup(
        self,
        patient_id: str,
        disease_text: str,
        lookup_result: Dict[str, Any]
    ) -> FHIRCondition:
        """Create a FHIR Condition from AYUSH lookup results"""

        # Map AYUSH discipline to FHIR coding system
        discipline_mapping = {
            "Siddha": {
                "system": "http://ayush.gov.in/cs/siddha-conditions",
                "code": lookup_result.get("code", "UNKNOWN"),
                "display": lookup_result.get("label", disease_text)
            },
            "Unani": {
                "system": "http://ayush.gov.in/cs/unani-conditions",
                "code": lookup_result.get("code", "UNKNOWN"),
                "display": lookup_result.get("label", disease_text)
            },
            "Ayurveda": {
                "system": "http://ayush.gov.in/cs/ayurveda-conditions",
                "code": lookup_result.get("code", "UNKNOWN"),
                "display": lookup_result.get("label", disease_text)
            }
        }

        discipline = lookup_result.get("discipline", "Unknown")
        coding_info = discipline_mapping.get(discipline, {
            "system": "http://ayush.gov.in/cs/conditions",
            "code": "UNKNOWN",
            "display": disease_text
        })

        condition = FHIRCondition(
            id=str(uuid.uuid4()),
            clinicalStatus=self._create_codeable_concept(
                "http://terminology.hl7.org/CodeSystem/condition-clinical",
                "active",
                "Active"
            ),
            verificationStatus=self._create_codeable_concept(
                "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                "confirmed",
                "Confirmed"
            ),
            code=self._create_codeable_concept(
                coding_info["system"],
                coding_info["code"],
                coding_info["display"]
            ),
            subject=self._create_reference("Patient", patient_id, "Patient"),
            recordedDate=datetime.now(),
            note=[{
                "text": f"AYUSH lookup result: {lookup_result}",
                "time": datetime.now().isoformat()
            }]
        )

        # Add AYUSH-specific identifier
        condition_id = self._create_identifier(
            system="http://ayush.gov.in/identifier/condition",
            value=f"AYUSH-COND-{condition.id}"
        )
        condition.identifier.append(condition_id)

        return condition

    def search_conditions(self, patient_id: str = None, code: str = None) -> FHIRBundle:
        """Search for conditions"""
        # In a real implementation, this would search the database
        # For now, return empty bundle
        return FHIRBundle(
            id=str(uuid.uuid4()),
            total=0,
            entry=[]
        )

    # Observation operations
    def create_observation_from_symptoms(
        self,
        patient_id: str,
        symptoms: List[str],
        ayush_system: str = "general"
    ) -> FHIRObservation:
        """Create a FHIR Observation from patient symptoms"""

        observation = FHIRObservation(
            id=str(uuid.uuid4()),
            status="preliminary",
            code=self._create_codeable_concept(
                "http://loinc.org",
                "75325-1",
                "Symptom"
            ),
            subject=self._create_reference("Patient", patient_id, "Patient"),
            effectiveDateTime=datetime.now(),
            valueString="; ".join(symptoms),
            note=[{
                "text": f"AYUSH System: {ayush_system}",
                "time": datetime.now().isoformat()
            }]
        )

        # Add AYUSH-specific identifier
        obs_id = self._create_identifier(
            system="http://ayush.gov.in/identifier/observation",
            value=f"AYUSH-OBS-{observation.id}"
        )
        observation.identifier.append(obs_id)

        return observation

    # Medication Request operations
    def create_medication_request_from_ayush(
        self,
        patient_id: str,
        condition_id: str,
        ayush_recommendation: Dict[str, Any]
    ) -> FHIRMedicationRequest:
        """Create a FHIR MedicationRequest from AYUSH recommendations"""

        medication_request = FHIRMedicationRequest(
            id=str(uuid.uuid4()),
            status="active",
            intent="order",
            medicationCodeableConcept=self._create_codeable_concept(
                "http://ayush.gov.in/cs/medications",
                ayush_recommendation.get("code", "UNKNOWN"),
                ayush_recommendation.get("name", "AYUSH Medication")
            ),
            subject=self._create_reference("Patient", patient_id, "Patient"),
            reasonReference=[self._create_reference("Condition", condition_id, "Condition")],
            authoredOn=datetime.now(),
            note=[{
                "text": f"AYUSH recommendation: {ayush_recommendation}",
                "time": datetime.now().isoformat()
            }]
        )

        # Add AYUSH-specific identifier
        med_id = self._create_identifier(
            system="http://ayush.gov.in/identifier/medication-request",
            value=f"AYUSH-MED-{medication_request.id}"
        )
        medication_request.identifier.append(med_id)

        return medication_request

    # Utility methods
    def log_fhir_operation(
        self,
        operation: str,
        resource_type: str,
        resource_id: str,
        details: Dict[str, Any]
    ):
        """Log FHIR operations for audit purposes"""
        try:
            log_entry = LookupLog(
                patient_id=details.get("patient_id"),
                disease_text=f"FHIR {operation} {resource_type}/{resource_id}",
                result_json={
                    "operation": operation,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "details": details,
                    "timestamp": datetime.now().isoformat()
                }
            )
            self.db.add(log_entry)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"Failed to log FHIR operation: {e}")


# Global service instance
def get_fhir_service(db: Session = Depends(get_db)) -> FHIRService:
    """Dependency injection for FHIR service"""
    return FHIRService(db)
