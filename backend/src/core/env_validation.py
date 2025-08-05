"""
Environment Variable Validation and Management

Provides utilities for validating and managing environment variables
across the application with consistent error handling.
"""

import os
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass

from core.logging_utils import get_logger
from core.error_handling import ConfigurationError


@dataclass
class EnvVarRequirement:
    """Define requirements for an environment variable"""
    name: str
    required: bool = True
    default: Optional[str] = None
    description: str = ""
    validation_regex: Optional[str] = None
    choices: Optional[List[str]] = None


class EnvironmentValidator:
    """Centralized environment variable validation"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self._requirements: Dict[str, EnvVarRequirement] = {}
        
        # Define standard requirements
        self._define_standard_requirements()
    
    def _define_standard_requirements(self):
        """Define standard environment variable requirements"""
        requirements = [
            # Security requirements
            EnvVarRequirement(
                "NEXTAUTH_SECRET",
                required=True,
                description="NextAuth.js secret for JWT signing"
            ),
            EnvVarRequirement(
                "SECRET_KEY",
                required=False,
                default="dev-secret-key-change-in-production",
                description="Flask secret key"
            ),
            
            # Environment settings
            EnvVarRequirement(
                "ENVIRONMENT",
                required=False,
                default="development",
                description="Application environment",
                choices=["development", "staging", "production"]
            ),
            EnvVarRequirement(
                "DEBUG",
                required=False,
                default="False",
                description="Enable debug mode",
                choices=["True", "False", "true", "false", "1", "0"]
            ),
            
            # Server settings
            EnvVarRequirement(
                "HOST",
                required=False,
                default="localhost",
                description="Server host"
            ),
            EnvVarRequirement(
                "PORT",
                required=False,
                default="5000",
                description="Server port"
            ),
            
            # API Keys (optional but recommended)
            EnvVarRequirement(
                "OPENAI_API_KEY",
                required=False,
                description="OpenAI API key for AI functionality"
            ),
            EnvVarRequirement(
                "UNSPLASH_ACCESS_KEY",
                required=False,
                description="Unsplash API key for image integration"
            ),
            EnvVarRequirement(
                "SERPER_API_KEY",
                required=False,
                description="Serper API key for search functionality"
            ),
            
            # URLs and domains
            EnvVarRequirement(
                "FRONTEND_URL",
                required=False,
                description="Frontend application URL"
            ),
            EnvVarRequirement(
                "NEXTAUTH_URL",
                required=False,
                default="http://localhost:3001",
                description="NextAuth.js URL"
            ),
            EnvVarRequirement(
                "DATABASE_URL",
                required=False,
                description="Database connection URL"
            ),
        ]
        
        for req in requirements:
            self._requirements[req.name] = req
    
    def add_requirement(self, requirement: EnvVarRequirement):
        """Add a custom environment variable requirement"""
        self._requirements[requirement.name] = requirement
    
    def validate_environment(self, strict: bool = False) -> Dict[str, Any]:
        """
        Validate all environment variables
        
        Args:
            strict: If True, raise exception on missing required vars
        
        Returns:
            Validation results dictionary
        """
        results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'missing_required': [],
            'missing_optional': [],
            'invalid_values': [],
            'summary': {}
        }
        
        for name, req in self._requirements.items():
            value = os.getenv(name)
            
            # Check if required variable is missing
            if req.required and not value:
                results['missing_required'].append(name)
                results['errors'].append(f"Required environment variable '{name}' is not set: {req.description}")
                results['valid'] = False
                continue
            
            # Check if optional variable is missing
            if not req.required and not value:
                results['missing_optional'].append(name)
                if not req.default:
                    results['warnings'].append(f"Optional environment variable '{name}' is not set: {req.description}")
                continue
            
            # Validate choices if specified
            if value and req.choices and value not in req.choices:
                results['invalid_values'].append(name)
                results['errors'].append(f"Environment variable '{name}' has invalid value '{value}'. Allowed: {req.choices}")
                results['valid'] = False
                continue
            
            # Add to summary
            results['summary'][name] = {
                'value': value or req.default,
                'is_set': bool(value),
                'using_default': not value and req.default,
                'required': req.required
            }
        
        # Log results
        if results['errors']:
            for error in results['errors']:
                self.logger.error(error)
        
        if results['warnings']:
            for warning in results['warnings']:
                self.logger.warning(warning)
        
        # Raise exception if strict mode and errors exist
        if strict and not results['valid']:
            raise ConfigurationError(
                f"Environment validation failed. Missing required variables: {results['missing_required']}",
                details=results
            )
        
        return results
    
    def get_environment_summary(self) -> str:
        """Get a formatted summary of environment configuration"""
        validation = self.validate_environment(strict=False)
        
        lines = ["Environment Configuration Summary:"]
        lines.append("=" * 50)
        
        # Required variables
        required_set = [name for name, info in validation['summary'].items() if info['required'] and info['is_set']]
        required_missing = validation['missing_required']
        
        lines.append(f"Required Variables: {len(required_set)} set, {len(required_missing)} missing")
        if required_missing:
            lines.append(f"  Missing: {', '.join(required_missing)}")
        
        # Optional variables
        optional_set = [name for name, info in validation['summary'].items() if not info['required'] and info['is_set']]
        optional_missing = validation['missing_optional']
        
        lines.append(f"Optional Variables: {len(optional_set)} set, {len(optional_missing)} not set")
        
        # Environment-specific info
        env = validation['summary'].get('ENVIRONMENT', {}).get('value', 'unknown')
        debug = validation['summary'].get('DEBUG', {}).get('value', 'False')
        lines.append(f"Environment: {env} (Debug: {debug})")
        
        # Validation status
        status = "✅ VALID" if validation['valid'] else "❌ INVALID"
        lines.append(f"Status: {status}")
        
        return "\n".join(lines)


# Global validator instance
env_validator = EnvironmentValidator()

# Convenience functions
def validate_env(strict: bool = False) -> Dict[str, Any]:
    """Convenience function for environment validation"""
    return env_validator.validate_environment(strict)

def get_env_summary() -> str:
    """Convenience function for environment summary"""
    return env_validator.get_environment_summary()

def require_env_vars(*var_names: str) -> None:
    """
    Require specific environment variables to be set
    
    Args:
        *var_names: Names of required environment variables
    
    Raises:
        ConfigurationError: If any required variable is missing
    """
    missing = [name for name in var_names if not os.getenv(name)]
    
    if missing:
        raise ConfigurationError(
            f"Required environment variables not set: {', '.join(missing)}",
            details={'missing_variables': missing}
        )

def get_env_with_validation(
    name: str, 
    default: Optional[str] = None,
    required: bool = False,
    choices: Optional[List[str]] = None
) -> Optional[str]:
    """
    Get environment variable with validation
    
    Args:
        name: Environment variable name
        default: Default value if not set
        required: Whether the variable is required
        choices: List of allowed values
    
    Returns:
        Environment variable value or default
    
    Raises:
        ConfigurationError: If required variable is missing or invalid
    """
    value = os.getenv(name, default)
    
    if required and not value:
        raise ConfigurationError(f"Required environment variable '{name}' is not set")
    
    if value and choices and value not in choices:
        raise ConfigurationError(
            f"Environment variable '{name}' has invalid value '{value}'. Allowed: {choices}"
        )
    
    return value
