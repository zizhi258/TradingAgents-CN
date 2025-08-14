#!/usr/bin/env python3
"""
Configuration Management System for TradingAgents-CN
Handles environment-specific configs, secrets, and validation
"""

import os
import json
import yaml
import base64
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConfigEnvironment:
    """Configuration environment definition"""
    name: str
    description: str
    base_config: Dict[str, Any] = field(default_factory=dict)
    secrets: Dict[str, Any] = field(default_factory=dict)
    overrides: Dict[str, Any] = field(default_factory=dict)
    validation_rules: List[Dict[str, Any]] = field(default_factory=list)


class ConfigurationManager:
    """Manages environment-specific configurations and secrets"""
    
    def __init__(self, config_dir: str = "config"):
        """
        Initialize configuration manager
        
        Args:
            config_dir: Path to configuration directory
        """
        self.config_dir = Path(config_dir)
        self.environments_dir = self.config_dir / "environments"
        self.secrets_dir = self.config_dir / "secrets"
        self.templates_dir = self.config_dir / "templates"
        
        # Ensure directories exist
        for directory in [self.environments_dir, self.secrets_dir, self.templates_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize encryption for secrets
        self._init_encryption()
        
        # Load environments
        self.environments = {}
        self._load_environments()
    
    def _init_encryption(self):
        """Initialize encryption for secrets management"""
        key_file = self.secrets_dir / ".encryption_key"
        
        if key_file.exists():
            with open(key_file, "rb") as f:
                key = f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(key)
            os.chmod(key_file, 0o600)  # Restrict permissions
        
        self.cipher = Fernet(key)
    
    def _load_environments(self):
        """Load environment configurations"""
        for env_file in self.environments_dir.glob("*.yaml"):
            env_name = env_file.stem
            try:
                with open(env_file, "r") as f:
                    env_data = yaml.safe_load(f)
                
                self.environments[env_name] = ConfigEnvironment(
                    name=env_name,
                    description=env_data.get("description", ""),
                    base_config=env_data.get("config", {}),
                    overrides=env_data.get("overrides", {}),
                    validation_rules=env_data.get("validation", [])
                )
                
                # Load encrypted secrets
                self._load_environment_secrets(env_name)
                
            except Exception as e:
                logger.error(f"Failed to load environment {env_name}: {e}")
    
    def _load_environment_secrets(self, env_name: str):
        """Load encrypted secrets for environment"""
        secrets_file = self.secrets_dir / f"{env_name}.enc"
        
        if secrets_file.exists():
            try:
                with open(secrets_file, "rb") as f:
                    encrypted_data = f.read()
                
                decrypted_data = self.cipher.decrypt(encrypted_data)
                secrets = json.loads(decrypted_data.decode())
                
                if env_name in self.environments:
                    self.environments[env_name].secrets = secrets
                
            except Exception as e:
                logger.error(f"Failed to load secrets for {env_name}: {e}")
    
    def create_environment(self, 
                          name: str, 
                          description: str, 
                          base_config: Dict[str, Any],
                          validation_rules: Optional[List[Dict[str, Any]]] = None) -> bool:
        """
        Create a new environment configuration
        
        Args:
            name: Environment name
            description: Environment description
            base_config: Base configuration dictionary
            validation_rules: Optional validation rules
            
        Returns:
            bool: Success status
        """
        try:
            env_data = {
                "description": description,
                "config": base_config,
                "overrides": {},
                "validation": validation_rules or []
            }
            
            env_file = self.environments_dir / f"{name}.yaml"
            with open(env_file, "w") as f:
                yaml.dump(env_data, f, default_flow_style=False, indent=2)
            
            # Create environment object
            self.environments[name] = ConfigEnvironment(
                name=name,
                description=description,
                base_config=base_config,
                validation_rules=validation_rules or []
            )
            
            logger.info(f"Created environment: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create environment {name}: {e}")
            return False
    
    def update_secrets(self, env_name: str, secrets: Dict[str, Any]) -> bool:
        """
        Update secrets for an environment
        
        Args:
            env_name: Environment name
            secrets: Secrets dictionary
            
        Returns:
            bool: Success status
        """
        try:
            # Encrypt secrets
            secrets_json = json.dumps(secrets, indent=2)
            encrypted_data = self.cipher.encrypt(secrets_json.encode())
            
            # Save encrypted secrets
            secrets_file = self.secrets_dir / f"{env_name}.enc"
            with open(secrets_file, "wb") as f:
                f.write(encrypted_data)
            
            os.chmod(secrets_file, 0o600)  # Restrict permissions
            
            # Update in-memory
            if env_name in self.environments:
                self.environments[env_name].secrets = secrets
            
            logger.info(f"Updated secrets for environment: {env_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update secrets for {env_name}: {e}")
            return False
    
    def get_config(self, env_name: str, include_secrets: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get complete configuration for an environment
        
        Args:
            env_name: Environment name
            include_secrets: Whether to include secrets
            
        Returns:
            Dict: Complete configuration or None if not found
        """
        if env_name not in self.environments:
            logger.error(f"Environment not found: {env_name}")
            return None
        
        env = self.environments[env_name]
        
        # Start with base config
        config = env.base_config.copy()
        
        # Apply overrides
        config.update(env.overrides)
        
        # Add secrets if requested
        if include_secrets and env.secrets:
            config.update(env.secrets)
        
        return config
    
    def validate_config(self, env_name: str) -> List[str]:
        """
        Validate configuration for an environment
        
        Args:
            env_name: Environment name
            
        Returns:
            List[str]: List of validation errors (empty if valid)
        """
        errors = []
        
        if env_name not in self.environments:
            return [f"Environment not found: {env_name}"]
        
        env = self.environments[env_name]
        config = self.get_config(env_name, include_secrets=True)
        
        # Run validation rules
        for rule in env.validation_rules:
            try:
                rule_type = rule.get("type")
                field = rule.get("field")
                value = config.get(field)
                
                if rule_type == "required":
                    if not value:
                        errors.append(f"Required field missing: {field}")
                
                elif rule_type == "format":
                    expected_format = rule.get("format")
                    if value and not self._validate_format(value, expected_format):
                        errors.append(f"Invalid format for {field}: expected {expected_format}")
                
                elif rule_type == "range":
                    min_val = rule.get("min")
                    max_val = rule.get("max")
                    if value is not None:
                        if min_val is not None and value < min_val:
                            errors.append(f"{field} below minimum value: {min_val}")
                        if max_val is not None and value > max_val:
                            errors.append(f"{field} above maximum value: {max_val}")
                
                elif rule_type == "enum":
                    allowed_values = rule.get("values", [])
                    if value and value not in allowed_values:
                        errors.append(f"Invalid value for {field}: must be one of {allowed_values}")
                
            except Exception as e:
                errors.append(f"Validation error for rule {rule}: {e}")
        
        return errors
    
    def _validate_format(self, value: str, format_type: str) -> bool:
        """Validate value format"""
        import re
        
        format_patterns = {
            "url": r"^https?://[^\s/$.?#].[^\s]*$",
            "email": r"^[^\s@]+@[^\s@]+\.[^\s@]+$",
            "mongodb_url": r"^mongodb://.*",
            "redis_url": r"^redis://.*",
            "port": r"^\d{1,5}$"
        }
        
        pattern = format_patterns.get(format_type)
        if pattern:
            return bool(re.match(pattern, str(value)))
        
        return True
    
    def export_config(self, env_name: str, format_type: str = "env") -> Optional[str]:
        """
        Export configuration in specified format
        
        Args:
            env_name: Environment name
            format_type: Export format (env, json, yaml, k8s_secret)
            
        Returns:
            str: Formatted configuration or None if error
        """
        config = self.get_config(env_name, include_secrets=True)
        if not config:
            return None
        
        try:
            if format_type == "env":
                lines = []
                for key, value in config.items():
                    # Convert to environment variable format
                    env_key = key.upper().replace(".", "_")
                    if isinstance(value, (dict, list)):
                        env_value = json.dumps(value)
                    else:
                        env_value = str(value)
                    lines.append(f'{env_key}="{env_value}"')
                return "\n".join(lines)
            
            elif format_type == "json":
                return json.dumps(config, indent=2)
            
            elif format_type == "yaml":
                return yaml.dump(config, default_flow_style=False, indent=2)
            
            elif format_type == "k8s_secret":
                # Kubernetes Secret format
                secret_data = {}
                for key, value in config.items():
                    if isinstance(value, (dict, list)):
                        encoded_value = base64.b64encode(json.dumps(value).encode()).decode()
                    else:
                        encoded_value = base64.b64encode(str(value).encode()).decode()
                    secret_data[key] = encoded_value
                
                secret_manifest = {
                    "apiVersion": "v1",
                    "kind": "Secret",
                    "metadata": {
                        "name": f"tradingagents-{env_name}-config",
                        "namespace": "tradingagents-cn"
                    },
                    "type": "Opaque",
                    "data": secret_data
                }
                
                return yaml.dump(secret_manifest, default_flow_style=False, indent=2)
            
            else:
                logger.error(f"Unsupported export format: {format_type}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to export config: {e}")
            return None
    
    def list_environments(self) -> List[str]:
        """Get list of available environments"""
        return list(self.environments.keys())
    
    def get_environment_info(self, env_name: str) -> Optional[Dict[str, Any]]:
        """Get environment information"""
        if env_name not in self.environments:
            return None
        
        env = self.environments[env_name]
        return {
            "name": env.name,
            "description": env.description,
            "config_keys": list(env.base_config.keys()),
            "secrets_keys": list(env.secrets.keys()),
            "override_keys": list(env.overrides.keys()),
            "validation_rules_count": len(env.validation_rules)
        }


# CLI Interface
def main():
    """CLI interface for configuration management"""
    import argparse
    
    parser = argparse.ArgumentParser(description="TradingAgents-CN Configuration Manager")
    parser.add_argument("--config-dir", default="config", help="Configuration directory path")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # List environments
    list_parser = subparsers.add_parser("list", help="List available environments")
    
    # Create environment
    create_parser = subparsers.add_parser("create", help="Create new environment")
    create_parser.add_argument("name", help="Environment name")
    create_parser.add_argument("--description", default="", help="Environment description")
    create_parser.add_argument("--template", help="Template file path")
    
    # Update secrets
    secrets_parser = subparsers.add_parser("secrets", help="Update environment secrets")
    secrets_parser.add_argument("environment", help="Environment name")
    secrets_parser.add_argument("--file", help="Secrets JSON file path")
    
    # Validate configuration
    validate_parser = subparsers.add_parser("validate", help="Validate environment configuration")
    validate_parser.add_argument("environment", help="Environment name")
    
    # Export configuration
    export_parser = subparsers.add_parser("export", help="Export environment configuration")
    export_parser.add_argument("environment", help="Environment name")
    export_parser.add_argument("--format", choices=["env", "json", "yaml", "k8s_secret"], 
                              default="env", help="Export format")
    export_parser.add_argument("--output", help="Output file path")
    
    args = parser.parse_args()
    
    # Initialize configuration manager
    config_manager = ConfigurationManager(args.config_dir)
    
    if args.command == "list":
        environments = config_manager.list_environments()
        print("Available environments:")
        for env_name in environments:
            info = config_manager.get_environment_info(env_name)
            print(f"  - {env_name}: {info['description']}")
    
    elif args.command == "create":
        base_config = {}
        if args.template:
            with open(args.template, "r") as f:
                if args.template.endswith(".yaml"):
                    base_config = yaml.safe_load(f)
                else:
                    base_config = json.load(f)
        
        success = config_manager.create_environment(
            args.name, 
            args.description, 
            base_config
        )
        
        if success:
            print(f"Environment '{args.name}' created successfully")
        else:
            print(f"Failed to create environment '{args.name}'")
            exit(1)
    
    elif args.command == "secrets":
        if args.file:
            with open(args.file, "r") as f:
                secrets = json.load(f)
        else:
            print("Please provide secrets via --file option")
            exit(1)
        
        success = config_manager.update_secrets(args.environment, secrets)
        
        if success:
            print(f"Secrets updated for environment '{args.environment}'")
        else:
            print(f"Failed to update secrets for environment '{args.environment}'")
            exit(1)
    
    elif args.command == "validate":
        errors = config_manager.validate_config(args.environment)
        
        if errors:
            print(f"Validation errors for environment '{args.environment}':")
            for error in errors:
                print(f"  - {error}")
            exit(1)
        else:
            print(f"Environment '{args.environment}' validation passed")
    
    elif args.command == "export":
        config_output = config_manager.export_config(args.environment, args.format)
        
        if config_output:
            if args.output:
                with open(args.output, "w") as f:
                    f.write(config_output)
                print(f"Configuration exported to {args.output}")
            else:
                print(config_output)
        else:
            print(f"Failed to export configuration for environment '{args.environment}'")
            exit(1)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()